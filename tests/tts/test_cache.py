"""Tests for the audio cache."""

from doppelganger.tts.cache import AudioCache


def test_miss_returns_none() -> None:
    """Cache miss returns None."""
    cache = AudioCache(max_size=10)
    assert cache.get("shane-gillis", "hello") is None


def test_hit_returns_bytes() -> None:
    """Cache hit returns stored bytes."""
    cache = AudioCache(max_size=10)
    data = b"wav-data-here"
    cache.put("shane-gillis", "hello", data)
    assert cache.get("shane-gillis", "hello") == data


def test_different_characters_different_keys() -> None:
    """Same text with different characters are separate entries."""
    cache = AudioCache(max_size=10)
    cache.put("shane-gillis", "hello", b"shane-gillis-audio")
    cache.put("joe-rogan", "hello", b"joe-rogan-audio")

    assert cache.get("shane-gillis", "hello") == b"shane-gillis-audio"
    assert cache.get("joe-rogan", "hello") == b"joe-rogan-audio"


def test_lru_eviction() -> None:
    """Oldest entry is evicted when cache is full."""
    cache = AudioCache(max_size=2)
    cache.put("a", "1", b"a1")
    cache.put("b", "2", b"b2")
    cache.put("c", "3", b"c3")  # should evict a:1

    assert cache.get("a", "1") is None
    assert cache.get("b", "2") == b"b2"
    assert cache.get("c", "3") == b"c3"


def test_access_refreshes_lru() -> None:
    """Accessing an entry moves it to the end, preventing eviction."""
    cache = AudioCache(max_size=2)
    cache.put("a", "1", b"a1")
    cache.put("b", "2", b"b2")

    cache.get("a", "1")  # Access "a" to refresh it
    cache.put("c", "3", b"c3")  # Add new entry, evicts "b" (now oldest)

    assert cache.get("a", "1") == b"a1"
    assert cache.get("b", "2") is None
    assert cache.get("c", "3") == b"c3"


def test_clear() -> None:
    """Clear removes all entries."""
    cache = AudioCache(max_size=10)
    cache.put("a", "1", b"data")
    cache.put("b", "2", b"data")
    assert cache.size == 2

    cache.clear()
    assert cache.size == 0
    assert cache.get("a", "1") is None


def test_size_property() -> None:
    """Size tracks the number of entries."""
    cache = AudioCache(max_size=10)
    assert cache.size == 0

    cache.put("a", "1", b"data")
    assert cache.size == 1

    cache.put("b", "2", b"data")
    assert cache.size == 2


def test_put_updates_existing() -> None:
    """Putting the same key updates the value."""
    cache = AudioCache(max_size=10)
    cache.put("a", "1", b"old")
    cache.put("a", "1", b"new")
    assert cache.get("a", "1") == b"new"
    assert cache.size == 1
