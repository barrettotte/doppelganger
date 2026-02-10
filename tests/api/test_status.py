"""Tests for the bot status and metrics API endpoints."""

from dataclasses import dataclass
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

_NOW = datetime(2026, 1, 1)


@dataclass
class _MockQueueState:
    """Simplified queue state for testing."""

    depth: int = 0
    max_depth: int = 10
    processing: None = None
    pending: list = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Initialize default pending list."""
        if self.pending is None:
            self.pending = []


@pytest.mark.asyncio
async def test_status_no_bot(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/status returns disconnected when no bot is running."""
    if hasattr(app.state, "bot"):
        del app.state.bot

    response = await client.get("/api/status")
    assert response.status_code == 200

    data = response.json()
    assert data["connected"] is False


@pytest.mark.asyncio
async def test_status_bot_not_ready(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/status returns disconnected when bot is not ready."""
    bot = MagicMock()
    bot.is_ready.return_value = False
    app.state.bot = bot

    response = await client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["connected"] is False


@pytest.mark.asyncio
async def test_status_bot_connected(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/status returns connection info when bot is ready."""

    bot = MagicMock()
    bot.is_ready.return_value = True
    bot._started_at = 0.0
    bot.user = MagicMock()
    bot.user.__str__ = MagicMock(return_value="TestBot#1234")
    bot.settings.max_text_length = 500
    bot.settings.cooldown_seconds = 5
    bot.settings.max_queue_depth = 20
    bot.settings.requests_per_minute = 3
    bot.settings.required_role_id = ""

    guild = MagicMock()
    guild.id = 123
    guild.name = "Test Guild"
    guild.member_count = 42
    bot.guilds = [guild]

    tts_service = MagicMock()
    tts_service._settings.device = "cuda"
    app.state.tts_service = tts_service
    app.state.bot = bot

    response = await client.get("/api/status")
    assert response.status_code == 200

    data = response.json()
    assert data["connected"] is True
    assert data["username"] == "TestBot#1234"
    assert data["guild_count"] == 1
    assert data["guilds"][0]["name"] == "Test Guild"
    assert data["config"]["max_text_length"] == 500


def _mock_db_for_metrics() -> MagicMock:
    """Create a mock DB engine that returns metrics query results."""
    engine = MagicMock()
    conn = AsyncMock()

    # get_request_metrics makes 4 queries:
    # 1. summary (mappings().one())
    # 2. by_status (mappings().all())
    # 3. by_character (mappings().all())
    # 4. top_users (mappings().all())
    summary_result = MagicMock()
    summary_result.mappings.return_value.one.return_value = {
        "total": 100,
        "completed": 80,
        "failed": 15,
        "cancelled": 5,
        "avg_duration_ms": 1234.5,
    }

    by_status_result = MagicMock()
    by_status_result.mappings.return_value.all.return_value = [
        {"status": "completed", "count": 80},
        {"status": "failed", "count": 15},
        {"status": "cancelled", "count": 5},
    ]

    by_character_result = MagicMock()
    by_character_result.mappings.return_value.all.return_value = [
        {"character": "gandalf", "count": 50},
        {"character": "gollum", "count": 30},
    ]

    top_users_result = MagicMock()
    top_users_result.mappings.return_value.all.return_value = [
        {"user_id": 1, "count": 40},
        {"user_id": 2, "count": 30},
    ]

    conn.execute = AsyncMock(side_effect=[summary_result, by_status_result, by_character_result, top_users_result])

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    return engine


@pytest.mark.asyncio
async def test_metrics(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/metrics returns aggregated request statistics."""
    app.state.db_engine = _mock_db_for_metrics()

    bot = MagicMock()
    bot.tts_queue.get_state.return_value = _MockQueueState(depth=3)
    app.state.bot = bot

    response = await client.get("/api/metrics")
    assert response.status_code == 200

    data = response.json()
    assert data["total_requests"] == 100
    assert data["completed"] == 80
    assert data["failed"] == 15
    assert data["cancelled"] == 5
    assert data["avg_duration_ms"] == 1234.5
    assert data["requests_by_status"]["completed"] == 80
    assert data["requests_by_character"]["gandalf"] == 50
    assert len(data["top_users"]) == 2
    assert data["queue_depth"] == 3


@pytest.mark.asyncio
async def test_metrics_no_bot(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/metrics works when bot is not running."""
    app.state.db_engine = _mock_db_for_metrics()

    if hasattr(app.state, "bot"):
        del app.state.bot

    response = await client.get("/api/metrics")
    assert response.status_code == 200
    assert response.json()["queue_depth"] == 0
