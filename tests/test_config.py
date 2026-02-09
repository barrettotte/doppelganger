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
