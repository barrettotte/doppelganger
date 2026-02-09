"""TTS slash commands for the Discord bot."""

import asyncio
import logging
import time
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from doppelganger.bot.checks import has_required_role, is_not_blacklisted
from doppelganger.bot.voice import VoiceManager
from doppelganger.db.queries.audit_log import create_audit_entry
from doppelganger.db.queries.tts_requests import (
    create_tts_request,
    mark_tts_request_completed,
    update_tts_request_status,
)
from doppelganger.db.queries.users import create_user, get_user_by_discord_id

logger = logging.getLogger(__name__)


class TTSCog(commands.Cog):
    """Cog providing /say and /voices slash commands."""

    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.max_text_length: int = bot.settings.max_text_length
        self.voice_manager = VoiceManager(
            cooldown_seconds=bot.settings.cooldown_seconds,
            entrance_sound=bot.settings.entrance_sound,
        )

    @app_commands.command(name="say", description="Generate TTS audio and play it in a voice channel")
    @app_commands.describe(
        character="The character voice to use",
        text=f"The text to speak (default max of 500 characters)",
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

        try:
            async with self.bot.db_engine.begin() as conn:
                user = await get_user_by_discord_id(conn, discord_id)
                if user is None:
                    user = await create_user(conn, discord_id)
                user_id: int = user["id"]
                request_row = await create_tts_request(conn, user_id, character, text)
                request_id: int = request_row["id"]

        except Exception:
            logger.exception("Error creating TTS request")
            await interaction.followup.send("An error occurred while processing your request.")
            return

        try:
            cached = self.bot.audio_cache.get(character, text)
            if cached is not None:
                audio_bytes = cached
                duration_ms = 0
            else:
                loop = asyncio.get_running_loop()
                start_time = time.monotonic()
                result = await loop.run_in_executor(None, self.bot.tts_service.generate, character, text)
                duration_ms = int((time.monotonic() - start_time) * 1000)
                audio_bytes = result.audio_bytes
                self.bot.audio_cache.put(character, text, audio_bytes)

            await self.voice_manager.play(target_channel, audio_bytes)

            async with self.bot.db_engine.begin() as conn:
                await mark_tts_request_completed(conn, request_id, duration_ms)
                await create_audit_entry(
                    conn,
                    "tts_play",
                    user_id=user_id,
                    details={"character": character, "text": text, "duration_ms": duration_ms},
                )

            preview = text[:50] + "..." if len(text) > 50 else text
            await interaction.followup.send(f"Playing '{preview}' as {character}")

        except Exception:
            logger.exception("Error processing /say command")
            try:
                async with self.bot.db_engine.begin() as conn:
                    await update_tts_request_status(conn, request_id, "failed")
            except Exception:
                logger.exception("Failed to update request status")

            await interaction.followup.send("An error occurred while generating audio. Please try again.")

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
        names = "\n".join(f"- {v.name}" for v in voice_list)
        embed.description = names
        await interaction.followup.send(embed=embed)


async def setup(bot: Any) -> None:
    """Add the TTS cog to the bot."""
    await bot.add_cog(TTSCog(bot))
