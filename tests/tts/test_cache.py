"""Tests for the audio cache."""

from doppelganger.tts.cache import AudioCache


def test_miss_returns_none() -> None:
    """Cache miss returns None."""
    cache = AudioCache(max_size=10)
    assert cache.get("gandalf", "hello") is None


def test_hit_returns_bytes() -> None:
    """Cache hit returns stored bytes."""
    cache = AudioCache(max_size=10)
    data = b"wav-data-here"
    cache.put("gandalf", "hello", data)
    assert cache.get("gandalf", "hello") == data


def test_different_characters_different_keys() -> None:
    """Same text with different characters are separate entries."""
    cache = AudioCache(max_size=10)
    cache.put("gandalf", "hello", b"gandalf-audio")
    cache.put("gollum", "hello", b"gollum-audio")

    assert cache.get("gandalf", "hello") == b"gandalf-audio"
    assert cache.get("gollum", "hello") == b"gollum-audio"


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


def test_disabled_get_returns_none() -> None:
    """Get returns None when cache is disabled."""
    cache = AudioCache(max_size=10)
    cache.put("a", "1", b"data")
    cache.set_enabled(False)
    assert cache.get("a", "1") is None


def test_disabled_put_is_noop() -> None:
    """Put does nothing when cache is disabled."""
    cache = AudioCache(max_size=10)
    cache.set_enabled(False)
    cache.put("a", "1", b"data")
    assert cache.size == 0


def test_enabled_property() -> None:
    """Enabled property reflects set_enabled state."""
    cache = AudioCache(max_size=10)
    assert cache.enabled is True

    cache.set_enabled(False)
    assert cache.enabled is False

    cache.set_enabled(True)
    assert cache.enabled is True


def test_re_enable_allows_operations() -> None:
    """Re-enabling the cache allows get and put to work again."""
    cache = AudioCache(max_size=10)
    cache.put("a", "1", b"data")
    cache.set_enabled(False)
    cache.set_enabled(True)
    assert cache.get("a", "1") == b"data"


def test_remove_existing_entry() -> None:
    """Remove returns True and deletes the entry."""
    cache = AudioCache(max_size=10)
    cache.put("a", "1", b"data")
    key = AudioCache._make_key("a", "1")

    assert cache.remove(key) is True
    assert cache.size == 0


def test_remove_nonexistent_entry() -> None:
    """Remove returns False for a missing key."""
    cache = AudioCache(max_size=10)
    assert cache.remove("nonexistent") is False


def test_list_entries_order() -> None:
    """List entries returns newest-first order."""
    cache = AudioCache(max_size=10)
    cache.put("a", "1", b"a1")
    cache.put("b", "2", b"b2")
    cache.put("c", "3", b"c3")

    entries = cache.list_entries()
    assert len(entries) == 3
    assert entries[0].character == "c"
    assert entries[1].character == "b"
    assert entries[2].character == "a"


def test_list_entries_metadata() -> None:
    """List entries includes correct metadata."""
    cache = AudioCache(max_size=10)
    cache.put("gandalf", "speak friend", b"wav-bytes")

    entries = cache.list_entries()
    assert len(entries) == 1

    entry = entries[0]
    assert entry.character == "gandalf"
    assert entry.text == "speak friend"
    assert entry.byte_size == len(b"wav-bytes")
    assert entry.created_at > 0
    assert entry.key == AudioCache._make_key("gandalf", "speak friend")


def test_total_bytes() -> None:
    """Total bytes sums all entry sizes."""
    cache = AudioCache(max_size=10)
    assert cache.total_bytes == 0

    cache.put("a", "1", b"12345")
    cache.put("b", "2", b"67890ab")
    assert cache.total_bytes == 12


def test_max_size_property() -> None:
    """Max size property exposes the configured limit."""
    cache = AudioCache(max_size=42)
    assert cache.max_size == 42


def test_get_entry_existing() -> None:
    """Get entry returns full CacheEntry for existing key."""
    cache = AudioCache(max_size=10)
    cache.put("gandalf", "hello", b"wav-data")
    key = AudioCache._make_key("gandalf", "hello")

    entry = cache.get_entry(key)
    assert entry is not None
    assert entry.character == "gandalf"
    assert entry.text == "hello"
    assert entry.audio_bytes == b"wav-data"
    assert entry.byte_size == len(b"wav-data")


def test_get_entry_nonexistent() -> None:
    """Get entry returns None for missing key."""
    cache = AudioCache(max_size=10)
    assert cache.get_entry("nonexistent") is None
