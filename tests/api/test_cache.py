"""Tests for the cache management API endpoints."""

from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from doppelganger.tts.cache import AudioCache


@pytest.mark.asyncio
async def test_get_cache_empty(client: AsyncClient) -> None:
    """GET /api/cache returns empty state."""
    response = await client.get("/api/cache")
    assert response.status_code == 200

    data = response.json()
    assert data["enabled"] is True
    assert data["entry_count"] == 0
    assert data["total_bytes"] == 0
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_get_cache_populated(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/cache returns entries after put."""
    cache: AudioCache = app.state.audio_cache
    cache.put("gandalf", "hello", b"wav-data-here")

    response = await client.get("/api/cache")
    assert response.status_code == 200

    data = response.json()
    assert data["entry_count"] == 1
    assert data["total_bytes"] == len(b"wav-data-here")
    assert len(data["entries"]) == 1

    entry = data["entries"][0]
    assert entry["character"] == "gandalf"
    assert entry["text"] == "hello"
    assert entry["byte_size"] == len(b"wav-data-here")
    assert entry["created_at"] > 0
    assert len(entry["key"]) == 64  # sha256 hex


@pytest.mark.asyncio
async def test_toggle_disable(client: AsyncClient, app: MagicMock) -> None:
    """POST /api/cache/toggle disables the cache."""
    response = await client.post("/api/cache/toggle", json={"enabled": False})
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "disabled" in data["message"]

    cache: AudioCache = app.state.audio_cache
    assert cache.enabled is False


@pytest.mark.asyncio
async def test_toggle_enable(client: AsyncClient, app: MagicMock) -> None:
    """POST /api/cache/toggle enables the cache."""
    cache: AudioCache = app.state.audio_cache
    cache.set_enabled(False)

    response = await client.post("/api/cache/toggle", json={"enabled": True})
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "enabled" in data["message"]
    assert cache.enabled is True


@pytest.mark.asyncio
async def test_flush_cache(client: AsyncClient, app: MagicMock) -> None:
    """POST /api/cache/flush clears all entries."""
    cache: AudioCache = app.state.audio_cache
    cache.put("a", "1", b"data1")
    cache.put("b", "2", b"data2")

    response = await client.post("/api/cache/flush")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "2" in data["message"]
    assert cache.size == 0


@pytest.mark.asyncio
async def test_flush_empty_cache(client: AsyncClient) -> None:
    """POST /api/cache/flush on empty cache succeeds."""
    response = await client.post("/api/cache/flush")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "0" in data["message"]


@pytest.mark.asyncio
async def test_delete_existing_entry(client: AsyncClient, app: MagicMock) -> None:
    """DELETE /api/cache/{key} removes an entry."""
    cache: AudioCache = app.state.audio_cache
    cache.put("gandalf", "hello", b"wav-data")
    key = AudioCache._make_key("gandalf", "hello")

    response = await client.delete(f"/api/cache/{key}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert cache.size == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_entry(client: AsyncClient) -> None:
    """DELETE /api/cache/{key} returns 404 for missing key."""
    response = await client.delete("/api/cache/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_existing_entry(client: AsyncClient, app: MagicMock) -> None:
    """GET /api/cache/{key}/download returns WAV bytes."""
    cache: AudioCache = app.state.audio_cache
    audio = b"RIFF....WAVEfmt "
    cache.put("gandalf", "hello", audio)
    key = AudioCache._make_key("gandalf", "hello")

    response = await client.get(f"/api/cache/{key}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content == audio


@pytest.mark.asyncio
async def test_download_nonexistent_entry(client: AsyncClient) -> None:
    """GET /api/cache/{key}/download returns 404 for missing key."""
    response = await client.get("/api/cache/nonexistent/download")
    assert response.status_code == 404
