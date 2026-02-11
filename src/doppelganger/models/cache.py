"""Request and response models for the audio cache."""

from pydantic import BaseModel


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
