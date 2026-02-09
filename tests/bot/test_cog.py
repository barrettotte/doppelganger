"""Tests for the TTS cog slash commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from doppelganger.bot.cogs.tts import TTSCog
from doppelganger.tts.voice_registry import VoiceEntry


def _make_db_engine(user_row: dict[str, object] | None = None, *, blacklisted: bool = False) -> MagicMock:
    """
    Create a mock DB engine with connect() and begin() async context managers.
    The execute mock returns a MagicMock result so .mappings().first() and .one() are sync.
    """
    engine = MagicMock()

    # For is_not_blacklisted (uses engine.connect)
    connect_conn = AsyncMock()
    connect_result = MagicMock()
    if user_row is None:
        connect_result.mappings.return_value.first.return_value = None
    else:
        connect_result.mappings.return_value.first.return_value = user_row
    connect_conn.execute.return_value = connect_result

    connect_ctx = AsyncMock()
    connect_ctx.__aenter__.return_value = connect_conn
    engine.connect.return_value = connect_ctx

    # For create_tts_request / get_user_by_discord_id (uses engine.begin)
    begin_conn = AsyncMock()
    begin_result = MagicMock()
    begin_result.mappings.return_value.first.return_value = {
        "id": 1,
        "discord_id": "12345",
        "blacklisted": blacklisted,
    }
    begin_result.mappings.return_value.one.return_value = {
        "id": 1,
        "discord_id": "12345",
    }
    begin_conn.execute.return_value = begin_result

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
    bot.db_engine = _make_db_engine({"id": 1, "discord_id": "12345", "blacklisted": False})
    bot.tts_service = MagicMock()
    bot.voice_registry = MagicMock()
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

    async def test_say_generates_and_plays_audio(self, cog: TTSCog, bot: MagicMock, interaction: MagicMock) -> None:
        voice_entry = VoiceEntry(name="gandalf", reference_audio_path=MagicMock())
        bot.voice_registry.get_voice.return_value = voice_entry

        result = MagicMock()
        result.audio_bytes = b"audio"
        result.duration_ms = 1000
        bot.tts_service.generate.return_value = result

        target_channel = MagicMock()
        target_channel.guild.id = 42

        with patch.object(cog.voice_manager, "play", new_callable=AsyncMock) as mock_play:
            await cog.say.callback(cog, interaction, "gandalf", "Hello world", target_channel)

        mock_play.assert_awaited_once()
        interaction.followup.send.assert_awaited()
        last_call = interaction.followup.send.call_args
        assert "gandalf" in str(last_call)

    async def test_say_with_unknown_character_returns_error(
        self, cog: TTSCog, bot: MagicMock, interaction: MagicMock
    ) -> None:
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
        bot.settings.required_role_id = "999"

        await cog.say.callback(cog, interaction, "gandalf", "Hello", None)

        last_call = interaction.followup.send.call_args
        assert "required role" in str(last_call)

    async def test_say_with_blacklisted_user_returns_error(
        self, cog: TTSCog, bot: MagicMock, interaction: MagicMock
    ) -> None:
        bot.db_engine = _make_db_engine(
            {"id": 1, "discord_id": "12345", "blacklisted": True},
            blacklisted=True,
        )

        await cog.say.callback(cog, interaction, "gandalf", "Hello", None)

        last_call = interaction.followup.send.call_args
        assert "blacklisted" in str(last_call)


class TestVoicesCommand:
    """Tests for the /voices slash command."""

    async def test_voices_returns_character_list(self, cog: TTSCog, bot: MagicMock, interaction: MagicMock) -> None:
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
