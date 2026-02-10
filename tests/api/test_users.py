"""Tests for the users API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

_NOW = datetime(2026, 1, 1)


def _mock_db_for_list(rows: list[dict[str, object]]) -> MagicMock:
    """Create a mock DB engine whose connect().execute().mappings().all() returns the given rows."""
    engine = MagicMock()
    conn = AsyncMock()
    execute_result = MagicMock()
    execute_result.mappings.return_value.all.return_value = rows
    conn.execute = AsyncMock(return_value=execute_result)

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    return engine


def _mock_db_for_single(row: dict[str, object] | None) -> MagicMock:
    """Create a mock DB engine whose connect().execute().mappings().first() returns a single row."""
    engine = MagicMock()
    conn = AsyncMock()
    execute_result = MagicMock()
    execute_result.mappings.return_value.first.return_value = row
    conn.execute = AsyncMock(return_value=execute_result)

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    return engine


def _mock_db_for_begin_single(row: dict[str, object] | None) -> MagicMock:
    """Create a mock DB engine whose begin().execute().mappings().first() returns a single row."""
    engine = MagicMock()
    conn = AsyncMock()
    execute_result = MagicMock()
    execute_result.mappings.return_value.first.return_value = row
    conn.execute = AsyncMock(return_value=execute_result)

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.begin.return_value = ctx
    return engine


@pytest.mark.asyncio
async def test_list_users_empty(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/users returns empty list when no users exist."""
    app.state.db_engine = _mock_db_for_list([])

    response = await client.get("/api/users")
    assert response.status_code == 200

    data = response.json()
    assert data["users"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_list_users_populated(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/users returns users from the database."""
    app.state.db_engine = _mock_db_for_list(
        [
            {"id": 1, "discord_id": "111", "blacklisted": False, "created_at": _NOW},
            {"id": 2, "discord_id": "222", "blacklisted": True, "created_at": _NOW},
        ]
    )

    response = await client.get("/api/users")
    data = response.json()
    assert data["count"] == 2
    assert data["users"][0]["discord_id"] == "111"
    assert data["users"][1]["blacklisted"] is True


@pytest.mark.asyncio
async def test_blacklist_user(app: MagicMock, client: AsyncClient) -> None:
    """POST /api/users/{id}/blacklist toggles blacklist status."""
    app.state.db_engine = _mock_db_for_begin_single(
        {"id": 1, "discord_id": "111", "blacklisted": True, "created_at": _NOW}
    )
    response = await client.post("/api/users/1/blacklist", json={"blacklisted": True})
    assert response.status_code == 200
    assert response.json()["blacklisted"] is True


@pytest.mark.asyncio
async def test_blacklist_user_not_found(app: MagicMock, client: AsyncClient) -> None:
    """POST /api/users/{id}/blacklist returns 404 for unknown user."""
    app.state.db_engine = _mock_db_for_begin_single(None)
    response = await client.post("/api/users/999/blacklist", json={"blacklisted": True})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_user_requests(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/users/{id}/requests returns user's TTS request history."""
    user_row = {"id": 1, "discord_id": "111", "blacklisted": False, "created_at": _NOW}
    request_rows = [
        {
            "id": 10,
            "user_id": 1,
            "character": "gandalf",
            "text": "hello",
            "status": "completed",
            "created_at": _NOW,
            "started_at": _NOW,
            "completed_at": _NOW,
            "duration_ms": 500,
        }
    ]

    # The endpoint makes two queries: first get_user, then list_tts_requests_by_user
    engine = MagicMock()
    conn = AsyncMock()

    # First call returns user row (mappings().first()), second returns request list (mappings().all())
    first_result = MagicMock()
    first_result.mappings.return_value.first.return_value = user_row

    second_result = MagicMock()
    second_result.mappings.return_value.all.return_value = request_rows

    conn.execute = AsyncMock(side_effect=[first_result, second_result])

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    app.state.db_engine = engine

    response = await client.get("/api/users/1/requests")
    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 1
    assert data["requests"][0]["character"] == "gandalf"


@pytest.mark.asyncio
async def test_user_requests_user_not_found(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/users/{id}/requests returns 404 for unknown user."""
    app.state.db_engine = _mock_db_for_single(None)
    response = await client.get("/api/users/999/requests")
    assert response.status_code == 404
