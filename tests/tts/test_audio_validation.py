"""Tests for audio validation using programmatically constructed WAV headers."""

import io
import wave

import pytest

from doppelganger.tts.audio_validation import AudioValidationError, validate_reference_audio


def _make_wav(
    sample_rate: int = 22050,
    channels: int = 1,
    sample_width: int = 2,
    duration_seconds: float = 10.0,
) -> bytes:
    """Create a minimal valid WAV file in memory."""
    buf = io.BytesIO()
    n_frames = int(sample_rate * duration_seconds)

    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00" * (n_frames * channels * sample_width))

    return buf.getvalue()


def test_valid_wav_passes() -> None:
    """A valid WAV with acceptable parameters passes validation."""
    data = _make_wav(sample_rate=22050, duration_seconds=10.0)
    info = validate_reference_audio(data)
    assert info.sample_rate == 22050
    assert info.channels == 1
    assert abs(info.duration_seconds - 10.0) < 0.1
    assert info.file_size == len(data)


def test_non_wav_rejected() -> None:
    """Non-WAV data is rejected."""
    with pytest.raises(AudioValidationError, match="Invalid WAV"):
        validate_reference_audio(b"not a wav file at all")


def test_too_short_rejected() -> None:
    """Audio shorter than 5 seconds is rejected."""
    data = _make_wav(duration_seconds=2.0)
    with pytest.raises(AudioValidationError, match="too short"):
        validate_reference_audio(data)


def test_too_long_rejected() -> None:
    """Audio longer than 30 seconds is rejected."""
    data = _make_wav(duration_seconds=35.0)
    with pytest.raises(AudioValidationError, match="too long"):
        validate_reference_audio(data)


def test_sample_rate_too_low() -> None:
    """Sample rate below 16000 Hz is rejected."""
    data = _make_wav(sample_rate=8000, duration_seconds=10.0)
    with pytest.raises(AudioValidationError, match="Sample rate"):
        validate_reference_audio(data)


def test_sample_rate_too_high() -> None:
    """Sample rate above 48000 Hz is rejected."""
    data = _make_wav(sample_rate=96000, duration_seconds=10.0)
    with pytest.raises(AudioValidationError, match="Sample rate"):
        validate_reference_audio(data)


def test_file_too_large() -> None:
    """Files over 10MB are rejected."""
    data = b"\x00" * (10 * 1024 * 1024 + 1)
    with pytest.raises(AudioValidationError, match="too large"):
        validate_reference_audio(data)


def test_stereo_accepted() -> None:
    """Stereo WAV files are accepted."""
    data = _make_wav(channels=2, duration_seconds=10.0)
    info = validate_reference_audio(data)
    assert info.channels == 2


def test_boundary_duration_min() -> None:
    """Exactly 5 seconds should pass validation."""
    data = _make_wav(duration_seconds=5.0)
    info = validate_reference_audio(data)
    assert info.duration_seconds >= 5.0


def test_boundary_duration_max() -> None:
    """Exactly 30 seconds should pass validation."""
    data = _make_wav(duration_seconds=30.0)
    info = validate_reference_audio(data)
    assert info.duration_seconds <= 30.0
