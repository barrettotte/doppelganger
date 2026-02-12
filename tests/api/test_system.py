"""Tests for the system stats API endpoint."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@dataclass
class _MockQueueState:
    """Simplified queue state for testing."""

    depth: int = 0


@pytest.mark.asyncio
async def test_system_stats_basic(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/system/stats returns system stats."""
    app.state._started_at = 0.0
    app.state.tts_service.engine_statuses.return_value = [
        {"engine": "chatterbox", "loaded": True, "device": "cuda"},
    ]

    bot = MagicMock()
    bot.tts_queue.get_state.return_value = _MockQueueState(depth=2)
    app.state.bot = bot

    # Put some data in the cache to test counters
    app.state.audio_cache.put("gandalf", "hello", b"wav-data")
    app.state.audio_cache.get("gandalf", "hello")  # hit
    app.state.audio_cache.get("gandalf", "missing")  # miss

    with patch("doppelganger.api.system.get_gpu_stats", return_value=[]):
        response = await client.get("/api/system/stats")

    assert response.status_code == 200
    data = response.json()

    assert data["uptime_seconds"] > 0
    assert data["engines"] == [{"engine": "chatterbox", "loaded": True, "device": "cuda"}]
    assert data["cache_hits"] == 1
    assert data["cache_misses"] == 1
    assert data["cache_hit_rate"] == 0.5
    assert data["cache_size"] == 1
    assert data["cache_total_bytes"] > 0
    assert data["queue_depth"] == 2
    assert data["gpus"] == []


@pytest.mark.asyncio
async def test_system_stats_with_gpu(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/system/stats includes GPU info when available."""
    app.state._started_at = 0.0
    app.state.tts_service.engine_statuses.return_value = []

    if hasattr(app.state, "bot"):
        del app.state.bot

    gpu_data = [
        {
            "index": 0,
            "name": "RTX 3090 Ti",
            "vram_used_mb": 4096,
            "vram_total_mb": 24576,
            "vram_percent": 16.7,
            "utilization_percent": 45.0,
            "temperature_c": 72,
        }
    ]

    with patch("doppelganger.api.system.get_gpu_stats", return_value=gpu_data):
        response = await client.get("/api/system/stats")

    assert response.status_code == 200
    data = response.json()

    assert len(data["gpus"]) == 1
    gpu = data["gpus"][0]
    assert gpu["name"] == "RTX 3090 Ti"
    assert gpu["vram_used_mb"] == 4096
    assert gpu["vram_total_mb"] == 24576
    assert gpu["utilization_percent"] == 45.0
    assert gpu["temperature_c"] == 72


@pytest.mark.asyncio
async def test_system_stats_no_bot(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/system/stats works when bot is not running."""
    app.state._started_at = 0.0
    app.state.tts_service.engine_statuses.return_value = []

    if hasattr(app.state, "bot"):
        del app.state.bot

    with patch("doppelganger.api.system.get_gpu_stats", return_value=[]):
        response = await client.get("/api/system/stats")

    assert response.status_code == 200
    assert response.json()["queue_depth"] == 0


@pytest.mark.asyncio
async def test_system_stats_no_started_at(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/system/stats handles missing _started_at gracefully."""
    app.state.tts_service.engine_statuses.return_value = []

    if hasattr(app.state, "bot"):
        del app.state.bot

    with patch("doppelganger.api.system.get_gpu_stats", return_value=[]):
        response = await client.get("/api/system/stats")

    assert response.status_code == 200
    assert response.json()["uptime_seconds"] == 0.0
