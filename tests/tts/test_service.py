"""Tests for the TTS service dispatcher."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from doppelganger.tts.engine import EngineType, TTSChunk, TTSEngine, TTSOverrides, TTSResult
from doppelganger.tts.exceptions import TTSModelNotLoadedError, TTSVoiceNotFoundError
from doppelganger.tts.service import TTSService
from doppelganger.tts.voice_registry import VoiceRegistry


def _make_voice(voices_dir: Path, name: str) -> None:
    """Create a voice directory with a reference.wav."""
    char_dir = voices_dir / name
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / "reference.wav").write_bytes(b"RIFF" + b"\x00" * 100)


@pytest.fixture
def voices_dir(tmp_path: Path) -> Path:
    """Create a voices directory with one chatterbox voice."""
    d = tmp_path / "voices"
    _make_voice(d, "gandalf")
    return d


@pytest.fixture
def registry(voices_dir: Path) -> VoiceRegistry:
    """A voice registry scanned from tmp voices directory."""
    r = VoiceRegistry(str(voices_dir))
    r.scan()
    return r


def _make_mock_engine(engine_type: EngineType) -> MagicMock:
    """Create a mock TTSEngine with the given type."""
    engine = MagicMock(spec=TTSEngine)
    engine.engine_type = engine_type
    engine.is_loaded = True
    return engine


def test_resolve_picks_correct_engine(registry: VoiceRegistry) -> None:
    """_resolve returns the engine matching the voice's engine type."""
    service = TTSService(registry)
    engine = _make_mock_engine(EngineType.CHATTERBOX)
    service.register_engine(engine)

    resolved_engine, voice_path = service._resolve("gandalf")
    assert resolved_engine is engine
    assert "gandalf" in voice_path


def test_voice_not_found_raises(registry: VoiceRegistry) -> None:
    """_resolve raises TTSVoiceNotFoundError for unknown characters."""
    service = TTSService(registry)
    engine = _make_mock_engine(EngineType.CHATTERBOX)
    service.register_engine(engine)

    with pytest.raises(TTSVoiceNotFoundError):
        service._resolve("unknown-voice")


def test_no_engine_for_type_raises(registry: VoiceRegistry) -> None:
    """_resolve raises TTSModelNotLoadedError when no engine matches the voice type."""
    service = TTSService(registry)
    # Register an orpheus engine but gandalf is chatterbox
    engine = _make_mock_engine(EngineType.ORPHEUS)
    service.register_engine(engine)

    with pytest.raises(TTSModelNotLoadedError, match="No engine registered"):
        service._resolve("gandalf")


def test_generate_delegates_to_engine(registry: VoiceRegistry) -> None:
    """generate calls the resolved engine's generate method."""
    service = TTSService(registry)
    engine = _make_mock_engine(EngineType.CHATTERBOX)
    expected = TTSResult(audio_bytes=b"wav-data", sample_rate=24000, duration_ms=500)
    engine.generate.return_value = expected
    service.register_engine(engine)

    result = service.generate("gandalf", "hello world")
    assert result is expected
    engine.generate.assert_called_once()
    # Verify the voice path was passed, not the character name
    call_args = engine.generate.call_args
    assert "gandalf" in call_args[0][0]
    assert call_args[0][1] == "hello world"


def test_generate_stream_delegates_to_engine(registry: VoiceRegistry) -> None:
    """generate_stream calls the resolved engine's generate_stream method."""
    service = TTSService(registry)
    engine = _make_mock_engine(EngineType.CHATTERBOX)
    chunks = [
        TTSChunk(audio_bytes=b"c1", chunk_index=0, is_final=False),
        TTSChunk(audio_bytes=b"c2", chunk_index=1, is_final=True),
    ]
    engine.generate_stream.return_value = iter(chunks)
    service.register_engine(engine)

    result = list(service.generate_stream("gandalf", "hello"))
    assert len(result) == 2
    engine.generate_stream.assert_called_once()


