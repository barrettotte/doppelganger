"""Request and response models for the TTS request queue."""

from pydantic import BaseModel


class QueueItemResponse(BaseModel):
    """Response model for a single queue item."""

    request_id: int
    user_id: int
    discord_id: str
    character: str
    text: str
    submitted_at: float


class QueueStateResponse(BaseModel):
    """Response model for the current queue state."""

    depth: int
    max_depth: int
    processing: QueueItemResponse | None = None
    pending: list[QueueItemResponse]


class QueueActionResponse(BaseModel):
    """Response model for queue cancel/bump actions."""

    success: bool
    message: str
