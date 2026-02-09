"""FastAPI application factory and lifespan management."""

import logging
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from doppelganger.api.characters import router as characters_router
from doppelganger.api.errors import register_error_handlers
from doppelganger.api.health import router as health_router
from doppelganger.api.middleware import RequestIDMiddleware
from doppelganger.api.tts import router as tts_router
from doppelganger.config import get_settings
from doppelganger.db.engine import create_db_engine, dispose_db_engine
from doppelganger.tts.cache import AudioCache
from doppelganger.tts.service import TTSService
from doppelganger.tts.voice_registry import VoiceRegistry

logger = logging.getLogger(__name__)

# resemble-perth uses pkg_resources which setuptools deprecated - remove when perth updates
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)
# diffusers LoRACompatibleLinear deprecation - remove when diffusers drops it
warnings.filterwarnings("ignore", message=".*LoRACompatibleLinear.*", category=FutureWarning)
# torch sdp_kernel deprecation - remove when chatterbox switches to sdpa_kernel
warnings.filterwarnings("ignore", message=".*sdp_kernel.*", category=FutureWarning)
# transformers past_key_values tuple deprecation - remove when chatterbox updates
warnings.filterwarnings("ignore", message=".*past_key_values.*as a tuple of tuples.*", category=UserWarning)
# transformers LlamaSdpaAttention fallback - remove when chatterbox updates
logging.getLogger("transformers.models.llama.modeling_llama").setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown resources."""
    settings = get_settings()

    engine = create_db_engine(settings)
    app.state.db_engine = engine

    registry = VoiceRegistry(settings.tts.voices_dir)
    registry.scan()
    app.state.voice_registry = registry

    cache = AudioCache(max_size=settings.tts.cache_max_size)
    app.state.audio_cache = cache

    tts_service = TTSService(settings.tts, registry)
    app.state.tts_service = tts_service
    app.state.tts_ready = False

    try:
        tts_service.load_model()
        app.state.tts_ready = True
    except Exception:
        logger.warning("TTS model failed to load — running in degraded mode", exc_info=True)

    yield

    tts_service.unload_model()
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
    app.include_router(tts_router)
    app.include_router(characters_router)

    return app
