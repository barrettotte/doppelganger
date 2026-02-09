"""Database queries for the characters table."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def get_character_by_name(conn: AsyncConnection, name: str) -> dict[str, Any] | None:
    """Fetch a character by name."""
    sql = text("SELECT * FROM characters WHERE name = :name")
    params = {"name": name}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else dict(row)


async def create_character(conn: AsyncConnection, name: str, reference_audio_path: str) -> dict[str, Any]:
    """Insert a new character and return the created row."""
    sql = text("INSERT INTO characters (name, reference_audio_path) VALUES (:name, :reference_audio_path) RETURNING *")
    params = {"name": name, "reference_audio_path": reference_audio_path}

    result = await conn.execute(sql, params)
    return dict(result.mappings().one())


async def delete_character(conn: AsyncConnection, character_id: int) -> bool:
    """Delete a character by ID. Returns True if a row was deleted."""
    sql = text("DELETE FROM characters WHERE id = :id")
    params = {"id": character_id}

    result = await conn.execute(sql, params)
    return result.rowcount > 0


async def list_characters(conn: AsyncConnection) -> list[dict[str, Any]]:
    """Fetch all characters ordered by name."""
    sql = text("SELECT * FROM characters ORDER BY name ASC")

    result = await conn.execute(sql)
    return [dict(row) for row in result.mappings().all()]
