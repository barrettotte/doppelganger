"""Tests for the TTS service with mocked chatterbox."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from doppelganger.config import TTSSettings
from doppelganger.tts.exceptions import (
    TTSModelNotLoadedError,
    TTSOutOfMemoryError,
    TTSVoiceNotFoundError,
)
from doppelganger.tts.service import TTSService
from doppelganger.tts.voice_registry import VoiceRegistry


def _make_voice(voices_dir: Path, name: str) -> None:
    char_dir = voices_dir / name
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / "reference.wav").write_bytes(b"RIFF" + b"\x00" * 100)


@pytest.fixture
def voices_dir(tmp_path: Path) -> Path:
    d = tmp_path / "voices"
    _make_voice(d, "gandalf")
    return d


@pytest.fixture
def registry(voices_dir: Path) -> VoiceRegistry:
    r = VoiceRegistry(str(voices_dir))
    r.scan()
    return r


@pytest.fixture
def tts_settings() -> TTSSettings:
    return TTSSettings(device="cpu")


@pytest.fixture
def mock_torch() -> tuple[MagicMock, MagicMock]:
    """Create a mock torch module."""
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
    """Create mock chatterbox module."""
    _torch, tensor = mock_torch

    model = MagicMock()
    model.sr = 24000
    model.generate.return_value = tensor
    model.generate_stream.return_value = iter([tensor, tensor])

    chatterbox_tts = MagicMock()
    chatterbox_tts.ChatterboxTTS.from_pretrained.return_value = model

    return chatterbox_tts, model


def test_not_loaded_raises(tts_settings: TTSSettings, registry: VoiceRegistry) -> None:
    """Generating without loading the model raises TTSModelNotLoadedError."""
    service = TTSService(tts_settings, registry)
    with pytest.raises(TTSModelNotLoadedError):
        service.generate("gandalf", "hello")


def test_is_loaded_property(tts_settings: TTSSettings, registry: VoiceRegistry) -> None:
    """is_loaded is False before loading."""
    service = TTSService(tts_settings, registry)
    assert service.is_loaded is False


def test_voice_not_found(
    tts_settings: TTSSettings,
    registry: VoiceRegistry,
    mock_chatterbox: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generating with unknown voice raises TTSVoiceNotFoundError."""
    chatterbox_tts, _model = mock_chatterbox
    monkeypatch.setitem(sys.modules, "chatterbox.tts", chatterbox_tts)

    service = TTSService(tts_settings, registry)
    service.load_model()

    with pytest.raises(TTSVoiceNotFoundError):
        service.generate("unknown-voice", "hello")


def test_generate_returns_result(
    tts_settings: TTSSettings,
    registry: VoiceRegistry,
    mock_chatterbox: tuple[MagicMock, MagicMock],
    mock_torch: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate returns a TTSResult with audio bytes."""
    chatterbox_tts, model = mock_chatterbox
    torch, tensor = mock_torch

    monkeypatch.setitem(sys.modules, "chatterbox.tts", chatterbox_tts)
    monkeypatch.setitem(sys.modules, "torch", torch)

    service = TTSService(tts_settings, registry)
    service.load_model()

    # Mock _tensor_to_wav_bytes to avoid deep torch internals
    service._tensor_to_wav_bytes = MagicMock(return_value=b"RIFF-wav-data")
    result = service.generate("gandalf", "hello world")

    assert result.audio_bytes == b"RIFF-wav-data"
    assert result.sample_rate == 24000
    model.generate.assert_called_once()


def test_oom_caught(
    tts_settings: TTSSettings,
    registry: VoiceRegistry,
    mock_chatterbox: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CUDA OOM RuntimeError is caught and re-raised as TTSOutOfMemoryError."""
    chatterbox_tts, model = mock_chatterbox
    monkeypatch.setitem(sys.modules, "chatterbox.tts", chatterbox_tts)

    model.generate.side_effect = RuntimeError("CUDA out of memory")
    service = TTSService(tts_settings, registry)
    service.load_model()

    with pytest.raises(TTSOutOfMemoryError):
        service.generate("gandalf", "hello")


def test_stream_yields_chunks(
    tts_settings: TTSSettings,
    registry: VoiceRegistry,
    mock_chatterbox: tuple[MagicMock, MagicMock],
    mock_torch: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """generate_stream yields TTSChunk objects."""
    chatterbox_tts, model = mock_chatterbox
    torch, tensor = mock_torch

    monkeypatch.setitem(sys.modules, "chatterbox.tts", chatterbox_tts)
    monkeypatch.setitem(sys.modules, "torch", torch)

    service = TTSService(tts_settings, registry)
    service.load_model()
    service._tensor_to_wav_bytes = MagicMock(return_value=b"chunk-data")
    chunks = list(service.generate_stream("gandalf", "hello"))

    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].audio_bytes == b"chunk-data"


def test_unload_model(
    tts_settings: TTSSettings,
    registry: VoiceRegistry,
    mock_chatterbox: tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unloading the model sets is_loaded to False."""
    chatterbox_tts, _model = mock_chatterbox
    monkeypatch.setitem(sys.modules, "chatterbox.tts", chatterbox_tts)

    service = TTSService(tts_settings, registry)
    service.load_model()
    assert service.is_loaded is True

    # Mock torch for unload cleanup
    torch = MagicMock()
    torch.cuda.is_available.return_value = False
    monkeypatch.setitem(sys.modules, "torch", torch)

    service.unload_model()
    assert service.is_loaded is False