def test_load_model_calls_all_engines(registry: VoiceRegistry) -> None:
    """load_model calls load_model on all registered engines."""
    service = TTSService(registry)
    e1 = _make_mock_engine(EngineType.CHATTERBOX)
    e2 = _make_mock_engine(EngineType.ORPHEUS)
    service.register_engine(e1)
    service.register_engine(e2)

    service.load_model()
    e1.load_model.assert_called_once()
    e2.load_model.assert_called_once()


def test_unload_model_calls_all_engines(registry: VoiceRegistry) -> None:
    """unload_model calls unload_model on all registered engines."""
    service = TTSService(registry)
    e1 = _make_mock_engine(EngineType.CHATTERBOX)
    service.register_engine(e1)

    service.unload_model()
    e1.unload_model.assert_called_once()


def test_is_loaded_any(registry: VoiceRegistry) -> None:
    """is_loaded is True if any engine is loaded."""
    service = TTSService(registry)
    assert service.is_loaded is False

    e1 = _make_mock_engine(EngineType.CHATTERBOX)
    e1.is_loaded = True
    service.register_engine(e1)
    assert service.is_loaded is True


def test_generate_passes_overrides(registry: VoiceRegistry) -> None:
    """generate passes TTSOverrides through to the engine."""
    service = TTSService(registry)
    engine = _make_mock_engine(EngineType.CHATTERBOX)
    expected = TTSResult(audio_bytes=b"wav-data", sample_rate=24000, duration_ms=500)
    engine.generate.return_value = expected
    service.register_engine(engine)

    overrides = TTSOverrides(exaggeration=0.7, temperature=0.9)
    result = service.generate("gandalf", "hello", overrides)
    assert result is expected

    call_args = engine.generate.call_args
    assert call_args[0][2] is overrides


def test_generate_stream_passes_overrides(registry: VoiceRegistry) -> None:
    """generate_stream passes TTSOverrides through to the engine."""
    service = TTSService(registry)
    engine = _make_mock_engine(EngineType.CHATTERBOX)
    chunks = [TTSChunk(audio_bytes=b"c1", chunk_index=0, is_final=True)]
    engine.generate_stream.return_value = iter(chunks)
    service.register_engine(engine)

    overrides = TTSOverrides(cfg_weight=3.0)
    list(service.generate_stream("gandalf", "hello", overrides))

    call_args = engine.generate_stream.call_args
    assert call_args[0][2] is overrides


def test_device_from_engine(registry: VoiceRegistry) -> None:
    """device property returns the first engine's device."""
    service = TTSService(registry)
    assert service.device == "cpu"  # fallback with no engines

    e1 = _make_mock_engine(EngineType.CHATTERBOX)
    e1.device = "cuda"
    service.register_engine(e1)
    assert service.device == "cuda"


def test_engine_statuses_empty(registry: VoiceRegistry) -> None:
    """engine_statuses returns empty list with no engines."""
    service = TTSService(registry)
    assert service.engine_statuses() == []


def test_engine_statuses_multiple(registry: VoiceRegistry) -> None:
    """engine_statuses returns info for each registered engine."""
    service = TTSService(registry)

    e1 = _make_mock_engine(EngineType.CHATTERBOX)
    e1.device = "cuda"
    e1.is_loaded = True
    service.register_engine(e1)

    e2 = _make_mock_engine(EngineType.ORPHEUS)
    e2.device = "cpu"
    e2.is_loaded = False
    service.register_engine(e2)

    statuses = service.engine_statuses()
    assert len(statuses) == 2

    assert statuses[0]["engine"] == "chatterbox"
    assert statuses[0]["loaded"] is True
    assert statuses[0]["device"] == "cuda"

    assert statuses[1]["engine"] == "orpheus"
    assert statuses[1]["loaded"] is False
    assert statuses[1]["device"] == "cpu"
