"""Database queries for the users table."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from doppelganger.db.types import UserRow


async def get_user_by_discord_id(conn: AsyncConnection, discord_id: str) -> UserRow | None:
    """Fetch a user by their Discord ID."""
    sql = text("SELECT * FROM users WHERE discord_id = :discord_id")
    params = {"discord_id": discord_id}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else UserRow(**row)


async def create_user(conn: AsyncConnection, discord_id: str, *, username: str | None = None) -> UserRow:
    """Insert a new user and return the created row."""
    sql = text("INSERT INTO users (discord_id, username) VALUES (:discord_id, :username) RETURNING *")
    params: dict[str, Any] = {"discord_id": discord_id, "username": username}

    result = await conn.execute(sql, params)
    return UserRow(**result.mappings().one())


async def update_username(conn: AsyncConnection, user_id: int, username: str) -> None:
    """Update a user's cached Discord username."""
    sql = text("UPDATE users SET username = :username WHERE id = :user_id")
    params: dict[str, Any] = {"user_id": user_id, "username": username}
    await conn.execute(sql, params)


async def set_user_blacklisted(conn: AsyncConnection, user_id: int, *, blacklisted: bool) -> UserRow | None:
    """Update a user's blacklisted status."""
    sql = text("UPDATE users SET blacklisted = :blacklisted WHERE id = :user_id RETURNING *")
    params: dict[str, Any] = {"user_id": user_id, "blacklisted": blacklisted}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else UserRow(**row)


async def get_user(conn: AsyncConnection, user_id: int) -> UserRow | None:
    """Fetch a user by primary key."""
    sql = text("SELECT * FROM users WHERE id = :user_id")
    params = {"user_id": user_id}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else UserRow(**row)


async def list_users(conn: AsyncConnection) -> list[UserRow]:
    """Fetch all users ordered by creation date."""
    sql = text("SELECT * FROM users ORDER BY created_at DESC")
    result = await conn.execute(sql)
    return [UserRow(**row) for row in result.mappings().all()]
