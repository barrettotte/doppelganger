"""Voice registry that scans the filesystem for reference audio files."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from doppelganger.tts.engine import EngineType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceEntry:
    """A registered voice with its reference audio path and engine type."""

    name: str
    reference_audio_path: Path
    engine: EngineType = field(default=EngineType.CHATTERBOX)


class VoiceRegistry:
    """
    Scans a voices directory for character reference audio files.
    Expected layout - voices/character-name/reference.wav
    """

    def __init__(self, voices_dir: str) -> None:
        self._voices_dir = Path(voices_dir)
        self._voices: dict[str, VoiceEntry] = {}

    def scan(self) -> None:
        """Walk the voices directory and register all valid voices."""
        self._voices.clear()

        if not self._voices_dir.exists():
            logger.warning("Voices directory does not exist: %s", self._voices_dir)
            return

        for subdir in sorted(self._voices_dir.iterdir()):
            if not subdir.is_dir():
                continue

            has_adapter = (subdir / "adapter_config.json").is_file()
            has_reference = (subdir / "reference.wav").is_file()

            if has_adapter:
                # LoRA adapter directory - use Orpheus engine, path is the dir itself
                name = subdir.name.lower()
                self._voices[name] = VoiceEntry(name=name, reference_audio_path=subdir, engine=EngineType.ORPHEUS)
                logger.info("Registered voice: %s (orpheus)", name)
            elif has_reference:
                # Reference WAV - use Chatterbox engine
                name = subdir.name.lower()
                self._voices[name] = VoiceEntry(
                    name=name, reference_audio_path=subdir / "reference.wav", engine=EngineType.CHATTERBOX
                )
                logger.info("Registered voice: %s (chatterbox)", name)
            else:
                logger.debug("Skipping %s: no reference.wav or adapter_config.json found", subdir.name)

        logger.info("Voice registry loaded %d voice(s)", len(self._voices))

    def list_voices(self) -> list[VoiceEntry]:
        """Return all registered voices."""
        return list(self._voices.values())

    def get_voice(self, name: str) -> VoiceEntry | None:
        """Look up a voice by name. Returns None if not found."""
        return self._voices.get(name.lower())

    def refresh(self) -> None:
        """Clear and re-scan the voices directory."""
        self.scan()

    @property
    def voices_dir(self) -> Path:
        """The directory containing voice reference audio files."""
        return self._voices_dir

    @property
    def size(self) -> int:
        """Number of registered voices."""
        return len(self._voices)
