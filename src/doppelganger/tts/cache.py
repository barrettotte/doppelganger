"""In-memory LRU audio cache backed by OrderedDict."""

import hashlib
from collections import OrderedDict


class AudioCache:
    """LRU cache for generated audio bytes, keyed by character+text."""

    def __init__(self, max_size: int = 100) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, bytes] = OrderedDict()

    @staticmethod
    def _make_key(character: str, text: str) -> str:
        raw = f"{character}:{text}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, character: str, text: str) -> bytes | None:
        """Retrieve cached audio. Moves entry to end on hit."""
        key = self._make_key(character, text)

        if key not in self._cache:
            return None

        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, character: str, text: str, audio_bytes: bytes) -> None:
        """Store audio bytes, evicting oldest entry if over max_size."""
        key = self._make_key(character, text)

        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = audio_bytes
            return

        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[key] = audio_bytes

    def clear(self) -> None:
        """Remove all cached entries."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        return len(self._cache)
