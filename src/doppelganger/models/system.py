"""Response models for system stats."""

from pydantic import BaseModel, Field


class GpuInfo(BaseModel):
    """GPU device information with VRAM and utilization stats."""

    index: int
    name: str
    vram_used_mb: int
    vram_total_mb: int
    vram_percent: float
    utilization_percent: float | None = None
    temperature_c: int | None = None


class EngineStatus(BaseModel):
    """Status of a single TTS engine."""

    engine: str
    loaded: bool
    device: str


class SystemStatsResponse(BaseModel):
    """Response model for system-level stats."""

    uptime_seconds: float
    gpus: list[GpuInfo] = Field(default_factory=list)
    engines: list[EngineStatus] = Field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    cache_size: int = 0
    cache_total_bytes: int = 0
    queue_depth: int = 0
    voices_loaded: int = 0
