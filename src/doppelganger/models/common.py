"""Shared response models for health checks and error responses."""

from pydantic import BaseModel


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
