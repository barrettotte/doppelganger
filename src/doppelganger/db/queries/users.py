"""Database queries for the users table."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def get_user_by_discord_id(conn: AsyncConnection, discord_id: str) -> dict[str, Any] | None:
    """Fetch a user by their Discord ID."""
    sql = text("SELECT * FROM users WHERE discord_id = :discord_id")
    params = {"discord_id": discord_id}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else dict(row)


async def create_user(conn: AsyncConnection, discord_id: str) -> dict[str, Any]:
    """Insert a new user and return the created row."""
    sql = text("INSERT INTO users (discord_id) VALUES (:discord_id) RETURNING *")
    params = {"discord_id": discord_id}

    result = await conn.execute(sql, params)
    return dict(result.mappings().one())


async def set_user_blacklisted(conn: AsyncConnection, user_id: int, *, blacklisted: bool) -> dict[str, Any] | None:
    """Update a user's blacklisted status."""
    sql = text("UPDATE users SET blacklisted = :blacklisted WHERE id = :user_id RETURNING *")
    params = {"user_id": user_id, "blacklisted": blacklisted}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else dict(row)


async def list_users(conn: AsyncConnection) -> list[dict[str, Any]]:
    """Fetch all users ordered by creation date."""
    sql = text("SELECT * FROM users ORDER BY created_at DESC")
    result = await conn.execute(sql)
    return [dict(row) for row in result.mappings().all()]
