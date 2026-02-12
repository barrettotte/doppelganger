"""Shared test fixtures with mocked database and TTS services."""

import io
import wave
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from testcontainers.core import config as tc_config
from testcontainers.postgres import PostgresContainer

from doppelganger.app import create_app
from doppelganger.config import Settings
from doppelganger.tts.cache import AudioCache
from doppelganger.tts.voice_registry import VoiceRegistry


def make_wav_bytes(duration_seconds: float = 10.0, sample_rate: int = 22050) -> bytes:
    """Create valid WAV bytes for upload testing."""
    buf = io.BytesIO()
    n_frames = int(sample_rate * duration_seconds)

    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00" * (n_frames * 2))

    return buf.getvalue()


def mock_db_connect_list(rows: list[dict[str, object]]) -> MagicMock:
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


def mock_db_connect_single(row: dict[str, object] | None) -> MagicMock:
    """Create a mock DB engine whose connect().execute().mappings().first() returns a single row."""
    engine = MagicMock()
    conn = AsyncMock()
    execute_result = MagicMock()
    execute_result.mappings.return_value.first.return_value = row
    conn.execute = AsyncMock(return_value=execute_result)

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    return engine


def mock_db_begin_single(row: dict[str, object] | None) -> MagicMock:
    """Create a mock DB engine whose begin().execute().mappings().first() returns a single row."""
    engine = MagicMock()
    conn = AsyncMock()
    execute_result = MagicMock()
    execute_result.mappings.return_value.first.return_value = row
    conn.execute = AsyncMock(return_value=execute_result)

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.begin.return_value = ctx
    return engine


@pytest.fixture
def settings() -> Settings:
    """Return default test settings."""
    return Settings()


@pytest.fixture
def mock_db_engine() -> MagicMock:
    """Return a mocked async database engine with async context manager support."""
    engine = MagicMock()
    conn = AsyncMock()
    # execute returns a sync MagicMock so .mappings().first() works without await
    execute_result = MagicMock()
    execute_result.mappings.return_value.first.return_value = None
    conn.execute = AsyncMock(return_value=execute_result)

    ctx = AsyncMock()
    ctx.__aenter__.return_value = conn
    engine.connect.return_value = ctx
    return engine


@pytest.fixture
def mock_tts_service() -> MagicMock:
    """Return a mocked TTS service with is_loaded=True."""
    service = MagicMock()
    service.is_loaded = True
    return service


@pytest.fixture
def mock_voice_registry(tmp_path: Path) -> VoiceRegistry:
    """Return a real VoiceRegistry pointing at a temp directory."""
    registry = VoiceRegistry(str(tmp_path / "voices"))
    (tmp_path / "voices").mkdir()
    return registry


@pytest.fixture
def audio_cache() -> AudioCache:
    """Return a small AudioCache for testing."""
    return AudioCache(max_size=3)


@pytest.fixture
def app(
    mock_db_engine: MagicMock,
    mock_tts_service: MagicMock,
    mock_voice_registry: VoiceRegistry,
    audio_cache: AudioCache,
) -> MagicMock:
    """Create the FastAPI app with mocked services."""
    application = create_app()
    application.state.db_engine = mock_db_engine
    application.state.tts_ready = False
    application.state.tts_service = mock_tts_service
    application.state.voice_registry = mock_voice_registry
    application.state.audio_cache = audio_cache
    return application


@pytest.fixture
async def client(app: MagicMock) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def pg_container():
    """Start a Postgres 17 container for integration tests."""
    tc_config.testcontainers_config.ryuk_privileged = True
    with PostgresContainer("postgres:17", driver=None, privileged=True) as pg:
        yield pg


@pytest.fixture(scope="session")
def pg_url(pg_container) -> str:
    """Async connection URL for the test container."""
    base = pg_container.get_connection_url()
    return base.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture(scope="session")
def _run_migrations(pg_container):
    """Run Alembic migrations against the test container once per session."""
    sync_url = pg_container.get_connection_url().replace("postgresql://", "postgresql+psycopg2://")
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")


@pytest.fixture
async def async_engine(pg_url: str, _run_migrations) -> AsyncIterator[AsyncEngine]:
    """Create an async engine pointing at the test container."""
    engine = create_async_engine(pg_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_conn(async_engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """Provide a transactional connection that rolls back after each test."""
    async with async_engine.connect() as conn:
        trans = await conn.begin()
        yield conn
        await trans.rollback()
