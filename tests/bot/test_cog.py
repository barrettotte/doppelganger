"""Tests for the TTS cog slash commands."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from doppelganger.bot.cogs.tts import TTSCog
from doppelganger.bot.queue import QueueItem, RateLimiter, TTSQueue
from doppelganger.tts.voice_registry import VoiceEntry

_NOW = datetime(2026, 1, 1)


def _make_execute_result(row_dict: dict[str, object] | None) -> MagicMock:
    """Create a mock execute result with mappings().first() and .one() returning the given dict."""
    result = MagicMock()
    result.mappings.return_value.first.return_value = row_dict

    if row_dict is not None:
        result.mappings.return_value.one.return_value = row_dict
    return result


def _make_db_engine(user_row: dict[str, object] | None = None, *, blacklisted: bool = False) -> MagicMock:
    """Create a mock DB engine with connect() and begin() async context managers."""
    engine = MagicMock()

    # Default user dict (ensure created_at is present)
    default_user = {
        "id": 1,
        "discord_id": "12345",
        "blacklisted": blacklisted,
        "created_at": _NOW,
    }

    # Default character dict for get_character_overrides queries
    default_character: dict[str, object] = {
        "id": 1,
        "name": "test",
        "reference_audio_path": "/voices/test/reference.wav",
        "created_at": _NOW,
        "engine": "chatterbox",
        "tts_exaggeration": None,
        "tts_cfg_weight": None,
        "tts_temperature": None,
        "tts_repetition_penalty": None,
        "tts_top_p": None,
        "tts_frequency_penalty": None,
    }

    # For is_not_blacklisted and get_character_overrides (uses engine.connect)
    connect_conn = AsyncMock()
    if user_row is not None:
        connect_row: dict[str, object] | None = {**default_user, **user_row}
    else:
        connect_row = None

    def connect_dispatch(*args: object, **kwargs: object) -> MagicMock:
        """Dispatch connect queries to user or character results based on SQL."""
        sql_str = str(args[0]) if args else ""
        if "characters" in sql_str:
            return _make_execute_result(default_character)
        return _make_execute_result(connect_row)

    connect_conn.execute = AsyncMock(side_effect=connect_dispatch)

    connect_ctx = AsyncMock()
    connect_ctx.__aenter__.return_value = connect_conn
    engine.connect.return_value = connect_ctx

    # For say command flow and _process_item (uses engine.begin)
    tts_request_dict: dict[str, object] = {
        "id": 1,
        "user_id": 1,
        "character": "test",
        "text": "test",
        "status": "pending",
        "created_at": _NOW,
        "started_at": None,
        "completed_at": None,
        "duration_ms": None,
    }
    audit_dict: dict[str, object] = {
        "id": 1,
        "user_id": 1,
        "action": "tts_play",
        "details": None,
        "created_at": _NOW,
    }

    def execute_dispatch(*args: object, **kwargs: object) -> MagicMock:
        """Return different mock results depending on which table the SQL targets."""
        sql_str = str(args[0]) if args else ""
        if "audit_log" in sql_str:
            return _make_execute_result(audit_dict)
        if "tts_requests" in sql_str:
            return _make_execute_result(tts_request_dict)
        return _make_execute_result(default_user)

    begin_conn = AsyncMock()
    begin_conn.execute = AsyncMock(side_effect=execute_dispatch)

    begin_ctx = AsyncMock()
    begin_ctx.__aenter__.return_value = begin_conn
    engine.begin.return_value = begin_ctx

    return engine


@pytest.fixture
def bot() -> MagicMock:
    """Create a mock bot with required attributes."""
    bot = MagicMock()
    bot.settings.cooldown_seconds = 5
    bot.settings.required_role_id = ""
    bot.settings.max_text_length = 2000
    bot.settings.entrance_sound = ""
    bot.db_engine = _make_db_engine({"id": 1, "discord_id": "12345", "blacklisted": False, "created_at": _NOW})
    bot.tts_service = MagicMock()
    bot.voice_registry = MagicMock()
    bot.audio_cache = MagicMock()
    bot.tts_queue = TTSQueue(max_depth=20)
    bot.rate_limiter = RateLimiter(requests_per_minute=10)
    return bot


@pytest.fixture
def cog(bot: MagicMock) -> TTSCog:
    """Create a TTSCog instance with a mocked bot."""
    return TTSCog(bot)


@pytest.fixture
def interaction() -> MagicMock:
    """Create a mock Discord interaction."""
    inter = MagicMock()
    inter.response.defer = AsyncMock()
    inter.followup.send = AsyncMock()
    inter.user.id = 12345
    inter.user.voice = MagicMock()
    inter.user.voice.channel = MagicMock()
    inter.user.voice.channel.guild.id = 42

    role = MagicMock()
    role.id = 111
    inter.user.roles = [role]

    return inter


class TestSayCommand:
    """Tests for the /say slash command."""

    async def test_say_submits_to_queue(self, cog: TTSCog, bot: MagicMock, interaction: MagicMock) -> None:
        """Successful /say should enqueue a request."""
        voice_entry = VoiceEntry(name="gandalf", reference_audio_path=MagicMock())
        bot.voice_registry.get_voice.return_value = voice_entry

        target_channel = MagicMock()
        target_channel.guild.id = 42

        await cog.say.callback(cog, interaction, "gandalf", "Hello world", target_channel)

        assert bot.tts_queue.depth == 1

        interaction.followup.send.assert_awaited()
        last_call = str(interaction.followup.send.call_args)
        assert "Generating" in last_call or "Queued" in last_call

    async def test_say_shows_queue_position_when_busy(
        self, cog: TTSCog, bot: MagicMock, interaction: MagicMock
    ) -> None:
        """Second /say while processing should show queue position."""
        voice_entry = VoiceEntry(name="gandalf", reference_audio_path=MagicMock())
        bot.voice_registry.get_voice.return_value = voice_entry

        target_channel = MagicMock()
        target_channel.guild.id = 42

        # Dequeue the first item so the queue has a "processing" item
        await cog.say.callback(cog, interaction, "gandalf", "First request", target_channel)
        await bot.tts_queue.dequeue()

        # Submit a second request while the first is processing
        interaction2 = MagicMock()
        interaction2.response.defer = AsyncMock()
        interaction2.followup.send = AsyncMock()
        interaction2.user.id = 12345
        role = MagicMock()
        role.id = 111
        interaction2.user.roles = [role]

        await cog.say.callback(cog, interaction2, "gandalf", "Second request", target_channel)

        last_call = str(interaction2.followup.send.call_args)
        assert "Queued" in last_call

    async def test_say_with_unknown_character_returns_error(
        self, cog: TTSCog, bot: MagicMock, interaction: MagicMock
    ) -> None:
        """Unknown character name should return an error."""
        bot.voice_registry.get_voice.return_value = None
        bot.voice_registry.list_voices.return_value = [
            VoiceEntry(name="gandalf", reference_audio_path=MagicMock()),
        ]

        await cog.say.callback(cog, interaction, "unknown", "Hello", None)

        last_call = interaction.followup.send.call_args
        assert "Unknown character" in str(last_call)

    async def test_say_without_required_role_returns_error(
        self, cog: TTSCog, bot: MagicMock, interaction: MagicMock
    ) -> None:
        """Missing required role should return a permission error."""
        bot.settings.required_role_id = "999"

        await cog.say.callback(cog, interaction, "gandalf", "Hello", None)

        last_call = interaction.followup.send.call_args
        assert "required role" in str(last_call)

    async def test_say_with_blacklisted_user_returns_error(
        self, cog: TTSCog, bot: MagicMock, interaction: MagicMock
    ) -> None:
        """Blacklisted user should be rejected."""
        bot.db_engine = _make_db_engine(
            {"id": 1, "discord_id": "12345", "blacklisted": True, "created_at": _NOW},
            blacklisted=True,
        )

        await cog.say.callback(cog, interaction, "gandalf", "Hello", None)

        last_call = interaction.followup.send.call_args
        assert "blacklisted" in str(last_call)

    async def test_say_rate_limited_returns_error(self, cog: TTSCog, bot: MagicMock, interaction: MagicMock) -> None:
        """Rate-limited user should be rejected."""
        bot.rate_limiter = RateLimiter(requests_per_minute=1)
        bot.rate_limiter.try_acquire("12345")

        voice_entry = VoiceEntry(name="gandalf", reference_audio_path=MagicMock())
        bot.voice_registry.get_voice.return_value = voice_entry

        target_channel = MagicMock()
        target_channel.guild.id = 42

        await cog.say.callback(cog, interaction, "gandalf", "Hello", target_channel)

        last_call = str(interaction.followup.send.call_args)
        assert "Rate limit" in last_call

    async def test_say_queue_full_returns_error(self, cog: TTSCog, bot: MagicMock, interaction: MagicMock) -> None:
        """Full queue should return a queue full error."""
        bot.tts_queue = TTSQueue(max_depth=1)
        voice_entry = VoiceEntry(name="gandalf", reference_audio_path=MagicMock())
        bot.voice_registry.get_voice.return_value = voice_entry

        target_channel = MagicMock()
        target_channel.guild.id = 42

        # Fill the queue
        await cog.say.callback(cog, interaction, "gandalf", "First", target_channel)

        # Second request should get queue full message
        interaction2 = MagicMock()
        interaction2.response.defer = AsyncMock()
        interaction2.followup.send = AsyncMock()
        interaction2.user.id = 12345
        role = MagicMock()
        role.id = 111
        interaction2.user.roles = [role]

        await cog.say.callback(cog, interaction2, "gandalf", "Second", target_channel)

        last_call = str(interaction2.followup.send.call_args)
        assert "queue is full" in last_call.lower()


class TestProcessItem:
    """Tests for the queue worker's item processing."""

    async def test_process_item_generates_and_plays(self, cog: TTSCog, bot: MagicMock) -> None:
        """Processing an item should generate audio and play it."""
        bot.audio_cache.get.return_value = None
        result = MagicMock()
        result.audio_bytes = b"audio"
        bot.tts_service.generate.return_value = result

        interaction = MagicMock()
        interaction.followup.send = AsyncMock()
        channel = MagicMock()
        channel.guild.id = 42

        item = QueueItem(
            request_id=1,
            user_id=1,
            discord_id="12345",
            character="gandalf",
            text="Hello world",
            channel=channel,
            interaction=interaction,
        )

        with patch.object(cog.voice_manager, "play", new_callable=AsyncMock) as mock_play:
            await cog._process_item(item)

        mock_play.assert_awaited_once()
        # generate is now called with three args: character, text, overrides
        call_args = bot.tts_service.generate.call_args
        assert call_args[0][0] == "gandalf"
        assert call_args[0][1] == "Hello world"
        assert len(call_args[0]) == 3

    async def test_process_item_uses_cache(self, cog: TTSCog, bot: MagicMock) -> None:
        """Cached audio should skip generation."""
        bot.audio_cache.get.return_value = b"cached_audio"

        interaction = MagicMock()
        interaction.followup.send = AsyncMock()
        channel = MagicMock()
        channel.guild.id = 42

        item = QueueItem(
            request_id=1,
            user_id=1,
            discord_id="12345",
            character="gandalf",
            text="Hello",
            channel=channel,
            interaction=interaction,
        )
        with patch.object(cog.voice_manager, "play", new_callable=AsyncMock) as mock_play:
            await cog._process_item(item)

        mock_play.assert_awaited_once_with(channel, b"cached_audio")
        bot.tts_service.generate.assert_not_called()


class TestVoicesCommand:
    """Tests for the /voices slash command."""

    async def test_voices_returns_character_list(self, cog: TTSCog, bot: MagicMock, interaction: MagicMock) -> None:
        """/voices should return an embed listing available characters."""
        bot.voice_registry.list_voices.return_value = [
            VoiceEntry(name="gandalf", reference_audio_path=MagicMock()),
            VoiceEntry(name="gollum", reference_audio_path=MagicMock()),
        ]

        await cog.voices.callback(cog, interaction)

        interaction.followup.send.assert_awaited_once()
        call_kwargs = interaction.followup.send.call_args
        embed = call_kwargs.kwargs.get("embed") or call_kwargs.args[0]
        assert "gandalf" in embed.description
        assert "gollum" in embed.description
