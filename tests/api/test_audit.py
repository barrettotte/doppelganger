"""Tests for the audit log API endpoints."""

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from tests.conftest import mock_db_connect_list

_NOW = datetime(2026, 1, 1)


@pytest.mark.asyncio
async def test_list_audit_empty(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/audit returns empty list when no entries exist."""
    app.state.db_engine = mock_db_connect_list([])

    response = await client.get("/api/audit")
    assert response.status_code == 200

    data = response.json()
    assert data["entries"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_list_audit_populated(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/audit returns audit entries with parsed JSON details."""
    app.state.db_engine = mock_db_connect_list(
        [
            {
                "id": 1,
                "user_id": 1,
                "action": "tts_generate",
                "details": json.dumps({"character": "gandalf"}),
                "created_at": _NOW,
            },
            {
                "id": 2,
                "user_id": None,
                "action": "bot_started",
                "details": None,
                "created_at": _NOW,
            },
        ]
    )

    response = await client.get("/api/audit")
    data = response.json()
    assert data["count"] == 2
    assert data["entries"][0]["action"] == "tts_generate"
    assert data["entries"][0]["details"] == {"character": "gandalf"}
    assert data["entries"][1]["details"] is None


@pytest.mark.asyncio
async def test_list_audit_with_action_filter(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/audit?action=tts_generate passes filter to the query."""
    app.state.db_engine = mock_db_connect_list(
        [
            {
                "id": 1,
                "user_id": 1,
                "action": "tts_generate",
                "details": None,
                "created_at": _NOW,
            },
        ]
    )

    response = await client.get("/api/audit?action=tts_generate")
    assert response.status_code == 200
    assert response.json()["count"] == 1


@pytest.mark.asyncio
async def test_list_audit_with_limit(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/audit?limit=10 passes limit to the query."""
    app.state.db_engine = mock_db_connect_list([])

    response = await client.get("/api/audit?limit=10")
    assert response.status_code == 200
