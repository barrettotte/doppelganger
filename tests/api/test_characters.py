"""Tests for the characters API endpoints."""

import io
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from doppelganger.tts.voice_registry import VoiceRegistry


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


@pytest.mark.asyncio
async def test_list_empty(client: AsyncClient) -> None:
    """GET /api/characters returns empty list when no voices registered."""
    response = await client.get("/api/characters")
    assert response.status_code == 200

    data = response.json()
    assert data["characters"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_list_populated(app: MagicMock, client: AsyncClient, tmp_path: Path) -> None:
    """GET /api/characters returns registered voices."""
    voices_dir = tmp_path / "list-voices"
    voices_dir.mkdir()
    char_dir = voices_dir / "shane-gillis"
    char_dir.mkdir()
    (char_dir / "reference.wav").write_bytes(b"RIFF" + b"\x00" * 100)

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()
    app.state.voice_registry = registry

    response = await client.get("/api/characters")
    data = response.json()
    assert data["count"] == 1
    assert data["characters"][0]["name"] == "shane-gillis"


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
