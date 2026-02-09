"""WAV audio validation using stdlib wave module."""

import io
import wave
from dataclasses import dataclass

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MIN_DURATION = 5.0  # seconds
MAX_DURATION = 30.0  # seconds
MIN_SAMPLE_RATE = 16000
MAX_SAMPLE_RATE = 48000


class AudioValidationError(ValueError):
    """Raised when reference audio fails validation."""


@dataclass(frozen=True)
class AudioInfo:
    """Metadata extracted from a validated WAV file."""

    sample_rate: int
    channels: int
    duration_seconds: float
    file_size: int


def validate_reference_audio(file_data: bytes) -> AudioInfo:
    """Validate WAV file data and return its metadata.

    Checks:
        - Valid WAV format (parseable by stdlib wave)
        - Duration between 5-30 seconds
        - Sample rate between 16000-48000 Hz
        - File size under 10 MB
    """
    file_size = len(file_data)
    if file_size > MAX_FILE_SIZE:
        raise AudioValidationError(f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})")

    try:
        with wave.open(io.BytesIO(file_data), "rb") as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            n_frames = wf.getnframes()

    except wave.Error as e:
        raise AudioValidationError(f"Invalid WAV file: {e}") from e
    except EOFError as e:
        raise AudioValidationError("Invalid WAV file: unexpected end of data") from e

    if sample_rate < MIN_SAMPLE_RATE or sample_rate > MAX_SAMPLE_RATE:
        raise AudioValidationError(
            f"Sample rate {sample_rate} Hz outside allowed range ({MIN_SAMPLE_RATE}-{MAX_SAMPLE_RATE} Hz)"
        )

    duration = n_frames / sample_rate
    if duration < MIN_DURATION:
        raise AudioValidationError(f"Audio too short: {duration:.1f}s (minimum {MIN_DURATION}s)")
    if duration > MAX_DURATION:
        raise AudioValidationError(f"Audio too long: {duration:.1f}s (maximum {MAX_DURATION}s)")

    return AudioInfo(
        sample_rate=sample_rate,
        channels=channels,
        duration_seconds=duration,
        file_size=file_size,
    )
