"""TTS slash commands for the Discord bot."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from doppelganger.bot.checks import has_required_role, is_not_blacklisted
from doppelganger.bot.queue import QueueFullError, QueueItem
from doppelganger.bot.voice import VoiceManager
from doppelganger.db.queries.audit_log import create_audit_entry
from doppelganger.db.queries.characters import get_character_overrides
from doppelganger.db.queries.tts_requests import (
    create_tts_request,
    mark_tts_request_completed,
    mark_tts_request_started,
    update_tts_request_status,
)
from doppelganger.db.queries.users import create_user, get_user_by_discord_id, update_username
from doppelganger.db.request_status import RequestStatus

if TYPE_CHECKING:
    from doppelganger.bot.client import DoppelgangerBot

logger = logging.getLogger(__name__)


class TTSCog(commands.Cog):
    """Cog providing /say and /voices slash commands with queued TTS processing."""

    def __init__(self, bot: DoppelgangerBot) -> None:
        self.bot = bot
        self.max_text_length: int = bot.settings.max_text_length
        self.voice_manager = VoiceManager(
            cooldown_seconds=bot.settings.cooldown_seconds,
            entrance_sound=bot.settings.entrance_sound,
        )
        self._worker_task: asyncio.Task[None] | None = None

    async def cog_load(self) -> None:
        """Start the queue worker when the cog loads."""
        self._worker_task = asyncio.create_task(self._queue_worker())
        logger.info("TTS queue worker started")

    async def cog_unload(self) -> None:
        """Stop the queue worker when the cog unloads."""
        if self._worker_task is not None:
            self._worker_task.cancel()
            self._worker_task = None
            logger.info("TTS queue worker stopped")

    async def _queue_worker(self) -> None:
        """Background worker that processes queued TTS requests."""
        while True:
            item = await self.bot.tts_queue.dequeue()
            try:
                await self._process_item(item)

            except Exception:
                logger.exception("Error processing queue item %d", item.request_id)
                # DB update and Discord followup are independent - if one fails,
                # we still want to attempt the other so neither is left hanging.
                try:
                    async with self.bot.db_engine.begin() as conn:
                        await update_tts_request_status(conn, item.request_id, RequestStatus.FAILED)
                except Exception:
                    logger.exception("Failed to update request status for %d", item.request_id)

                try:
                    await item.interaction.followup.send("An error occurred while generating audio. Please try again.")
                except Exception:
                    logger.exception("Failed to send error followup for request %d", item.request_id)

            finally:
                self.bot.tts_queue.mark_done()

    async def _process_item(self, item: QueueItem) -> None:
        """Generate TTS audio, play it, and update the database for a single queue item."""
        async with self.bot.db_engine.begin() as conn:
            await mark_tts_request_started(conn, item.request_id)

        async with self.bot.db_engine.connect() as conn:
            overrides = await get_character_overrides(conn, item.character)

        cached = self.bot.audio_cache.get(item.character, item.text)
        if cached is not None:
            audio_bytes = cached
            duration_ms = 0
        else:
            loop = asyncio.get_running_loop()
            start_time = time.monotonic()
            result = await loop.run_in_executor(
                None, self.bot.tts_service.generate, item.character, item.text, overrides
            )
            duration_ms = int((time.monotonic() - start_time) * 1000)
            audio_bytes = result.audio_bytes
            self.bot.audio_cache.put(item.character, item.text, audio_bytes)

        await self.voice_manager.play(item.channel, audio_bytes)

        async with self.bot.db_engine.begin() as conn:
            await mark_tts_request_completed(conn, item.request_id, duration_ms)
            await create_audit_entry(
                conn,
                "tts_play",
                user_id=item.user_id,
                details={"character": item.character, "text": item.text, "duration_ms": duration_ms},
            )

    @app_commands.command(name="say", description="Generate TTS audio and play it in a voice channel")
    @app_commands.describe(
        character="The character voice to use",
        text="The text to speak (default max of 255 characters)",
        channel="Voice channel to play in (defaults to your current channel)",
    )
    async def say(
        self,
        interaction: discord.Interaction,
        character: str,
        text: str,
        channel: discord.VoiceChannel | None = None,
    ) -> None:
        """Generate TTS audio for the given text and play it in a voice channel."""
        await interaction.response.defer(ephemeral=True)

        if not await has_required_role(interaction, self.bot.settings.required_role_id):
            await interaction.followup.send("You don't have the required role to use this command.")
            return

        discord_id = str(interaction.user.id)
        if not await is_not_blacklisted(self.bot.db_engine, discord_id):
            await interaction.followup.send("You have been blacklisted from using this bot.")
            return

        if not self.bot.rate_limiter.try_acquire(discord_id):
            remaining = self.bot.rate_limiter.remaining(discord_id)
            await interaction.followup.send(f"Rate limit reached. You have {remaining} requests remaining this minute.")
            return

        if len(text) > self.max_text_length:
            await interaction.followup.send(f"Text must be {self.max_text_length} characters or fewer.")
            return

        voice = self.bot.voice_registry.get_voice(character)
        if voice is None:
            available = [v.name for v in self.bot.voice_registry.list_voices()]
            await interaction.followup.send(
                f"Unknown character '{character}'. Available: {', '.join(available) or 'none'}"
            )
            return

        target_channel = channel
        if (
            target_channel is None
            and isinstance(interaction.user, discord.Member)
            and interaction.user.voice is not None
        ):
            voice_channel = interaction.user.voice.channel
            if isinstance(voice_channel, discord.VoiceChannel):
                target_channel = voice_channel

        if target_channel is None:
            await interaction.followup.send("You must be in a voice channel or specify one.")
            return

        if self.voice_manager.is_on_cooldown(target_channel.guild.id):
            await interaction.followup.send("Please wait a few seconds before the next TTS request.")
            return

        display_name = interaction.user.display_name

        try:
            async with self.bot.db_engine.begin() as conn:
                user = await get_user_by_discord_id(conn, discord_id)

                if user is None:
                    user = await create_user(conn, discord_id, username=display_name)
                elif user.username != display_name:
                    await update_username(conn, user.id, display_name)

                user_id: int = user.id
                request_row = await create_tts_request(conn, user_id, character, text)
                request_id: int = request_row.id

        except Exception:
            logger.exception("Error creating TTS request")
            await interaction.followup.send("An error occurred while processing your request.")
            return

        item = QueueItem(
            request_id=request_id,
            user_id=user_id,
            discord_id=discord_id,
            character=character,
            text=text,
            channel=target_channel,
            interaction=interaction,
        )

        try:
            position = await self.bot.tts_queue.submit(item)
        except QueueFullError:
            await interaction.followup.send("The request queue is full. Please try again shortly.")

            async with self.bot.db_engine.begin() as conn:
                await update_tts_request_status(conn, request_id, RequestStatus.CANCELLED)
            return

        if position == 1 and self.bot.tts_queue.processing is None:
            await interaction.followup.send(f"Generating '{character}' voice now...")
        else:
            await interaction.followup.send(f"Queued at position {position}. Please wait...")

    @say.autocomplete("character")
    async def character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Provide autocomplete suggestions for the character parameter."""
        voices = self.bot.voice_registry.list_voices()
        matches = [v for v in voices if current.lower() in v.name.lower()]
        return [app_commands.Choice(name=v.name, value=v.name) for v in matches[:25]]

    @app_commands.command(name="voices", description="List available character voices")
    async def voices(self, interaction: discord.Interaction) -> None:
        """List all available character voices."""
        await interaction.response.defer(ephemeral=True)

        voice_list = self.bot.voice_registry.list_voices()
        if not voice_list:
            await interaction.followup.send("No character voices are currently available.")
            return

        embed = discord.Embed(title="Available Voices", color=discord.Color.blue())
        names = "\n".join(f"- {v.name} ({v.engine.value})" for v in voice_list)
        embed.description = names
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="help", description="Show available commands and usage info")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """Show a summary of available commands and bot configuration."""
        await interaction.response.defer(ephemeral=True)

        settings = self.bot.settings
        voice_count = len(self.bot.voice_registry.list_voices())
        queue_state = self.bot.tts_queue.get_state()

        embed = discord.Embed(title="Doppelganger TTS", color=discord.Color.blue())
        embed.description = "Voice cloning bot - generate character speech in voice channels."

        embed.add_field(
            name="Commands",
            value=(
                "**/say** `<character> <text> [channel]` - Generate TTS and play in a voice channel\n"
                "**/voices** - List available character voices\n"
                "**/help** - Show this message"
            ),
            inline=False,
        )

        limits = (
            f"Max text length: {settings.max_text_length} chars\n"
            f"Rate limit: {settings.requests_per_minute}/min\n"
            f"Cooldown: {settings.cooldown_seconds}s\n"
            f"Queue depth: {queue_state.depth}/{settings.max_queue_depth}"
        )
        embed.add_field(name="Limits", value=limits, inline=True)

        info = f"Voices loaded: {voice_count}"
        if settings.required_role_id:
            info += f"\nRequired role: <@&{settings.required_role_id}>"
        embed.add_field(name="Info", value=info, inline=True)

        await interaction.followup.send(embed=embed)


async def setup(bot: DoppelgangerBot) -> None:
    """Add the TTS cog to the bot."""
    await bot.add_cog(TTSCog(bot))
