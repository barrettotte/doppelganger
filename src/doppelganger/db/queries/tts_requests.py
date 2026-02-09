"""Database queries for the tts_requests table."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def create_tts_request(conn: AsyncConnection, user_id: int, voice: str, request_text: str) -> dict[str, Any]:
    """Insert a new TTS request and return the created row."""
    sql = text("INSERT INTO tts_requests (user_id, character, text) VALUES (:user_id, :voice, :text) RETURNING *")
    params = {"user_id": user_id, "voice": voice, "text": request_text}

    result = await conn.execute(sql, params)
    return dict(result.mappings().one())


async def update_tts_request_status(conn: AsyncConnection, request_id: int, status: str) -> dict[str, Any] | None:
    """Update the status of a TTS request."""
    sql = text("UPDATE tts_requests SET status = :status WHERE id = :id RETURNING *")
    params = {"id": request_id, "status": status}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else dict(row)


async def mark_tts_request_started(conn: AsyncConnection, request_id: int) -> dict[str, Any] | None:
    """Mark a TTS request as processing with a started timestamp."""
    sql = text("UPDATE tts_requests SET status = 'processing', started_at = NOW() WHERE id = :id RETURNING *")
    params = {"id": request_id}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else dict(row)


async def mark_tts_request_completed(conn: AsyncConnection, request_id: int, duration_ms: int) -> dict[str, Any] | None:
    """Mark a TTS request as completed with timing data."""
    sql = text(
        "UPDATE tts_requests "
        "SET status = 'completed', completed_at = NOW(), duration_ms = :duration_ms "
        "WHERE id = :id "
        "RETURNING *"
    )
    params = {"id": request_id, "duration_ms": duration_ms}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else dict(row)


async def list_tts_requests(conn: AsyncConnection, *, status: str | None = None) -> list[dict[str, Any]]:
    """Fetch TTS requests, optionally filtered by status."""
    if status is not None:
        sql = text("SELECT * FROM tts_requests WHERE status = :status ORDER BY created_at DESC")
        params = {"status": status}
        result = await conn.execute(sql, params)
    else:
        sql = text("SELECT * FROM tts_requests ORDER BY created_at DESC")
        result = await conn.execute(sql)

    return [dict(row) for row in result.mappings().all()]


async def get_tts_request(conn: AsyncConnection, request_id: int) -> dict[str, Any] | None:
    """Fetch a single TTS request by ID."""
    sql = text("SELECT * FROM tts_requests WHERE id = :id")
    params = {"id": request_id}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else dict(row)
