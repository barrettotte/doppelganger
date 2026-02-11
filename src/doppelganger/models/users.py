"""Request and response models for user management."""

from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    """Response model for a user record."""

    id: int
    discord_id: str
    username: str | None = None
    blacklisted: bool
    created_at: datetime


class UserListResponse(BaseModel):
    """Response model for listing all users."""

    users: list[UserResponse]
    count: int


class BlacklistRequest(BaseModel):
    """Request model for toggling a user's blacklist status."""

    blacklisted: bool
