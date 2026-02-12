"""Discord bot client for Doppelganger TTS."""

import logging
import time

import discord
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncEngine

from doppelganger.bot.queue import RateLimiter, TTSQueue
from doppelganger.config import DiscordSettings
from doppelganger.tts.cache import AudioCache
from doppelganger.tts.service import TTSService
from doppelganger.tts.voice_registry import VoiceRegistry

logger = logging.getLogger(__name__)


class DoppelgangerBot(commands.Bot):
    """Discord bot for TTS voice cloning."""

    def __init__(
        self,
        settings: DiscordSettings,
        tts_service: TTSService,
        voice_registry: VoiceRegistry,
        audio_cache: AudioCache,
        db_engine: AsyncEngine,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(command_prefix=settings.command_prefix, intents=intents)

        self.settings = settings
        self.tts_service = tts_service
        self.voice_registry = voice_registry
        self.audio_cache = audio_cache
        self.db_engine = db_engine
        self.tts_queue = TTSQueue(max_depth=settings.max_queue_depth)
        self.rate_limiter = RateLimiter(requests_per_minute=settings.requests_per_minute)
        self._started_at: float = time.monotonic()

    async def setup_hook(self) -> None:
        """Load cogs and sync slash commands."""
        await self.load_extension("doppelganger.bot.cogs.tts")

        guild_id = self.settings.guild_id
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)

            await self.tree.sync(guild=guild)
            logger.info("Synced slash commands to guild %s", guild_id)
        else:
            await self.tree.sync()
            logger.info("Synced slash commands globally")

    async def on_ready(self) -> None:
        """Log connection info and set bot status."""
        logger.info("Bot logged in as %s (ID: %s)", self.user, getattr(self.user, "id", None))
        logger.info("Connected to %d guild(s)", len(self.guilds))
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))

    async def start_bot(self) -> None:
        """Start the bot. Intended to be run via asyncio.create_task()."""
        token = self.settings.token.get_secret_value()
        await self.start(token)
