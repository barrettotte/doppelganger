"""Response models for bot status and metrics."""

from pydantic import BaseModel, Field


class GuildInfo(BaseModel):
    """Basic info about a connected Discord guild."""

    id: str
    name: str
    member_count: int


class BotStatusResponse(BaseModel):
    """Response model for bot connection status."""

    connected: bool
    username: str | None = None
    guild_count: int = 0
    guilds: list[GuildInfo] = Field(default_factory=list)
    uptime_seconds: float | None = None
    config: dict[str, str | int | bool] = Field(default_factory=dict)


class TopUserEntry(BaseModel):
    """A user entry in the top-users metrics list."""

    user_id: int
    count: int


class MetricsResponse(BaseModel):
    """Response model for aggregated TTS metrics."""

    total_requests: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    avg_duration_ms: float | None = None
    requests_by_status: dict[str, int] = Field(default_factory=dict)
    requests_by_character: dict[str, int] = Field(default_factory=dict)
    top_users: list[TopUserEntry] = Field(default_factory=list)
    queue_depth: int = 0
    cache_size: int = 0
    voices_loaded: int = 0
