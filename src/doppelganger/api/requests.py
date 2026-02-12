"""TTS request history API endpoints."""

import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request

from doppelganger.db.queries.tts_requests import (
    count_tts_requests,
    get_tts_request,
    list_tts_requests,
)
from doppelganger.db.request_status import RequestStatus
from doppelganger.models.tts import TTSRequestListResponse, TTSRequestResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.get("", response_model=TTSRequestListResponse)
async def list_all_requests(
    request: Request,
    status: str | None = Query(default=None, description="Filter by request status"),
    limit: int = Query(default=50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
) -> TTSRequestListResponse:
    """List TTS requests with optional status filter and pagination."""
    filter_status = RequestStatus(status) if status is not None else None

    async with request.app.state.db_engine.connect() as conn:
        total = await count_tts_requests(conn, status=filter_status)
        rows = await list_tts_requests(conn, status=filter_status, limit=limit, offset=offset)

    requests_list = [TTSRequestResponse(**asdict(row)) for row in rows]
    return TTSRequestListResponse(requests=requests_list, count=len(requests_list), total=total)


@router.get("/{request_id}", response_model=TTSRequestResponse)
async def get_single_request(request: Request, request_id: int) -> TTSRequestResponse:
    """Fetch a single TTS request by ID."""

    async with request.app.state.db_engine.connect() as conn:
        row = await get_tts_request(conn, request_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")

    return TTSRequestResponse(**asdict(row))
