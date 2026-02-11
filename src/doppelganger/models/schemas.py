"""Pydantic request and response models for the API."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str
    database: str
    tts_model: str
    gpu_available: bool
    voices_loaded: int = 0
    cache_size: int = 0


class ErrorDetail(BaseModel):
    """Structured error detail returned by all error responses."""

    status_code: int
    message: str
    request_id: str = ""
    details: list[dict[str, str]] | None = None


class ErrorResponse(BaseModel):
    """Wrapper for error responses."""

    error: ErrorDetail


class UserResponse(BaseModel):
    """Response model for a user record."""

    id: int
    discord_id: str
    username: str | None = None
    blacklisted: bool
    created_at: datetime


class CharacterResponse(BaseModel):
    """Response model for a character record."""

    id: int
    name: str
    reference_audio_path: str
    created_at: datetime
    engine: str = "chatterbox"


def _sanitize_text(value: str) -> str:
    """Strip C0/C1 control characters, preserving tab, newline, and carriage return."""
    return _CONTROL_CHAR_RE.sub("", value)


class _SanitizedTextMixin(BaseModel):
    """Mixin that strips control characters from the text field."""

    @field_validator("text", check_fields=False)
    @classmethod
    def strip_control_chars(cls, v: str) -> str:
        """Remove control characters from the text field."""
        cleaned = _sanitize_text(v)

        if not cleaned.strip():
            msg = "Text must not be empty after sanitization"
            raise ValueError(msg)

        return cleaned


class TTSRequestCreate(_SanitizedTextMixin):
    """Request model for creating a TTS request."""

    character: str
    text: str = Field(max_length=255)


class TTSRequestResponse(BaseModel):
    """Response model for a TTS request record."""

    id: int
    user_id: int
    character: str
    text: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None


class AuditLogResponse(BaseModel):
    """Response model for an audit log entry."""

    id: int
    user_id: int | None
    action: str
    details: dict[str, str | int | bool | None] | None = None
    created_at: datetime


class CharacterListResponse(BaseModel):
    """Response model for listing all characters."""

    characters: list[CharacterResponse]
    count: int


class TTSGenerateRequest(_SanitizedTextMixin):
    """Request model for TTS generation."""

    character: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    text: str = Field(min_length=1, max_length=500)


class CharacterCreateRequest(BaseModel):
    """Request model for creating a character (name field for multipart)."""

    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class QueueItemResponse(BaseModel):
    """Response model for a single queue item."""

    request_id: int
    user_id: int
    discord_id: str
    character: str
    text: str
    submitted_at: float


class QueueStateResponse(BaseModel):
    """Response model for the current queue state."""

    depth: int
    max_depth: int
    processing: QueueItemResponse | None = None
    pending: list[QueueItemResponse]


class QueueActionResponse(BaseModel):
    """Response model for queue cancel/bump actions."""

    success: bool
    message: str


class UserListResponse(BaseModel):
    """Response model for listing all users."""

    users: list[UserResponse]
    count: int


class BlacklistRequest(BaseModel):
    """Request model for toggling a user's blacklist status."""

    blacklisted: bool


class TTSRequestListResponse(BaseModel):
    """Response model for listing TTS requests with pagination info."""

    requests: list[TTSRequestResponse]
    count: int
    total: int


class AuditLogListResponse(BaseModel):
    """Response model for listing audit log entries."""

    entries: list[AuditLogResponse]
    count: int


class GuildInfo(BaseModel):
    """Basic info about a connected Discord guild."""

    id: str
    name: str
    member_count: int


class BotStatusResponse(BaseModel):
    """Response model for bot connection status."""

    connected: bool
    username: str | None = None
    guild_count: int = 0
    guilds: list[GuildInfo] = Field(default_factory=list)
    uptime_seconds: float | None = None
    config: dict[str, str | int | bool] = Field(default_factory=dict)


class CacheEntryResponse(BaseModel):
    """Response model for a single cache entry."""

    key: str
    character: str
    text: str
    byte_size: int
    created_at: float


class CacheStateResponse(BaseModel):
    """Response model for full cache state including all entries."""

    enabled: bool
    entry_count: int
    max_size: int
    total_bytes: int
    entries: list[CacheEntryResponse]


class CacheToggleRequest(BaseModel):
    """Request model for enabling or disabling the cache."""

    enabled: bool


class CacheActionResponse(BaseModel):
    """Response model for cache mutation actions."""

    success: bool
    message: str


class TopUserEntry(BaseModel):
    """A user entry in the top-users metrics list."""

    user_id: int
    count: int


class MetricsResponse(BaseModel):
    """Response model for aggregated TTS metrics."""

    total_requests: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    avg_duration_ms: float | None = None
    requests_by_status: dict[str, int] = Field(default_factory=dict)
    requests_by_character: dict[str, int] = Field(default_factory=dict)
    top_users: list[TopUserEntry] = Field(default_factory=list)
    queue_depth: int = 0
    cache_size: int = 0
    voices_loaded: int = 0
