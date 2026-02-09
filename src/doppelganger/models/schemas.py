"""Pydantic request and response models for the API."""

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str
    database: str
    tts_model: str
    gpu_available: bool


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
    blacklisted: bool
    created_at: datetime


class CharacterResponse(BaseModel):
    """Response model for a character record."""

    id: int
    name: str
    reference_audio_path: str
    created_at: datetime


class TTSRequestCreate(BaseModel):
    """Request model for creating a TTS request."""

    character_voice: str
    text: str = Field(max_length=255)


class TTSRequestResponse(BaseModel):
    """Response model for a TTS request record."""

    id: int
    user_id: int
    character_voice: str
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
