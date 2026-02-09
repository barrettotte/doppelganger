"""Shared test fixtures with mocked database."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from doppelganger.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Return default test settings."""
    return Settings()


@pytest.fixture
def mock_db_engine() -> MagicMock:
    """Return a mocked async database engine."""
    engine = MagicMock()
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=MagicMock())
    engine.connect = MagicMock(return_value=conn)
    return engine


@pytest.fixture
def app(mock_db_engine: MagicMock) -> MagicMock:
    """Create the FastAPI app with a mocked DB engine."""
    from doppelganger.app import create_app

    application = create_app()
    application.state.db_engine = mock_db_engine
    application.state.tts_ready = False
    return application


@pytest.fixture
async def client(app: MagicMock) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP client for testing."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
