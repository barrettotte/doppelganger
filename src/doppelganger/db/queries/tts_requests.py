"""Database queries for the tts_requests table."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from doppelganger.db.request_status import RequestStatus
from doppelganger.db.types import TTSRequestRow


async def create_tts_request(conn: AsyncConnection, user_id: int, character: str, request_text: str) -> TTSRequestRow:
    """Insert a new TTS request and return the created row."""
    sql = text("INSERT INTO tts_requests (user_id, character, text) VALUES (:user_id, :character, :text) RETURNING *")
    params: dict[str, Any] = {"user_id": user_id, "character": character, "text": request_text}

    result = await conn.execute(sql, params)
    return TTSRequestRow(**result.mappings().one())


async def update_tts_request_status(
    conn: AsyncConnection, request_id: int, status: RequestStatus
) -> TTSRequestRow | None:
    """Update the status of a TTS request."""
    sql = text("UPDATE tts_requests SET status = :status WHERE id = :id RETURNING *")
    params: dict[str, Any] = {"id": request_id, "status": status}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else TTSRequestRow(**row)


async def mark_tts_request_started(conn: AsyncConnection, request_id: int) -> TTSRequestRow | None:
    """Mark a TTS request as processing with a started timestamp."""
    sql = text("UPDATE tts_requests SET status = 'processing', started_at = NOW() WHERE id = :id RETURNING *")
    params = {"id": request_id}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else TTSRequestRow(**row)


async def mark_tts_request_completed(conn: AsyncConnection, request_id: int, duration_ms: int) -> TTSRequestRow | None:
    """Mark a TTS request as completed with timing data."""
    sql = text(
        "UPDATE tts_requests "
        "SET status = 'completed', completed_at = NOW(), duration_ms = :duration_ms "
        "WHERE id = :id "
        "RETURNING *"
    )
    params: dict[str, Any] = {"id": request_id, "duration_ms": duration_ms}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else TTSRequestRow(**row)


async def list_tts_requests(
    conn: AsyncConnection, *, status: RequestStatus | None = None, limit: int = 50, offset: int = 0
) -> list[TTSRequestRow]:
    """Fetch TTS requests, optionally filtered by status, with pagination."""
    if status is not None:
        sql = text(
            "SELECT * FROM tts_requests WHERE status = :status ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        )
        params: dict[str, Any] = {"status": status, "limit": limit, "offset": offset}
        result = await conn.execute(sql, params)
    else:
        sql = text("SELECT * FROM tts_requests ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
        result = await conn.execute(sql, {"limit": limit, "offset": offset})

    return [TTSRequestRow(**row) for row in result.mappings().all()]


async def get_tts_request(conn: AsyncConnection, request_id: int) -> TTSRequestRow | None:
    """Fetch a single TTS request by ID."""
    sql = text("SELECT * FROM tts_requests WHERE id = :id")
    params = {"id": request_id}

    result = await conn.execute(sql, params)
    row = result.mappings().first()
    return None if row is None else TTSRequestRow(**row)


async def list_tts_requests_by_user(
    conn: AsyncConnection, user_id: int, *, status: RequestStatus | None = None
) -> list[TTSRequestRow]:
    """Fetch TTS requests for a specific user, optionally filtered by status."""
    if status is not None:
        sql = text("SELECT * FROM tts_requests WHERE user_id = :user_id AND status = :status ORDER BY created_at DESC")
        params: dict[str, Any] = {"user_id": user_id, "status": status}
        result = await conn.execute(sql, params)
    else:
        sql = text("SELECT * FROM tts_requests WHERE user_id = :user_id ORDER BY created_at DESC")
        result = await conn.execute(sql, {"user_id": user_id})

    return [TTSRequestRow(**row) for row in result.mappings().all()]


async def count_tts_requests(conn: AsyncConnection, *, status: RequestStatus | None = None) -> int:
    """Count total TTS requests, optionally filtered by status."""
    if status is not None:
        sql = text("SELECT COUNT(*) AS cnt FROM tts_requests WHERE status = :status")
        result = await conn.execute(sql, {"status": status})
    else:
        sql = text("SELECT COUNT(*) AS cnt FROM tts_requests")
        result = await conn.execute(sql)

    row = result.mappings().first()
    return int(row["cnt"]) if row else 0


async def get_request_metrics(conn: AsyncConnection) -> dict[str, Any]:
    """Aggregate TTS request statistics for the metrics endpoint."""
    summary_sql = text(
        "SELECT COUNT(*) AS total, "
        "COUNT(*) FILTER (WHERE status = 'completed') AS completed, "
        "COUNT(*) FILTER (WHERE status = 'failed') AS failed, "
        "COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled, "
        "AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) AS avg_duration_ms "
        "FROM tts_requests"
    )
    summary_result = await conn.execute(summary_sql)
    summary = dict(summary_result.mappings().one())

    by_status_sql = text("SELECT status, COUNT(*) AS count FROM tts_requests GROUP BY status ORDER BY count DESC")
    by_status_result = await conn.execute(by_status_sql)
    requests_by_status = {row["status"]: row["count"] for row in by_status_result.mappings().all()}

    by_character_sql = text(
        "SELECT character, COUNT(*) AS count FROM tts_requests GROUP BY character ORDER BY count DESC"
    )
    by_character_result = await conn.execute(by_character_sql)
    requests_by_character = {row["character"]: row["count"] for row in by_character_result.mappings().all()}

    top_users_sql = text(
        "SELECT user_id, COUNT(*) AS count FROM tts_requests GROUP BY user_id ORDER BY count DESC LIMIT 10"
    )
    top_users_result = await conn.execute(top_users_sql)
    top_users = [{"user_id": row["user_id"], "count": row["count"]} for row in top_users_result.mappings().all()]

    avg_duration = summary.get("avg_duration_ms")
    return {
        "total_requests": summary["total"],
        "completed": summary["completed"],
        "failed": summary["failed"],
        "cancelled": summary["cancelled"],
        "avg_duration_ms": round(float(avg_duration), 1) if avg_duration is not None else None,
        "requests_by_status": requests_by_status,
        "requests_by_character": requests_by_character,
        "top_users": top_users,
    }


async def fail_stale_requests(conn: AsyncConnection) -> int:
    """Mark any pending or processing requests as failed. Used on startup to clean up after crashes."""
    sql = text("UPDATE tts_requests SET status = 'failed' WHERE status IN ('pending', 'processing') RETURNING id")
    result = await conn.execute(sql)
    return len(result.fetchall())
