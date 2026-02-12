"""TTS service that dispatches generation requests to registered engines."""

import logging
from collections.abc import Iterator

from doppelganger.tts.engine import EngineType, TTSChunk, TTSEngine, TTSOverrides, TTSResult
from doppelganger.tts.exceptions import TTSModelNotLoadedError, TTSVoiceNotFoundError
from doppelganger.tts.voice_registry import VoiceRegistry

# Re-export for backward compatibility (API tests, bot client import from here)
__all__ = ["TTSChunk", "TTSOverrides", "TTSResult", "TTSService"]

logger = logging.getLogger(__name__)


class TTSService:
    """Routes TTS requests to the appropriate engine based on voice configuration."""

    def __init__(self, registry: VoiceRegistry) -> None:
        self._registry = registry
        self._engines: dict[EngineType, TTSEngine] = {}

    def register_engine(self, engine: TTSEngine) -> None:
        """Register a TTS engine for its engine type."""
        self._engines[engine.engine_type] = engine
        logger.info("Registered TTS engine: %s", engine.engine_type.value)

    def _resolve(self, character_name: str) -> tuple[TTSEngine, str]:
        """Look up the voice entry and return the matching engine and voice path."""
        voice = self._registry.get_voice(character_name)
        if voice is None:
            raise TTSVoiceNotFoundError(f"Voice not found: {character_name}")

        engine = self._engines.get(voice.engine)
        if engine is None:
            raise TTSModelNotLoadedError(f"No engine registered for type: {voice.engine.value}")

        return engine, str(voice.reference_audio_path)

    def generate(self, character_name: str, text: str, overrides: TTSOverrides | None = None) -> TTSResult:
        """Generate speech by delegating to the resolved engine."""
        engine, voice_path = self._resolve(character_name)
        logger.info(
            "Generating TTS: character=%s, engine=%s, text_len=%d", character_name, engine.engine_type.value, len(text)
        )
        result = engine.generate(voice_path, text, overrides)
        logger.info(
            "TTS complete: character=%s, duration_ms=%d, audio_size=%d",
            character_name,
            result.duration_ms,
            len(result.audio_bytes),
        )
        return result

    def generate_stream(
        self, character_name: str, text: str, overrides: TTSOverrides | None = None
    ) -> Iterator[TTSChunk]:
        """Stream speech by delegating to the resolved engine."""
        engine, voice_path = self._resolve(character_name)
        logger.info(
            "Streaming TTS: character=%s, engine=%s, text_len=%d", character_name, engine.engine_type.value, len(text)
        )
        return engine.generate_stream(voice_path, text, overrides)

    def load_model(self) -> None:
        """Load all registered engines."""
        for engine in self._engines.values():
            engine.load_model()

    def unload_model(self) -> None:
        """Unload all registered engines."""
        for engine in self._engines.values():
            engine.unload_model()

    @property
    def is_loaded(self) -> bool:
        """True if any registered engine is loaded."""
        return any(engine.is_loaded for engine in self._engines.values())

    def engine_statuses(self) -> list[dict[str, str | bool]]:
        """Return status info for each registered engine."""
        return [
            {
                "engine": engine_type.value,
                "loaded": engine.is_loaded,
                "device": engine.device,
            }
            for engine_type, engine in self._engines.items()
        ]

    @property
    def device(self) -> str:
        """The device from the first registered engine, or 'cpu' if none."""
        for engine in self._engines.values():
            return engine.device
        return "cpu"
