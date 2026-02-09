"""Tests for VoiceManager."""

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from doppelganger.bot.voice import VoiceManager


@pytest.fixture
def voice_manager() -> VoiceManager:
    """Create a VoiceManager with a 2-second cooldown."""
    return VoiceManager(cooldown_seconds=2)


@pytest.fixture
def voice_channel() -> MagicMock:
    """Create a mock voice channel."""
    channel = MagicMock()
    channel.guild.id = 42
    channel.connect = AsyncMock()
    return channel


@pytest.fixture
def wav_bytes() -> bytes:
    """Create minimal valid WAV-like bytes for testing."""
    return b"RIFF" + b"\x00" * 100


def _make_voice_client() -> MagicMock:
    """Create a mock voice client that simulates immediate playback completion."""
    vc = MagicMock()
    vc.disconnect = AsyncMock()

    def fake_play(source: object, *, after: object = None) -> None:
        if callable(after):
            after(None)

    vc.play = MagicMock(side_effect=fake_play)
    return vc


class TestVoiceManager:
    """Tests for VoiceManager playback and cooldown."""

    async def test_play_joins_channel_and_plays_audio(
        self, voice_manager: VoiceManager, voice_channel: MagicMock, wav_bytes: bytes
    ) -> None:
        vc = _make_voice_client()
        voice_channel.connect.return_value = vc

        with patch("doppelganger.bot.voice.discord.FFmpegPCMAudio"):
            await voice_manager.play(voice_channel, wav_bytes)

        voice_channel.connect.assert_awaited_once()
        vc.play.assert_called_once()

    async def test_play_disconnects_after_playback(
        self, voice_manager: VoiceManager, voice_channel: MagicMock, wav_bytes: bytes
    ) -> None:
        vc = _make_voice_client()
        voice_channel.connect.return_value = vc

        with patch("doppelganger.bot.voice.discord.FFmpegPCMAudio"):
            await voice_manager.play(voice_channel, wav_bytes)

        vc.disconnect.assert_awaited_once()

    async def test_is_on_cooldown_returns_false_initially(self, voice_manager: VoiceManager) -> None:
        assert voice_manager.is_on_cooldown(42) is False

    async def test_is_on_cooldown_returns_true_after_play(
        self, voice_manager: VoiceManager, voice_channel: MagicMock, wav_bytes: bytes
    ) -> None:
        vc = _make_voice_client()
        voice_channel.connect.return_value = vc

        with patch("doppelganger.bot.voice.discord.FFmpegPCMAudio"):
            await voice_manager.play(voice_channel, wav_bytes)

        assert voice_manager.is_on_cooldown(42) is True

    async def test_is_on_cooldown_returns_false_after_expiry(self, voice_manager: VoiceManager) -> None:
        voice_manager._last_play_time[42] = time.monotonic() - 10
        assert voice_manager.is_on_cooldown(42) is False

    async def test_play_with_entrance_sound(self, voice_channel: MagicMock, wav_bytes: bytes, tmp_path: Path) -> None:
        entrance_file = tmp_path / "entrance.wav"
        entrance_file.write_bytes(b"RIFF" + b"\x00" * 100)
        vm = VoiceManager(cooldown_seconds=2, entrance_sound=str(entrance_file))

        vc = _make_voice_client()
        voice_channel.connect.return_value = vc

        with patch("doppelganger.bot.voice.discord.FFmpegPCMAudio"):
            await vm.play(voice_channel, wav_bytes)

        assert vc.play.call_count == 2
