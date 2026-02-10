"""Abstract base class for TTS engines and shared result types."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum


class EngineType(Enum):
    """Supported TTS engine backends."""

    CHATTERBOX = "chatterbox"
    ORPHEUS = "orpheus"


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


class TTSEngine(ABC):
    """Base class for pluggable TTS backends."""

    engine_type: EngineType

    @abstractmethod
    def load_model(self) -> None:
        """Load the model into memory."""

    @abstractmethod
    def unload_model(self) -> None:
        """Release the model and free resources."""

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Whether the engine's model is loaded and ready."""

    @property
    def device(self) -> str:
        """The device this engine runs on. Override in subclasses with a real device."""
        return "cpu"

    @abstractmethod
    def generate(self, voice_path: str, text: str) -> TTSResult:
        """Generate speech audio. voice_path is a reference WAV or adapter directory."""

    def generate_stream(self, voice_path: str, text: str) -> Iterator[TTSChunk]:
        """Stream speech audio in chunks. Override in engines that support streaming."""
        raise NotImplementedError(f"{type(self).__name__} does not support streaming")
