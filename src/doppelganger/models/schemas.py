"""Pydantic request and response models for the API."""

from datetime import datetime

from pydantic import BaseModel, Field


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


class CharacterVoiceResponse(BaseModel):
    """Response model for a voice registry entry."""

    name: str
    reference_audio_path: str


class CharacterListResponse(BaseModel):
    """Response model for listing all characters."""

    characters: list[CharacterVoiceResponse]
    count: int


class TTSGenerateRequest(BaseModel):
    """Request model for TTS generation."""

    character: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    text: str = Field(min_length=1, max_length=500)


class CharacterCreateRequest(BaseModel):
    """Request model for creating a character (name field for multipart)."""

    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
