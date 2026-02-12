"""Tests for the characters API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from tests.conftest import mock_db_begin_single, mock_db_connect_list

_NOW = datetime(2026, 1, 1)


@pytest.mark.asyncio
async def test_list_empty(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/characters returns empty list when no characters exist."""
    app.state.db_engine = mock_db_connect_list([])

    response = await client.get("/api/characters")
    assert response.status_code == 200

    data = response.json()
    assert data["characters"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_list_populated(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/characters returns characters with IDs from the database."""
    app.state.db_engine = mock_db_connect_list(
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
async def test_list_includes_tuning(app: MagicMock, client: AsyncClient) -> None:
    """GET /api/characters includes tuning fields in each character."""
    app.state.db_engine = mock_db_connect_list(
        [
            {
                "id": 1,
                "name": "gandalf",
                "reference_audio_path": "/voices/gandalf/reference.wav",
                "created_at": _NOW,
                "tts_exaggeration": 0.7,
                "tts_cfg_weight": None,
                "tts_temperature": None,
                "tts_repetition_penalty": None,
                "tts_top_p": None,
                "tts_frequency_penalty": None,
            },
        ]
    )

    response = await client.get("/api/characters")
    data = response.json()
    tuning = data["characters"][0]["tuning"]
    assert tuning["exaggeration"] == 0.7
    assert tuning["cfg_weight"] is None


@pytest.mark.asyncio
async def test_put_tuning(app: MagicMock, client: AsyncClient) -> None:
    """PUT /api/characters/{id}/tuning updates and returns tuning."""
    updated_row = {
        "id": 1,
        "name": "gandalf",
        "reference_audio_path": "/voices/gandalf/reference.wav",
        "created_at": _NOW,
        "engine": "chatterbox",
        "tts_exaggeration": 0.5,
        "tts_cfg_weight": None,
        "tts_temperature": None,
        "tts_repetition_penalty": None,
        "tts_top_p": None,
        "tts_frequency_penalty": None,
    }
    app.state.db_engine = mock_db_begin_single(updated_row)

    response = await client.put("/api/characters/1/tuning", json={"exaggeration": 0.5})
    assert response.status_code == 200

    data = response.json()
    assert data["tuning"]["exaggeration"] == 0.5
    assert data["name"] == "gandalf"


@pytest.mark.asyncio
async def test_put_tuning_not_found(app: MagicMock, client: AsyncClient) -> None:
    """PUT /api/characters/{id}/tuning returns 404 when character not found."""
    app.state.db_engine = mock_db_begin_single(None)

    response = await client.put("/api/characters/999/tuning", json={"exaggeration": 0.5})
    assert response.status_code == 404


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
