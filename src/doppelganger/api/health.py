"""Health check endpoint for monitoring service status."""

import importlib

from fastapi import APIRouter, Request
from sqlalchemy import text

from doppelganger.models.schemas import HealthResponse

router = APIRouter()


def _check_gpu() -> bool:
    """Check if a CUDA GPU is available via torch."""
    try:
        torch = importlib.import_module("torch")
        return bool(torch.cuda.is_available())
    except ImportError:
        return False


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Check database connectivity, TTS model state, and GPU availability."""
    db_status = "disconnected"
    engine = getattr(request.app.state, "db_engine", None)

    if engine is not None:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            db_status = "connected"
        except Exception:
            db_status = "disconnected"

    tts_status = "not_loaded"
    if getattr(request.app.state, "tts_ready", False):
        tts_status = "loaded"

    gpu_available = _check_gpu()

    if db_status == "connected" and tts_status == "loaded":
        status = "healthy"
    else:
        status = "degraded"

    voice_registry = getattr(request.app.state, "voice_registry", None)
    voices_loaded = voice_registry.size if voice_registry is not None else 0

    audio_cache = getattr(request.app.state, "audio_cache", None)
    cache_size = audio_cache.size if audio_cache is not None else 0

    return HealthResponse(
        status=status,
        database=db_status,
        tts_model=tts_status,
        gpu_available=gpu_available,
        voices_loaded=voices_loaded,
        cache_size=cache_size,
    )
