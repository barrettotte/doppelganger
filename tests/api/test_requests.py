"""Tests for the TTS requests API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

_NOW = datetime(2026, 1, 1)


def _mock_db_for_requests(rows: list[dict[str, object]], count: int | None = None) -> MagicMock:
    """Create a mock DB engine for request listing (count query + list query)."""
    engine = MagicMock()
    conn = AsyncMock()

    # First call: count_tts_requests -> mappings().first()
    count_result = MagicMock()
    count_result.mappings.return_value.first.return_value = {"cnt": count if count is not None else len(rows)}

    # Second call: list_tts_requests -> mappings().all()
    list_result = MagicMock()
    list_result.mappings.return_value.all.return_value = rows

    conn.execute = AsyncMock(side_effect=[count_result, list_result])

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    return engine


def _make_request_row(request_id: int = 1, status: str = "completed") -> dict[str, object]:
    """Create a mock TTS request row."""
    return {
        "id": request_id,
        "user_id": 1,
        "character": "gandalf",
        "text": "hello",
        "status": status,
        "created_at": _NOW,
        "started_at": _NOW,
        "completed_at": _NOW,
        "duration_ms": 500,
    }


@pytest.mark.asyncio
async def test_list_requests_empty(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/requests returns empty list when no requests exist."""
    app.state.db_engine = _mock_db_for_requests([])

    response = await client.get("/api/requests")
    assert response.status_code == 200

    data = response.json()
    assert data["requests"] == []
    assert data["count"] == 0
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_requests_populated(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/requests returns requests from the database."""
    rows = [_make_request_row(1), _make_request_row(2, status="failed")]
    app.state.db_engine = _mock_db_for_requests(rows)

    response = await client.get("/api/requests")
    data = response.json()
    assert data["count"] == 2
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_list_requests_with_limit(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/requests respects limit parameter."""
    rows = [_make_request_row(1), _make_request_row(2)]
    app.state.db_engine = _mock_db_for_requests(rows, count=5)

    response = await client.get("/api/requests?limit=2")
    data = response.json()
    assert data["count"] == 2
    assert data["total"] == 5


@pytest.mark.asyncio
async def test_get_single_request(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/requests/{id} returns a single request."""
    engine = MagicMock()
    conn = AsyncMock()
    execute_result = MagicMock()
    execute_result.mappings.return_value.first.return_value = _make_request_row(42)
    conn.execute = AsyncMock(return_value=execute_result)

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    app.state.db_engine = engine

    response = await client.get("/api/requests/42")
    assert response.status_code == 200
    assert response.json()["id"] == 42


@pytest.mark.asyncio
async def test_get_single_request_not_found(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/requests/{id} returns 404 for unknown request."""
    engine = MagicMock()
    conn = AsyncMock()
    execute_result = MagicMock()
    execute_result.mappings.return_value.first.return_value = None
    conn.execute = AsyncMock(return_value=execute_result)

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    app.state.db_engine = engine

    response = await client.get("/api/requests/999")
    assert response.status_code == 404
