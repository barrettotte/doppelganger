"""User management API endpoints."""

import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request

from doppelganger.db.queries.tts_requests import list_tts_requests_by_user
from doppelganger.db.queries.users import get_user, list_users, set_user_blacklisted
from doppelganger.models.tts import TTSRequestListResponse, TTSRequestResponse
from doppelganger.models.users import (
    BlacklistRequest,
    UserListResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_all_users(request: Request) -> UserListResponse:
    """List all registered users."""
    async with request.app.state.db_engine.connect() as conn:
        rows = await list_users(conn)

    users = [UserResponse(**asdict(row)) for row in rows]
    return UserListResponse(users=users, count=len(users))


@router.post("/{user_id}/blacklist", response_model=UserResponse)
async def toggle_blacklist(request: Request, user_id: int, body: BlacklistRequest) -> UserResponse:
    """Toggle a user's blacklisted status."""
    async with request.app.state.db_engine.begin() as conn:
        row = await set_user_blacklisted(conn, user_id, blacklisted=body.blacklisted)

    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(**asdict(row))


@router.get("/{user_id}/requests", response_model=TTSRequestListResponse)
async def get_user_requests(
    request: Request,
    user_id: int,
    status: str | None = Query(default=None, description="Filter by request status"),
) -> TTSRequestListResponse:
    """List TTS requests for a specific user."""
    async with request.app.state.db_engine.connect() as conn:
        user = await get_user(conn, user_id)

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        rows = await list_tts_requests_by_user(conn, user_id, status=status)

    requests_list = [TTSRequestResponse(**asdict(row)) for row in rows]
    return TTSRequestListResponse(requests=requests_list, count=len(requests_list), total=len(requests_list))
