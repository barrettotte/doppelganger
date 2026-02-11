"""In-memory LRU audio cache backed by OrderedDict."""

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """A single cached audio entry with metadata."""

    key: str
    character: str
    text: str
    audio_bytes: bytes
    byte_size: int
    created_at: float


class AudioCache:
    """LRU cache for generated audio bytes, keyed by character+text."""

    def __init__(self, max_size: int = 100) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._enabled: bool = True

    @property
    def enabled(self) -> bool:
        """Whether the cache is currently accepting reads and writes."""
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        """Enable or disable the cache."""
        self._enabled = value

    @property
    def max_size(self) -> int:
        """Maximum number of entries the cache can hold."""
        return self._max_size

    @property
    def total_bytes(self) -> int:
        """Sum of byte sizes across all cached entries."""
        return sum(entry.byte_size for entry in self._cache.values())

    @staticmethod
    def _make_key(character: str, text: str) -> str:
        """Generate a deterministic cache key from character and text."""
        raw = f"{character}:{text}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, character: str, text: str) -> bytes | None:
        """Retrieve cached audio. Moves entry to end on hit."""
        if not self._enabled:
            return None

        key = self._make_key(character, text)

        if key not in self._cache:
            return None

        self._cache.move_to_end(key)
        return self._cache[key].audio_bytes

    def put(self, character: str, text: str, audio_bytes: bytes) -> None:
        """Store audio bytes, evicting oldest entry if over max_size."""
        if not self._enabled:
            return

        key = self._make_key(character, text)

        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = CacheEntry(
                key=key,
                character=character,
                text=text,
                audio_bytes=audio_bytes,
                byte_size=len(audio_bytes),
                created_at=self._cache[key].created_at,
            )
            return

        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(
            key=key,
            character=character,
            text=text,
            audio_bytes=audio_bytes,
            byte_size=len(audio_bytes),
            created_at=time.time(),
        )

    def get_entry(self, key: str) -> CacheEntry | None:
        """Retrieve a full cache entry by its key."""
        return self._cache.get(key)

    def remove(self, key: str) -> bool:
        """Remove a single entry by key. Returns True if found."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def remove_by_character(self, character: str) -> int:
        """Remove all entries for a character. Returns the number of entries removed."""
        keys = [k for k, v in self._cache.items() if v.character == character]
        for k in keys:
            del self._cache[k]
        return len(keys)

    def list_entries(self) -> list[CacheEntry]:
        """Return all entries newest-first."""
        return list(reversed(self._cache.values()))

    def clear(self) -> None:
        """Remove all cached entries."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        return len(self._cache)
