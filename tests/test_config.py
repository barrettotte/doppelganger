"""Tests for application configuration."""

import os
from unittest.mock import patch

from pydantic import SecretStr

from doppelganger.config import Settings


def test_default_settings() -> None:
    """Default settings should have sensible values."""
    settings = Settings()
    assert settings.debug is False
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.database.host == "localhost"
    assert settings.database.port == 5432
    assert settings.database.pool_size == 5


def test_database_async_url() -> None:
    """Async URL should use asyncpg driver."""
    settings = Settings()
    url = settings.database.async_url
    assert url.startswith("postgresql+asyncpg://")
    assert "doppelganger" in url


def test_database_sync_url() -> None:
    """Sync URL should use psycopg2 driver."""
    settings = Settings()
    url = settings.database.sync_url
    assert url.startswith("postgresql+psycopg2://")
    assert "doppelganger" in url


def test_env_var_loading() -> None:
    """Settings should load from environment variables."""
    env = {
        "DOPPELGANGER_DEBUG": "true",
        "DOPPELGANGER_PORT": "9000",
        "DOPPELGANGER_DATABASE__HOST": "db.example.com",
        "DOPPELGANGER_DATABASE__PORT": "5433",
    }

    with patch.dict(os.environ, env, clear=False):
        settings = Settings()
        assert settings.debug is True
        assert settings.port == 9000
        assert settings.database.host == "db.example.com"
        assert settings.database.port == 5433


def test_secret_str_hiding() -> None:
    """SecretStr fields should not expose values in repr."""
    settings = Settings()
    assert isinstance(settings.database.password, SecretStr)
    assert "doppelganger" not in repr(settings.database.password)
    assert settings.database.password.get_secret_value() == "doppelganger"


def test_chatterbox_defaults() -> None:
    """ChatterboxSettings should have sensible defaults."""
    settings = Settings()
    assert settings.chatterbox.device == "cuda"
    assert settings.chatterbox.exaggeration == 0.1
    assert settings.chatterbox.temperature == 0.5
    assert settings.voices_dir == "voices"
    assert settings.cache_max_size == 100


def test_chatterbox_env_loading() -> None:
    """ChatterboxSettings should load from DOPPELGANGER_CHATTERBOX__ env vars."""
    env = {
        "DOPPELGANGER_CHATTERBOX__DEVICE": "cpu",
        "DOPPELGANGER_CHATTERBOX__EXAGGERATION": "0.5",
        "DOPPELGANGER_VOICES_DIR": "/data/voices",
    }

    with patch.dict(os.environ, env, clear=False):
        settings = Settings()
        assert settings.chatterbox.device == "cpu"
        assert settings.chatterbox.exaggeration == 0.5
        assert settings.voices_dir == "/data/voices"


def test_orpheus_defaults() -> None:
    """OrpheusSettings should default to disabled with sensible values."""
    settings = Settings()
    assert settings.orpheus.enabled is False
    assert settings.orpheus.vllm_base_url == "http://localhost:8001/v1"
    assert settings.orpheus.snac_device == "cpu"
    assert settings.orpheus.sample_rate == 24000
    assert settings.orpheus.max_tokens == 4096


def test_orpheus_env_loading() -> None:
    """OrpheusSettings should load from environment variables."""
    env = {
        "DOPPELGANGER_ORPHEUS__ENABLED": "true",
        "DOPPELGANGER_ORPHEUS__VLLM_BASE_URL": "http://gpu-server:8001/v1",
        "DOPPELGANGER_ORPHEUS__TEMPERATURE": "0.8",
    }

    with patch.dict(os.environ, env, clear=False):
        settings = Settings()
        assert settings.orpheus.enabled is True
        assert settings.orpheus.vllm_base_url == "http://gpu-server:8001/v1"
        assert settings.orpheus.temperature == 0.8
