"""Bot status and metrics API endpoints."""

import logging
import time

from fastapi import APIRouter, Request

from doppelganger.db.queries.tts_requests import get_request_metrics
from doppelganger.models.status import (
    BotStatusResponse,
    GuildInfo,
    MetricsResponse,
    TopUserEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status(request: Request) -> BotStatusResponse:
    """Return the current bot connection status and config summary."""
    bot = getattr(request.app.state, "bot", None)

    if bot is None or not bot.is_ready():
        return BotStatusResponse(connected=False)

    uptime = time.monotonic() - bot._started_at
    guilds = [GuildInfo(id=str(g.id), name=g.name, member_count=g.member_count or 0) for g in bot.guilds]
    tts_service = getattr(request.app.state, "tts_service", None)

    config = {
        "max_text_length": bot.settings.max_text_length,
        "cooldown_seconds": bot.settings.cooldown_seconds,
        "max_queue_depth": bot.settings.max_queue_depth,
        "requests_per_minute": bot.settings.requests_per_minute,
        "required_role_id": bot.settings.required_role_id or "(none)",
        "tts_device": tts_service.device if tts_service else "unknown",
    }

    username = str(bot.user) if bot.user else None
    return BotStatusResponse(
        connected=True,
        username=username,
        guild_count=len(guilds),
        guilds=guilds,
        uptime_seconds=round(uptime, 1),
        config=config,
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(request: Request) -> MetricsResponse:
    """Return aggregated TTS request metrics."""

    async with request.app.state.db_engine.connect() as conn:
        metrics = await get_request_metrics(conn)

    bot = getattr(request.app.state, "bot", None)
    queue_depth = 0
    if bot is not None:
        state = bot.tts_queue.get_state()
        queue_depth = state.depth

    cache = getattr(request.app.state, "audio_cache", None)
    cache_size = cache.size if cache is not None else 0

    registry = getattr(request.app.state, "voice_registry", None)
    voices_loaded = len(registry.list_voices()) if registry is not None else 0

    top_users = [TopUserEntry(**u) for u in metrics.get("top_users", [])]

    return MetricsResponse(
        total_requests=metrics["total_requests"],
        completed=metrics["completed"],
        failed=metrics["failed"],
        cancelled=metrics["cancelled"],
        avg_duration_ms=metrics["avg_duration_ms"],
        requests_by_status=metrics["requests_by_status"],
        requests_by_character=metrics["requests_by_character"],
        top_users=top_users,
        queue_depth=queue_depth,
        cache_size=cache_size,
        voices_loaded=voices_loaded,
    )
