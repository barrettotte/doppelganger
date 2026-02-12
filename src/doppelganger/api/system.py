"""System stats API endpoint."""

import time

from fastapi import APIRouter, Request

from doppelganger.models.system import EngineStatus, GpuInfo, SystemStatsResponse
from doppelganger.tts.gpu import get_gpu_stats

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(request: Request) -> SystemStatsResponse:
    """Return system-level stats including GPU, engines, cache, and uptime."""
    started_at = getattr(request.app.state, "_started_at", None)
    uptime = time.monotonic() - started_at if started_at is not None else 0.0

    gpu_data = get_gpu_stats()
    gpus = [GpuInfo(**g) for g in gpu_data]

    tts_service = getattr(request.app.state, "tts_service", None)
    engines: list[EngineStatus] = []
    if tts_service is not None:
        engines = [EngineStatus(**e) for e in tts_service.engine_statuses()]

    cache = getattr(request.app.state, "audio_cache", None)
    cache_hits = cache.hits if cache is not None else 0
    cache_misses = cache.misses if cache is not None else 0
    cache_hit_rate = cache.hit_rate if cache is not None else 0.0
    cache_size = cache.size if cache is not None else 0
    cache_total_bytes = cache.total_bytes if cache is not None else 0

    bot = getattr(request.app.state, "bot", None)
    queue_depth = 0
    if bot is not None:
        state = bot.tts_queue.get_state()
        queue_depth = state.depth

    registry = getattr(request.app.state, "voice_registry", None)
    voices_loaded = len(registry.list_voices()) if registry is not None else 0

    return SystemStatsResponse(
        uptime_seconds=round(uptime, 1),
        gpus=gpus,
        engines=engines,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        cache_hit_rate=round(cache_hit_rate, 4),
        cache_size=cache_size,
        cache_total_bytes=cache_total_bytes,
        queue_depth=queue_depth,
        voices_loaded=voices_loaded,
    )
