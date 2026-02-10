"""Dataclass definitions for database row types."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserRow:
    """Row returned by queries against the users table."""

    id: int
    discord_id: str
    blacklisted: bool
    created_at: datetime


@dataclass
class CharacterRow:
    """Row returned by queries against the characters table."""

    id: int
    name: str
    reference_audio_path: str
    created_at: datetime


@dataclass
class TTSRequestRow:
    """Row returned by queries against the tts_requests table."""

    id: int
    user_id: int
    character: str
    text: str
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None


@dataclass
class AuditLogRow:
    """Row returned by queries against the audit_log table."""

    id: int
    user_id: int | None
    action: str
    details: str | None
    created_at: datetime
