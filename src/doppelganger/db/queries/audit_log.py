"""Database queries for the audit_log table."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from doppelganger.db.types import AuditLogRow


async def create_audit_entry(
    conn: AsyncConnection,
    action: str,
    *,
    user_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLogRow:
    """Insert an audit log entry and return the created row."""
    sql = text("INSERT INTO audit_log (user_id, action, details) VALUES (:user_id, :action, :details) RETURNING *")
    params: dict[str, Any] = {
        "user_id": user_id,
        "action": action,
        "details": json.dumps(details) if details is not None else None,
    }

    result = await conn.execute(sql, params)
    return AuditLogRow(**result.mappings().one())


async def list_audit_entries(
    conn: AsyncConnection, *, limit: int = 100, action: str | None = None
) -> list[AuditLogRow]:
    """Fetch recent audit log entries with optional action filter."""
    if action is not None:
        sql = text("SELECT * FROM audit_log WHERE action = :action ORDER BY created_at DESC LIMIT :limit")
        params: dict[str, Any] = {"limit": limit, "action": action}
        result = await conn.execute(sql, params)
    else:
        sql = text("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT :limit")
        result = await conn.execute(sql, {"limit": limit})

    return [AuditLogRow(**row) for row in result.mappings().all()]
