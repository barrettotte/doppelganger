"""Tests for the characters API endpoints."""

import io
import wave
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

_NOW = datetime(2026, 1, 1)


def _make_wav_bytes(duration_seconds: float = 10.0, sample_rate: int = 22050) -> bytes:
    """Create valid WAV bytes for upload."""
    buf = io.BytesIO()
    n_frames = int(sample_rate * duration_seconds)

    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00" * (n_frames * 2))

    return buf.getvalue()


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


@pytest.mark.asyncio
async def test_list_empty(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/characters returns empty list when no characters exist."""
    app.state.db_engine = _mock_db_for_list([])

    response = await client.get("/api/characters")
    assert response.status_code == 200

    data = response.json()
    assert data["characters"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_list_populated(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/characters returns characters with IDs from the database."""
    app.state.db_engine = _mock_db_for_list(
        [
            {"id": 1, "name": "gandalf", "reference_audio_path": "/voices/gandalf/reference.wav", "created_at": _NOW},
            {"id": 2, "name": "gollum", "reference_audio_path": "/voices/gollum/reference.wav", "created_at": _NOW},
        ]
    )

    response = await client.get("/api/characters")
    data = response.json()
    assert data["count"] == 2
    assert data["characters"][0]["name"] == "gandalf"
    assert data["characters"][0]["id"] == 1
    assert data["characters"][1]["name"] == "gollum"
    assert data["characters"][1]["id"] == 2


@pytest.mark.asyncio
async def test_delete_not_found(app: MagicMock, client: AsyncClient) -> None:
    """DELETE /api/characters/999 returns 404 when not found."""
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = None
    mock_conn.execute = AsyncMock(return_value=mock_result)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    app.state.db_engine.begin = MagicMock(return_value=mock_conn)

    response = await client.delete("/api/characters/999")
    assert response.status_code == 404
