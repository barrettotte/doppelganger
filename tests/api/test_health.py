"""Tests for the health check endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """Health endpoint should return 200."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_reports_db_connected(app: MagicMock, client: AsyncClient) -> None:
    """Health should report database as connected when engine is available."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    app.state.db_engine.connect = MagicMock(return_value=mock_conn)

    response = await client.get("/health")
    data = response.json()
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_health_reports_tts_not_loaded(client: AsyncClient) -> None:
    """Health should report TTS model as not loaded by default."""
    response = await client.get("/health")
    data = response.json()
    assert data["tts_model"] == "not_loaded"
    assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_includes_request_id(client: AsyncClient) -> None:
    """Health response should include X-Request-ID header."""
    response = await client.get("/health")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0
