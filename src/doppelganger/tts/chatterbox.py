"""Chatterbox TTS engine for zero-shot voice cloning."""

import io
import logging
import wave
from collections.abc import Iterator
from typing import Any

import torch
from chatterbox.tts import ChatterboxTTS

from doppelganger.config import ChatterboxSettings
from doppelganger.tts.engine import EngineType, TTSChunk, TTSEngine, TTSResult
from doppelganger.tts.exceptions import (
    TTSError,
    TTSGenerationError,
    TTSModelNotLoadedError,
    TTSOutOfMemoryError,
)

logger = logging.getLogger(__name__)


class ChatterboxEngine(TTSEngine):
    """Wraps ChatterboxTTS for zero-shot voice cloning from a reference WAV."""

    engine_type = EngineType.CHATTERBOX

    def __init__(self, settings: ChatterboxSettings) -> None:
        self._settings = settings
        self._model: Any | None = None

    def load_model(self) -> None:
        """Load the ChatterboxTTS model onto the configured device."""
        logger.info("Loading ChatterboxTTS model on device=%s", self._settings.device)
        self._model = ChatterboxTTS.from_pretrained(device=self._settings.device)
        logger.info("ChatterboxTTS model loaded successfully")

    def unload_model(self) -> None:
        """Release the model and free GPU memory."""
        if self._model is not None:
            del self._model
            self._model = None

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("ChatterboxTTS model unloaded")

    @property
    def is_loaded(self) -> bool:
        """Whether the Chatterbox model is loaded and ready."""
        return self._model is not None

    @property
    def device(self) -> str:
        """The device the model runs on (e.g. 'cpu', 'cuda')."""
        return self._settings.device

    def _require_model(self) -> Any:
        """Return the loaded model, or raise if not loaded."""
        if self._model is None:
            raise TTSModelNotLoadedError("ChatterboxTTS model is not loaded")
        return self._model

    def _tensor_to_wav_bytes(self, audio_tensor: Any, sample_rate: int) -> bytes:
        """Convert a torch tensor to PCM16 WAV bytes for browser compatibility."""
        if not isinstance(audio_tensor, torch.Tensor):
            raise TTSGenerationError("Model returned unexpected type instead of Tensor")

        tensor = audio_tensor.unsqueeze(0) if audio_tensor.dim() == 1 else audio_tensor
        # Clamp to [-1, 1] then scale to signed 16-bit PCM range (max 32767)
        tensor = tensor.cpu().clamp(-1.0, 1.0)
        pcm16 = (tensor * 32767).to(torch.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(pcm16.shape[0])
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm16.numpy().tobytes())

        return buf.getvalue()

    def generate(self, voice_path: str, text: str) -> TTSResult:
        """Generate speech using Chatterbox with the given reference WAV path."""
        model = self._require_model()

        try:
            wav = model.generate(
                text,
                audio_prompt_path=voice_path,
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

        sample_rate: int = model.sr
        audio_bytes = self._tensor_to_wav_bytes(wav, sample_rate)

        n_samples = wav.shape[-1] if isinstance(wav, torch.Tensor) else 0
        duration_ms = int(n_samples / sample_rate * 1000) if sample_rate > 0 else 0

        return TTSResult(audio_bytes=audio_bytes, sample_rate=sample_rate, duration_ms=duration_ms)

    def generate_stream(self, voice_path: str, text: str) -> Iterator[TTSChunk]:
        """Stream TTS audio in chunks using Chatterbox's streaming API."""
        model = self._require_model()

        try:
            sample_rate: int = model.sr
            chunk_iter = model.generate_stream(
                text,
                audio_prompt_path=voice_path,
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
