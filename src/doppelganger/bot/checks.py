"""Permission checks for Discord bot commands."""

import logging

import discord
from sqlalchemy.ext.asyncio import AsyncEngine

from doppelganger.db.queries.users import get_user_by_discord_id

logger = logging.getLogger(__name__)


async def has_required_role(interaction: discord.Interaction, required_role_id: str) -> bool:
    """Check if the user has the required role. Returns True if no role is configured."""
    if not required_role_id:
        return True

    if not isinstance(interaction.user, discord.Member):
        return False

    role_id = int(required_role_id)
    return any(role.id == role_id for role in interaction.user.roles)


async def is_not_blacklisted(db_engine: AsyncEngine, discord_id: str) -> bool:
    """Check if the user is not blacklisted. Returns True if user doesn't exist or isn't blacklisted."""
    async with db_engine.connect() as conn:
        user = await get_user_by_discord_id(conn, discord_id)

    if user is None:
        return True

    return not user.blacklisted
