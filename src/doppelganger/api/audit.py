"""Audit log API endpoints."""

import json
import logging
from dataclasses import asdict

from fastapi import APIRouter, Query, Request

from doppelganger.db.queries.audit_log import list_audit_entries
from doppelganger.models.schemas import AuditLogListResponse, AuditLogResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit(
    request: Request,
    action: str | None = Query(default=None, description="Filter by action type"),
    limit: int = Query(default=100, ge=1, le=500, description="Max entries to return"),
) -> AuditLogListResponse:
    """List audit log entries with optional action filter."""

    async with request.app.state.db_engine.connect() as conn:
        rows = await list_audit_entries(conn, limit=limit, action=action)

    entries = []
    for row in rows:
        row_dict = asdict(row)
        if row_dict["details"] is not None and isinstance(row_dict["details"], str):
            row_dict["details"] = json.loads(row_dict["details"])

        entries.append(AuditLogResponse(**row_dict))

    return AuditLogListResponse(entries=entries, count=len(entries))
