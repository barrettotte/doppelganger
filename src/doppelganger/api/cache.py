"""Cache management endpoints for viewing and controlling the audio cache."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from doppelganger.models.cache import (
    CacheActionResponse,
    CacheEntryResponse,
    CacheStateResponse,
    CacheToggleRequest,
)
from doppelganger.tts.cache import AudioCache

router = APIRouter(prefix="/api/cache", tags=["cache"])


def _get_cache(request: Request) -> AudioCache:
    """Retrieve the audio cache from app state."""
    cache: AudioCache | None = getattr(request.app.state, "audio_cache", None)
    if cache is None:
        raise HTTPException(status_code=503, detail="Audio cache not available")
    return cache


@router.get("", response_model=CacheStateResponse)
async def get_cache_state(request: Request) -> CacheStateResponse:
    """Return the full cache state including all entries."""
    cache = _get_cache(request)
    entries = [
        CacheEntryResponse(
            key=e.key,
            character=e.character,
            text=e.text,
            byte_size=e.byte_size,
            created_at=e.created_at,
        )
        for e in cache.list_entries()
    ]
    return CacheStateResponse(
        enabled=cache.enabled,
        entry_count=cache.size,
        max_size=cache.max_size,
        total_bytes=cache.total_bytes,
        entries=entries,
    )


@router.post("/toggle", response_model=CacheActionResponse)
async def toggle_cache(request: Request, body: CacheToggleRequest) -> CacheActionResponse:
    """Enable or disable the audio cache."""
    cache = _get_cache(request)
    cache.set_enabled(body.enabled)
    state = "enabled" if body.enabled else "disabled"
    return CacheActionResponse(success=True, message=f"Cache {state}")


@router.post("/flush", response_model=CacheActionResponse)
async def flush_cache(request: Request) -> CacheActionResponse:
    """Clear all entries from the cache."""
    cache = _get_cache(request)
    count = cache.size
    cache.clear()
    return CacheActionResponse(success=True, message=f"Flushed {count} entries")


@router.delete("/{key}", response_model=CacheActionResponse)
async def delete_cache_entry(request: Request, key: str) -> CacheActionResponse:
    """Remove a single cache entry by key."""
    cache = _get_cache(request)

    if not cache.remove(key):
        raise HTTPException(status_code=404, detail="Cache entry not found")
    return CacheActionResponse(success=True, message="Entry removed")


@router.get("/{key}/download")
async def download_cache_entry(request: Request, key: str) -> Response:
    """Download a cached audio file as WAV."""
    cache = _get_cache(request)
    entry = cache.get_entry(key)

    if entry is None:
        raise HTTPException(status_code=404, detail="Cache entry not found")

    return Response(
        content=entry.audio_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="{entry.character}_{key[:8]}.wav"'},
    )
