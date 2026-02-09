"""Database queries for the audit_log table."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def create_audit_entry(
    conn: AsyncConnection,
    action: str,
    *,
    user_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Insert an audit log entry and return the created row."""
    sql = text("INSERT INTO audit_log (user_id, action, details) VALUES (:user_id, :action, :details) RETURNING *")
    params = {
        "user_id": user_id,
        "action": action,
        "details": json.dumps(details) if details is not None else None,
    }

    result = await conn.execute(sql, params)
    return dict(result.mappings().one())


async def list_audit_entries(conn: AsyncConnection, *, limit: int = 100) -> list[dict[str, Any]]:
    """Fetch recent audit log entries."""
    sql = text("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT :limit")
    params = {"limit": limit}

    result = await conn.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]
