"""TTS-specific exception hierarchy."""


class TTSError(Exception):
    """Base exception for all TTS-related errors."""


class TTSModelNotLoadedError(TTSError):
    """Raised when a TTS operation is attempted before the model is loaded."""


class TTSGenerationError(TTSError):
    """Raised when TTS audio generation fails."""


class TTSOutOfMemoryError(TTSError):
    """Raised when TTS generation fails due to CUDA out-of-memory."""


class TTSVoiceNotFoundError(TTSError):
    """Raised when a requested voice/character is not in the registry."""
