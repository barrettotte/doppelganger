"""Tests for the TTS API endpoints."""

from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from doppelganger.tts.exceptions import (
    TTSModelNotLoadedError,
    TTSOutOfMemoryError,
    TTSVoiceNotFoundError,
)
from doppelganger.tts.service import TTSResult


@pytest.mark.asyncio
async def test_generate_returns_wav(app: MagicMock, client: AsyncClient) -> None:
    """POST /api/tts/generate returns WAV audio on success."""

    result = TTSResult(audio_bytes=b"RIFF-fake-wav", sample_rate=24000, duration_ms=1000)
    app.state.tts_service.generate.return_value = result

    response = await client.post(
        "/api/tts/generate",
        json={"character": "gandalf", "text": "hello world"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"RIFF-fake-wav"


@pytest.mark.asyncio
async def test_generate_404_unknown_voice(app: MagicMock, client: AsyncClient) -> None:
    """POST /api/tts/generate returns 404 for unknown voice."""
    app.state.tts_service.generate.side_effect = TTSVoiceNotFoundError("not found")

    response = await client.post(
        "/api/tts/generate",
        json={"character": "unknown", "text": "hello"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_503_oom(app: MagicMock, client: AsyncClient) -> None:
    """POST /api/tts/generate returns 503 on OOM."""
    app.state.tts_service.generate.side_effect = TTSOutOfMemoryError("OOM")

    response = await client.post(
        "/api/tts/generate",
        json={"character": "gandalf", "text": "hello"},
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_generate_503_model_not_loaded(app: MagicMock, client: AsyncClient) -> None:
    """POST /api/tts/generate returns 503 when model not loaded."""
    app.state.tts_service.generate.side_effect = TTSModelNotLoadedError("not loaded")

    response = await client.post(
        "/api/tts/generate",
        json={"character": "gandalf", "text": "hello"},
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_generate_cache_hit(app: MagicMock, client: AsyncClient) -> None:
    """Cached results skip the TTS service call."""
    app.state.audio_cache.put("gandalf", "hello", b"cached-wav")

    response = await client.post(
        "/api/tts/generate",
        json={"character": "gandalf", "text": "hello"},
    )
    assert response.status_code == 200
    assert response.content == b"cached-wav"
    app.state.tts_service.generate.assert_not_called()


@pytest.mark.asyncio
async def test_generate_validation_error(client: AsyncClient) -> None:
    """Invalid request body returns 422."""
    response = await client.post(
        "/api/tts/generate",
        json={"character": "INVALID NAME!", "text": "hello"},
    )
    assert response.status_code == 422
