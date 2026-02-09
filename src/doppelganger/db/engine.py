"""Async SQLAlchemy engine creation and lifecycle management."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from doppelganger.config import Settings


def create_db_engine(settings: Settings) -> AsyncEngine:
    """Create an async SQLAlchemy engine with connection pooling."""
    return create_async_engine(
        settings.database.async_url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.pool_max_overflow,
        pool_pre_ping=True,
    )


async def dispose_db_engine(engine: AsyncEngine) -> None:
    """Dispose the engine and close all pooled connections."""
    await engine.dispose()
