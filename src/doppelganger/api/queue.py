"""Queue management API endpoints for dashboard consumption."""

import logging
from dataclasses import asdict

from fastapi import APIRouter, Request

from doppelganger.db.queries.tts_requests import update_tts_request_status
from doppelganger.models.queue import QueueActionResponse, QueueStateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.get("", response_model=QueueStateResponse)
async def get_queue_state(request: Request) -> QueueStateResponse:
    """Return the current TTS request queue state."""

    bot = getattr(request.app.state, "bot", None)
    if bot is None:
        return QueueStateResponse(depth=0, max_depth=0, processing=None, pending=[])

    state = bot.tts_queue.get_state()
    return QueueStateResponse(**asdict(state))


@router.post("/{request_id}/cancel", response_model=QueueActionResponse)
async def cancel_request(request: Request, request_id: int) -> QueueActionResponse:
    """Cancel a pending request in the queue."""

    bot = getattr(request.app.state, "bot", None)
    if bot is None:
        return QueueActionResponse(success=False, message="Bot is not running")

    cancelled = await bot.tts_queue.cancel(request_id)
    if not cancelled:
        return QueueActionResponse(success=False, message="Request not found in queue")

    try:
        async with bot.db_engine.begin() as conn:
            await update_tts_request_status(conn, request_id, "cancelled")

    except Exception:
        logger.warning("Failed to update DB status for cancelled request %d", request_id)

    return QueueActionResponse(success=True, message=f"Request {request_id} cancelled")


@router.post("/{request_id}/bump", response_model=QueueActionResponse)
async def bump_request(request: Request, request_id: int) -> QueueActionResponse:
    """Move a pending request to the front of the queue."""

    bot = getattr(request.app.state, "bot", None)
    if bot is None:
        return QueueActionResponse(success=False, message="Bot is not running")

    bumped = await bot.tts_queue.bump(request_id)
    if not bumped:
        return QueueActionResponse(success=False, message="Request not found in queue")

    return QueueActionResponse(success=True, message=f"Request {request_id} moved to front of queue")
