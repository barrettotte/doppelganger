"""Voice registry that scans the filesystem for reference audio files."""

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceEntry:
    """A registered voice with its reference audio path."""

    name: str
    reference_audio_path: Path


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

            ref_audio = subdir / "reference.wav"
            if not ref_audio.is_file():
                logger.debug("Skipping %s: no reference.wav found", subdir.name)
                continue

            name = subdir.name.lower()
            self._voices[name] = VoiceEntry(name=name, reference_audio_path=ref_audio)
            logger.info("Registered voice: %s", name)

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
    def size(self) -> int:
        """Number of registered voices."""
        return len(self._voices)
