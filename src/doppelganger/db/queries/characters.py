"""Database queries for the characters table."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from doppelganger.db.types import CharacterRow
from doppelganger.tts.engine import TTSOverrides
from doppelganger.tts.voice_registry import VoiceRegistry

logger = logging.getLogger(__name__)


async def get_character(conn: AsyncConnection, character_id: int) -> CharacterRow | None:
    """Fetch a character by ID."""
    sql = text("SELECT * FROM characters WHERE id = :id")
    params = {"id": character_id}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else CharacterRow(**row)


async def get_character_by_name(conn: AsyncConnection, name: str) -> CharacterRow | None:
    """Fetch a character by name."""
    sql = text("SELECT * FROM characters WHERE name = :name")
    params = {"name": name}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else CharacterRow(**row)


async def create_character(
    conn: AsyncConnection, name: str, reference_audio_path: str, engine: str = "chatterbox"
) -> CharacterRow:
    """Insert a new character and return the created row."""
    sql = text(
        "INSERT INTO characters (name, reference_audio_path, engine)"
        " VALUES (:name, :reference_audio_path, :engine) RETURNING *"
    )
    params = {"name": name, "reference_audio_path": reference_audio_path, "engine": engine}

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


async def update_character_tuning(
    conn: AsyncConnection,
    character_id: int,
    tts_exaggeration: float | None = None,
    tts_cfg_weight: float | None = None,
    tts_temperature: float | None = None,
    tts_repetition_penalty: float | None = None,
    tts_top_p: float | None = None,
    tts_frequency_penalty: float | None = None,
) -> CharacterRow | None:
    """Update tuning columns for a character and return the updated row."""
    sql = text(
        "UPDATE characters"
        " SET tts_exaggeration = :tts_exaggeration,"
        " tts_cfg_weight = :tts_cfg_weight,"
        " tts_temperature = :tts_temperature,"
        " tts_repetition_penalty = :tts_repetition_penalty,"
        " tts_top_p = :tts_top_p,"
        " tts_frequency_penalty = :tts_frequency_penalty"
        " WHERE id = :id RETURNING *"
    )
    params = {
        "id": character_id,
        "tts_exaggeration": tts_exaggeration,
        "tts_cfg_weight": tts_cfg_weight,
        "tts_temperature": tts_temperature,
        "tts_repetition_penalty": tts_repetition_penalty,
        "tts_top_p": tts_top_p,
        "tts_frequency_penalty": tts_frequency_penalty,
    }

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else CharacterRow(**row)


async def get_character_overrides(conn: AsyncConnection, character_name: str) -> TTSOverrides | None:
    """Fetch a character's tuning overrides by name, returning None if not found."""
    row_result = await get_character_by_name(conn, character_name)
    if row_result is None:
        return None

    return TTSOverrides(
        exaggeration=row_result.tts_exaggeration,
        cfg_weight=row_result.tts_cfg_weight,
        temperature=row_result.tts_temperature,
        repetition_penalty=row_result.tts_repetition_penalty,
        top_p=row_result.tts_top_p,
        frequency_penalty=row_result.tts_frequency_penalty,
    )


async def sync_voices_to_db(conn: AsyncConnection, registry: VoiceRegistry) -> int:
    """Insert DB rows for any filesystem voices not already in the characters table.

    Returns the number of new rows created.
    """
    existing = await list_characters(conn)
    existing_names = {c.name for c in existing}

    created = 0
    for voice in registry.list_voices():
        if voice.name not in existing_names:
            await create_character(conn, voice.name, str(voice.reference_audio_path), voice.engine.value)
            logger.info("Synced filesystem voice to DB: %s (engine=%s)", voice.name, voice.engine.value)
            created += 1

    return created
