"""Database queries for the characters table."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from doppelganger.db.types import CharacterRow
from doppelganger.tts.voice_registry import VoiceRegistry

logger = logging.getLogger(__name__)


async def get_character_by_name(conn: AsyncConnection, name: str) -> CharacterRow | None:
    """Fetch a character by name."""
    sql = text("SELECT * FROM characters WHERE name = :name")
    params = {"name": name}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else CharacterRow(**row)


async def create_character(conn: AsyncConnection, name: str, reference_audio_path: str) -> CharacterRow:
    """Insert a new character and return the created row."""
    sql = text("INSERT INTO characters (name, reference_audio_path) VALUES (:name, :reference_audio_path) RETURNING *")
    params = {"name": name, "reference_audio_path": reference_audio_path}

    result = await conn.execute(sql, params)
    return CharacterRow(**result.mappings().one())


async def delete_character(conn: AsyncConnection, character_id: int) -> bool:
    """Delete a character by ID. Returns True if a row was deleted."""
    sql = text("DELETE FROM characters WHERE id = :id")
    params = {"id": character_id}

    result = await conn.execute(sql, params)
    return result.rowcount > 0


async def list_characters(conn: AsyncConnection) -> list[CharacterRow]:
    """Fetch all characters ordered by name."""
    sql = text("SELECT * FROM characters ORDER BY name ASC")

    result = await conn.execute(sql)
    return [CharacterRow(**row) for row in result.mappings().all()]


async def sync_voices_to_db(conn: AsyncConnection, registry: VoiceRegistry) -> int:
    """Insert DB rows for any filesystem voices not already in the characters table.

    Returns the number of new rows created.
    """
    existing = await list_characters(conn)
    existing_names = {c.name for c in existing}

    created = 0
    for voice in registry.list_voices():
        if voice.name not in existing_names:
            await create_character(conn, voice.name, str(voice.reference_audio_path))
            logger.info("Synced filesystem voice to DB: %s", voice.name)
            created += 1

    return created
