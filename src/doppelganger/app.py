"""FastAPI application factory and lifespan management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from doppelganger.api.errors import register_error_handlers
from doppelganger.api.health import router as health_router
from doppelganger.api.middleware import RequestIDMiddleware
from doppelganger.config import get_settings
from doppelganger.db.engine import create_db_engine, dispose_db_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown resources."""
    settings = get_settings()

    engine = create_db_engine(settings)
    app.state.db_engine = engine
    app.state.tts_ready = False

    yield
    await dispose_db_engine(engine)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Doppelganger",
        description="TTS voice cloning Discord bot API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)

    register_error_handlers(app)
    app.include_router(health_router)

    return app
