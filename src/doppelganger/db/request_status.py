"""Enum for TTS request lifecycle statuses."""

from enum import StrEnum


class RequestStatus(StrEnum):
    """Status values for the tts_requests table."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
