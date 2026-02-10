"""Tests for the Chatterbox TTS engine with mocked chatterbox."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from doppelganger.config import ChatterboxSettings
from doppelganger.tts.chatterbox import ChatterboxEngine
from doppelganger.tts.exceptions import (
    TTSModelNotLoadedError,
    TTSOutOfMemoryError,
)


@pytest.fixture
def voice_path(tmp_path: Path) -> str:
    """Create a fake reference WAV and return its path."""
    ref = tmp_path / "gandalf" / "reference.wav"
    ref.parent.mkdir(parents=True, exist_ok=True)
    ref.write_bytes(b"RIFF" + b"\x00" * 100)
    return str(ref)


@pytest.fixture
def chatterbox_settings() -> ChatterboxSettings:
    """Default TTS settings for testing."""
    return ChatterboxSettings(device="cpu")


@pytest.fixture
def mock_torch() -> tuple[MagicMock, MagicMock]:
    """Create a mock torch module and tensor."""
    torch = MagicMock()
    tensor = MagicMock()
    tensor.dim.return_value = 1
    tensor.unsqueeze.return_value = tensor
    tensor.cpu.return_value = tensor
    tensor.shape = (1, 16000)

    torch.Tensor = MagicMock
    tensor.__class__ = torch.Tensor

    torch.cuda.is_available.return_value = False
    return torch, tensor


@pytest.fixture
def mock_chatterbox(mock_torch: tuple[MagicMock, MagicMock]) -> tuple[MagicMock, MagicMock]:
    """Create mock chatterbox module and model."""
    _torch, tensor = mock_torch

    model = MagicMock()
    model.sr = 24000
    model.generate.return_value = tensor
    model.generate_stream.return_value = iter([tensor, tensor])

    chatterbox_tts_class = MagicMock()
    chatterbox_tts_class.from_pretrained.return_value = model

    return chatterbox_tts_class, model


def test_not_loaded_raises(chatterbox_settings: ChatterboxSettings) -> None:
    """Generating without loading the model raises TTSModelNotLoadedError."""
    engine = ChatterboxEngine(chatterbox_settings)
    with pytest.raises(TTSModelNotLoadedError):
        engine.generate("/fake/path.wav", "hello")


def test_is_loaded_property(chatterbox_settings: ChatterboxSettings) -> None:
    """is_loaded is False before loading."""
    engine = ChatterboxEngine(chatterbox_settings)
    assert engine.is_loaded is False


def test_load_and_unload(
    chatterbox_settings: ChatterboxSettings,
    mock_chatterbox: tuple[MagicMock, MagicMock],
    mock_torch: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loading sets is_loaded to True, unloading sets it to False."""
    chatterbox_tts_class, _model = mock_chatterbox
    torch, _tensor = mock_torch

    monkeypatch.setattr("doppelganger.tts.chatterbox.ChatterboxTTS", chatterbox_tts_class)
    monkeypatch.setattr("doppelganger.tts.chatterbox.torch", torch)

    engine = ChatterboxEngine(chatterbox_settings)
    engine.load_model()
    assert engine.is_loaded is True

    engine.unload_model()
    assert engine.is_loaded is False


def test_generate_returns_result(
    chatterbox_settings: ChatterboxSettings,
    voice_path: str,
    mock_chatterbox: tuple[MagicMock, MagicMock],
    mock_torch: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate returns a TTSResult with audio bytes."""
    chatterbox_tts_class, model = mock_chatterbox
    torch, _tensor = mock_torch

    monkeypatch.setattr("doppelganger.tts.chatterbox.ChatterboxTTS", chatterbox_tts_class)
    monkeypatch.setattr("doppelganger.tts.chatterbox.torch", torch)

    engine = ChatterboxEngine(chatterbox_settings)
    engine.load_model()

    # Mock _tensor_to_wav_bytes to avoid deep torch internals
    engine._tensor_to_wav_bytes = MagicMock(return_value=b"RIFF-wav-data")
    result = engine.generate(voice_path, "hello world")

    assert result.audio_bytes == b"RIFF-wav-data"
    assert result.sample_rate == 24000
    model.generate.assert_called_once()


def test_oom_caught(
    chatterbox_settings: ChatterboxSettings,
    voice_path: str,
    mock_chatterbox: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CUDA OOM RuntimeError is caught and re-raised as TTSOutOfMemoryError."""
    chatterbox_tts_class, model = mock_chatterbox

    monkeypatch.setattr("doppelganger.tts.chatterbox.ChatterboxTTS", chatterbox_tts_class)

    model.generate.side_effect = RuntimeError("CUDA out of memory")
    engine = ChatterboxEngine(chatterbox_settings)
    engine.load_model()

    with pytest.raises(TTSOutOfMemoryError):
        engine.generate(voice_path, "hello")


def test_stream_yields_chunks(
    chatterbox_settings: ChatterboxSettings,
    voice_path: str,
    mock_chatterbox: tuple[MagicMock, MagicMock],
    mock_torch: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """generate_stream yields TTSChunk objects."""
    chatterbox_tts_class, _model = mock_chatterbox
    torch, _tensor = mock_torch

    monkeypatch.setattr("doppelganger.tts.chatterbox.ChatterboxTTS", chatterbox_tts_class)
    monkeypatch.setattr("doppelganger.tts.chatterbox.torch", torch)

    engine = ChatterboxEngine(chatterbox_settings)
    engine.load_model()
    engine._tensor_to_wav_bytes = MagicMock(return_value=b"chunk-data")
    chunks = list(engine.generate_stream(voice_path, "hello"))

    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].audio_bytes == b"chunk-data"


def test_device_property(chatterbox_settings: ChatterboxSettings) -> None:
    """device property returns the configured device."""
    engine = ChatterboxEngine(chatterbox_settings)
    assert engine.device == "cpu"
