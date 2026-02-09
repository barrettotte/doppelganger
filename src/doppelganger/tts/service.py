"""TTS service wrapping Chatterbox for voice cloning."""

import importlib
import io
import logging
import wave
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from doppelganger.config import TTSSettings
from doppelganger.tts.exceptions import (
    TTSError,
    TTSGenerationError,
    TTSModelNotLoadedError,
    TTSOutOfMemoryError,
    TTSVoiceNotFoundError,
)
from doppelganger.tts.voice_registry import VoiceRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TTSResult:
    """Result of a TTS generation call."""

    audio_bytes: bytes
    sample_rate: int
    duration_ms: int


@dataclass(frozen=True)
class TTSChunk:
    """A chunk of streamed TTS audio."""

    audio_bytes: bytes
    chunk_index: int
    is_final: bool


class TTSService:
    """Wraps ChatterboxTTS with voice registry lookup, error handling, and WAV encoding."""

    def __init__(self, settings: TTSSettings, registry: VoiceRegistry) -> None:
        self._settings = settings
        self._registry = registry
        self._model: Any | None = None

    def load_model(self) -> None:
        """Import chatterbox and torchaudio at runtime and load the model."""
        try:
            chatterbox_tts = importlib.import_module("chatterbox.tts")

        except ImportError as e:
            raise RuntimeError("chatterbox-tts is not installed. Install with: uv sync --extra tts") from e

        logger.info("Loading ChatterboxTTS model on device=%s", self._settings.device)
        self._model = chatterbox_tts.ChatterboxTTS.from_pretrained(device=self._settings.device)
        logger.info("ChatterboxTTS model loaded successfully")

    def unload_model(self) -> None:
        """Release the model and free GPU memory."""
        if self._model is not None:
            del self._model
            self._model = None

            try:
                torch = importlib.import_module("torch")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            logger.info("TTS model unloaded")

    @property
    def is_loaded(self) -> bool:
        """Whether the TTS model is loaded and ready."""
        return self._model is not None

    def _require_model(self) -> None:
        if not self.is_loaded:
            raise TTSModelNotLoadedError("TTS model is not loaded")

    def _get_voice_path(self, character_name: str) -> str:
        voice = self._registry.get_voice(character_name)
        if voice is None:
            raise TTSVoiceNotFoundError(f"Voice not found: {character_name}")
        return str(voice.reference_audio_path)

    def _tensor_to_wav_bytes(self, audio_tensor: Any, sample_rate: int) -> bytes:
        """Convert a torch tensor to PCM16 WAV bytes for browser compatibility."""
        torch = importlib.import_module("torch")

        if not isinstance(audio_tensor, torch.Tensor):
            raise TTSGenerationError("Model returned unexpected type instead of Tensor")

        tensor = audio_tensor.unsqueeze(0) if audio_tensor.dim() == 1 else audio_tensor
        tensor = tensor.cpu().clamp(-1.0, 1.0)
        pcm16 = (tensor * 32767).to(torch.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(pcm16.shape[0])
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm16.numpy().tobytes())

        return buf.getvalue()

    def generate(self, character_name: str, text: str) -> TTSResult:
        """
        Generate speech for the given text using the character's voice.
        This is a blocking call - use run_in_executor from async code.
        """
        self._require_model()
        ref_path = self._get_voice_path(character_name)

        try:
            wav = self._model.generate(  # type: ignore[union-attr]
                text,
                audio_prompt_path=ref_path,
                exaggeration=self._settings.exaggeration,
                cfg_weight=self._settings.cfg_weight,
                temperature=self._settings.temperature,
            )

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                raise TTSOutOfMemoryError("CUDA out of memory during generation") from e
            raise TTSGenerationError(f"Generation failed: {e}") from e
        except Exception as e:
            raise TTSGenerationError(f"Generation failed: {e}") from e

        sample_rate: int = self._model.sr  # type: ignore[union-attr]
        audio_bytes = self._tensor_to_wav_bytes(wav, sample_rate)

        torch = importlib.import_module("torch")
        n_samples = wav.shape[-1] if isinstance(wav, torch.Tensor) else 0
        duration_ms = int(n_samples / sample_rate * 1000) if sample_rate > 0 else 0

        return TTSResult(audio_bytes=audio_bytes, sample_rate=sample_rate, duration_ms=duration_ms)

    def generate_stream(self, character_name: str, text: str) -> Iterator[TTSChunk]:
        """
        Stream TTS audio in chunks.
        This is a blocking iterator - use run_in_executor from async code.
        """
        self._require_model()
        ref_path = self._get_voice_path(character_name)

        try:
            sample_rate: int = self._model.sr  # type: ignore[union-attr]
            chunk_iter = self._model.generate_stream(  # type: ignore[union-attr]
                text,
                audio_prompt_path=ref_path,
                exaggeration=self._settings.exaggeration,
                cfg_weight=self._settings.cfg_weight,
                temperature=self._settings.temperature,
            )

            for i, chunk_tensor in enumerate(chunk_iter):
                audio_bytes = self._tensor_to_wav_bytes(chunk_tensor, sample_rate)
                yield TTSChunk(audio_bytes=audio_bytes, chunk_index=i, is_final=False)

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                raise TTSOutOfMemoryError("CUDA out of memory during streaming") from e
            raise TTSGenerationError(f"Stream generation failed: {e}") from e
        except TTSError:
            raise
        except Exception as e:
            raise TTSGenerationError(f"Stream generation failed: {e}") from e
