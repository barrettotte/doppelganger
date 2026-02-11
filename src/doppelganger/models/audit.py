"""Response models for the audit log."""

from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Response model for an audit log entry."""

    id: int
    user_id: int | None
    action: str
    details: dict[str, str | int | bool | None] | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Response model for listing audit log entries."""

    entries: list[AuditLogResponse]
    count: int
