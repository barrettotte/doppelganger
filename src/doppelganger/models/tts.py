"""Request and response models for TTS generation and characters."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


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


class TTSRequestListResponse(BaseModel):
    """Response model for listing TTS requests with pagination info."""

    requests: list[TTSRequestResponse]
    count: int
    total: int


class TTSGenerateRequest(_SanitizedTextMixin):
    """Request model for TTS generation."""

    character: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    text: str = Field(min_length=1, max_length=255)


class CharacterTuning(BaseModel):
    """Per-character TTS tuning overrides (null means use global default)."""

    exaggeration: float | None = None
    cfg_weight: float | None = None
    temperature: float | None = None
    repetition_penalty: float | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None


class CharacterResponse(BaseModel):
    """Response model for a character record."""

    id: int
    name: str
    reference_audio_path: str
    created_at: datetime
    engine: str = "chatterbox"
    tuning: CharacterTuning = Field(default_factory=CharacterTuning)


class CharacterListResponse(BaseModel):
    """Response model for listing all characters."""

    characters: list[CharacterResponse]
    count: int


class CharacterCreateRequest(BaseModel):
    """Request model for creating a character (name field for multipart)."""

    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
