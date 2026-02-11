"""Voice channel connection and audio playback management."""

import asyncio
import io
import logging
import time
from collections.abc import Callable
from pathlib import Path

import discord

logger = logging.getLogger(__name__)


class VoiceManager:
    """Manages voice channel connections and audio playback."""

    def __init__(self, cooldown_seconds: int, entrance_sound: str = "") -> None:
        self._cooldown_seconds = cooldown_seconds
        self._last_play_time: dict[int, float] = {}
        self._entrance_sound: Path | None = None

        if entrance_sound:
            path = Path(entrance_sound)
            if path.is_file():
                self._entrance_sound = path
                logger.info("Entrance sound loaded: %s", path)
            else:
                logger.warning("Entrance sound not found: %s", path)

    def is_on_cooldown(self, guild_id: int) -> bool:
        """Check if the given guild is still within the cooldown period."""
        last = self._last_play_time.get(guild_id)
        if last is None:
            return False
        return (time.monotonic() - last) < self._cooldown_seconds

    async def _play_source(
        self,
        voice_client: discord.VoiceClient,
        source: discord.AudioSource,
        guild_id: int,
    ) -> None:
        """Play an audio source and wait for it to finish."""
        done_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        def _after_callback(error: Exception | None) -> None:
            """Discord's play() callback runs in a thread pool, so we need
            call_soon_threadsafe to signal the event back to the async loop."""
            if error is not None:
                logger.error("Playback error in guild %s: %s", guild_id, error)
            loop.call_soon_threadsafe(done_event.set)

        voice_client.play(source, after=_after_callback)
        await done_event.wait()

    async def play(
        self,
        channel: discord.VoiceChannel,
        audio_bytes: bytes,
        *,
        after: Callable[..., object] | None = None,
    ) -> None:
        """Join channel, play optional entrance sound then WAV bytes, leave after playback."""
        guild_id = channel.guild.id
        voice_client: discord.VoiceClient | None = None
        try:
            voice_client = await channel.connect()
            logger.debug("Connected to voice channel %s in guild %s", channel.name, guild_id)

            if self._entrance_sound is not None:
                entrance_source = discord.FFmpegPCMAudio(str(self._entrance_sound))
                await self._play_source(voice_client, entrance_source, guild_id)

            tts_source = discord.FFmpegPCMAudio(io.BytesIO(audio_bytes), pipe=True)
            await self._play_source(voice_client, tts_source, guild_id)

            if after is not None:
                after(None)

            self._last_play_time[guild_id] = time.monotonic()

        except Exception:
            logger.exception("Voice playback failed in guild %s, channel %s", guild_id, channel.name)
            raise

        finally:
            if voice_client is not None:
                await voice_client.disconnect()
