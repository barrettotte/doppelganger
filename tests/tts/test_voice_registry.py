"""Tests for the voice registry."""

from pathlib import Path

from doppelganger.tts.engine import EngineType
from doppelganger.tts.voice_registry import VoiceRegistry


def _make_voice(voices_dir: Path, name: str) -> Path:
    """Helper to create a voice directory with a reference.wav."""
    char_dir = voices_dir / name
    char_dir.mkdir(parents=True, exist_ok=True)
    ref = char_dir / "reference.wav"
    ref.write_bytes(b"RIFF" + b"\x00" * 100)
    return ref


def test_empty_dir(tmp_path: Path) -> None:
    """Registry with no voice directories returns empty list."""
    voices_dir = tmp_path / "voices"
    voices_dir.mkdir()
    registry = VoiceRegistry(str(voices_dir))
    registry.scan()

    assert registry.list_voices() == []
    assert registry.size == 0


def test_missing_dir(tmp_path: Path) -> None:
    """Registry with nonexistent directory returns empty list without error."""
    registry = VoiceRegistry(str(tmp_path / "nonexistent"))
    registry.scan()
    assert registry.list_voices() == []


def test_valid_voices(tmp_path: Path) -> None:
    """Registry finds voices with reference.wav files."""
    voices_dir = tmp_path / "voices"
    _make_voice(voices_dir, "gandalf")
    _make_voice(voices_dir, "gollum")

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()
    assert registry.size == 2

    names = [v.name for v in registry.list_voices()]
    assert "gandalf" in names
    assert "gollum" in names


def test_missing_reference_wav_skipped(tmp_path: Path) -> None:
    """Directories without reference.wav are skipped."""
    voices_dir = tmp_path / "voices"
    _make_voice(voices_dir, "gandalf")
    (voices_dir / "empty-char").mkdir()

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()

    assert registry.size == 1
    assert registry.get_voice("gandalf") is not None
    assert registry.get_voice("empty-char") is None


def test_get_unknown_voice(tmp_path: Path) -> None:
    """Getting an unknown voice returns None."""
    voices_dir = tmp_path / "voices"
    voices_dir.mkdir()

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()

    assert registry.get_voice("unknown") is None


def test_get_voice_case_insensitive(tmp_path: Path) -> None:
    """Voice lookup is case-insensitive."""
    voices_dir = tmp_path / "voices"
    _make_voice(voices_dir, "gandalf")

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()

    assert registry.get_voice("gandalf") is not None
    assert registry.get_voice("GANDALF") is not None


def test_refresh_picks_up_new_voices(tmp_path: Path) -> None:
    """Refresh re-scans and finds newly added voices."""
    voices_dir = tmp_path / "voices"
    _make_voice(voices_dir, "gandalf")

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()
    assert registry.size == 1

    _make_voice(voices_dir, "gollum")
    registry.refresh()
    assert registry.size == 2


def test_chatterbox_engine_detected(tmp_path: Path) -> None:
    """Voice with reference.wav is detected as chatterbox engine."""
    voices_dir = tmp_path / "voices"
    _make_voice(voices_dir, "gandalf")

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()

    voice = registry.get_voice("gandalf")
    assert voice is not None
    assert voice.engine == EngineType.CHATTERBOX
    assert voice.reference_audio_path.name == "reference.wav"


def test_orpheus_engine_detected(tmp_path: Path) -> None:
    """Voice with adapter_config.json is detected as orpheus engine."""
    voices_dir = tmp_path / "voices"
    char_dir = voices_dir / "sauron"
    char_dir.mkdir(parents=True)
    (char_dir / "adapter_config.json").write_text("{}")
    (char_dir / "adapter_model.safetensors").write_bytes(b"\x00" * 10)

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()

    voice = registry.get_voice("sauron")
    assert voice is not None
    assert voice.engine == EngineType.ORPHEUS
    # Path points to the directory itself for adapter-based voices
    assert voice.reference_audio_path == char_dir


def test_orpheus_takes_priority_over_chatterbox(tmp_path: Path) -> None:
    """When both adapter_config.json and reference.wav exist, orpheus takes priority."""
    voices_dir = tmp_path / "voices"
    char_dir = voices_dir / "hybrid"
    char_dir.mkdir(parents=True)
    (char_dir / "reference.wav").write_bytes(b"RIFF" + b"\x00" * 100)
    (char_dir / "adapter_config.json").write_text("{}")

    registry = VoiceRegistry(str(voices_dir))
    registry.scan()

    voice = registry.get_voice("hybrid")
    assert voice is not None
    assert voice.engine == EngineType.ORPHEUS
