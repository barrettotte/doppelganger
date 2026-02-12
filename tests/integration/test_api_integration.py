"""Integration tests for API endpoints against a real Postgres."""

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from doppelganger.app import create_app
from doppelganger.tts.cache import AudioCache
from doppelganger.tts.voice_registry import VoiceRegistry
from tests.conftest import make_wav_bytes

pytestmark = pytest.mark.integration


@pytest.fixture
def integration_app(async_engine: AsyncEngine, tmp_path: Path) -> MagicMock:
    """Create the FastAPI app backed by a real async engine."""
    application = create_app()

    voices_dir = tmp_path / "voices"
    voices_dir.mkdir()

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()

    application.state.db_engine = async_engine
    application.state.tts_ready = False
    application.state.tts_service = MagicMock()
    application.state.voice_registry = registry
    application.state.audio_cache = AudioCache(max_size=3)
    return application


@pytest.fixture
async def integration_client(integration_app: MagicMock) -> AsyncIterator[AsyncClient]:
    """HTTP client wired to the integration app."""
    transport = ASGITransport(app=integration_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_database_connected(integration_client: AsyncClient) -> None:
    """GET /health reports database connected with a real Postgres."""
    response = await integration_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "connected"


async def test_create_character(integration_client: AsyncClient) -> None:
    """POST /api/characters with valid WAV creates a character (201)."""
    wav_data = make_wav_bytes()
    response = await integration_client.post(
        "/api/characters",
        params={"name": "test-char"},
        files={"audio": ("reference.wav", wav_data, "audio/wav")},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "test-char"
    assert data["id"] is not None


async def test_create_duplicate_character(integration_client: AsyncClient) -> None:
    """POST /api/characters with duplicate name returns 409."""
    wav_data = make_wav_bytes()
    first = await integration_client.post(
        "/api/characters",
        params={"name": "dupe-char"},
        files={"audio": ("reference.wav", wav_data, "audio/wav")},
    )
    assert first.status_code == 201

    second = await integration_client.post(
        "/api/characters",
        params={"name": "dupe-char"},
        files={"audio": ("reference.wav", wav_data, "audio/wav")},
    )
    assert second.status_code == 409


async def test_delete_character(integration_client: AsyncClient) -> None:
    """DELETE /api/characters/{id} removes the character (204)."""
    wav_data = make_wav_bytes()
    create_resp = await integration_client.post(
        "/api/characters",
        params={"name": "delete-me"},
        files={"audio": ("reference.wav", wav_data, "audio/wav")},
    )
    assert create_resp.status_code == 201
    character_id = create_resp.json()["id"]

    delete_resp = await integration_client.delete(f"/api/characters/{character_id}")
    assert delete_resp.status_code == 204

    # Verify it's gone
    delete_again = await integration_client.delete(f"/api/characters/{character_id}")
    assert delete_again.status_code == 404


async def test_delete_missing_character(integration_client: AsyncClient) -> None:
    """DELETE /api/characters/999999 returns 404."""
    response = await integration_client.delete("/api/characters/999999")
    assert response.status_code == 404
