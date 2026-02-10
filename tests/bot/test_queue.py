"""Tests for TTS request queue and rate limiter."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from doppelganger.bot.queue import QueueFullError, QueueItem, RateLimiter, TTSQueue


def _make_item(request_id: int = 1, discord_id: str = "12345") -> QueueItem:
    """Create a QueueItem with sensible defaults for testing."""
    return QueueItem(
        request_id=request_id,
        user_id=1,
        discord_id=discord_id,
        character="gandalf",
        text="Hello world",
        channel=MagicMock(),
        interaction=MagicMock(),
    )


class TestRateLimiter:
    """Tests for the sliding-window rate limiter."""

    def test_allows_first_request(self) -> None:
        limiter = RateLimiter(requests_per_minute=3)
        assert limiter.try_acquire("user1") is True

    def test_allows_up_to_limit(self) -> None:
        limiter = RateLimiter(requests_per_minute=3)
        assert limiter.try_acquire("user1") is True
        assert limiter.try_acquire("user1") is True
        assert limiter.try_acquire("user1") is True

    def test_rejects_over_limit(self) -> None:
        limiter = RateLimiter(requests_per_minute=2)
        limiter.try_acquire("user1")
        limiter.try_acquire("user1")
        assert limiter.try_acquire("user1") is False

    def test_independent_per_user(self) -> None:
        limiter = RateLimiter(requests_per_minute=1)
        limiter.try_acquire("user1")
        assert limiter.try_acquire("user2") is True

    def test_allows_after_window_expires(self) -> None:
        limiter = RateLimiter(requests_per_minute=1)

        with patch("doppelganger.bot.queue.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            limiter.try_acquire("user1")

            mock_time.monotonic.return_value = 61.0
            assert limiter.try_acquire("user1") is True

    def test_remaining_shows_correct_count(self) -> None:
        limiter = RateLimiter(requests_per_minute=3)
        assert limiter.remaining("user1") == 3
        limiter.try_acquire("user1")
        assert limiter.remaining("user1") == 2
        limiter.try_acquire("user1")
        assert limiter.remaining("user1") == 1

    def test_zero_limit_allows_all(self) -> None:
        limiter = RateLimiter(requests_per_minute=0)
        assert limiter.try_acquire("user1") is True
        assert limiter.remaining("user1") == 999


class TestTTSQueue:
    """Tests for the async TTS request queue."""

    async def test_submit_returns_position(self) -> None:
        queue = TTSQueue(max_depth=10)
        pos1 = await queue.submit(_make_item(request_id=1))
        pos2 = await queue.submit(_make_item(request_id=2))
        assert pos1 == 1
        assert pos2 == 2

    async def test_dequeue_returns_fifo_order(self) -> None:
        queue = TTSQueue(max_depth=10)
        await queue.submit(_make_item(request_id=1))
        await queue.submit(_make_item(request_id=2))

        item = await queue.dequeue()
        assert item.request_id == 1

        item = await queue.dequeue()
        assert item.request_id == 2

    async def test_submit_raises_when_full(self) -> None:
        queue = TTSQueue(max_depth=2)
        await queue.submit(_make_item(request_id=1))
        await queue.submit(_make_item(request_id=2))

        with pytest.raises(QueueFullError):
            await queue.submit(_make_item(request_id=3))

    async def test_depth_tracks_items(self) -> None:
        queue = TTSQueue(max_depth=10)
        assert queue.depth == 0
        await queue.submit(_make_item(request_id=1))
        assert queue.depth == 1
        await queue.dequeue()
        assert queue.depth == 0

    async def test_cancel_removes_item(self) -> None:
        queue = TTSQueue(max_depth=10)
        await queue.submit(_make_item(request_id=1))
        await queue.submit(_make_item(request_id=2))

        result = await queue.cancel(1)
        assert result is True
        assert queue.depth == 1

        item = await queue.dequeue()
        assert item.request_id == 2

    async def test_cancel_returns_false_for_missing(self) -> None:
        queue = TTSQueue(max_depth=10)
        result = await queue.cancel(999)
        assert result is False

    async def test_bump_moves_to_front(self) -> None:
        queue = TTSQueue(max_depth=10)
        await queue.submit(_make_item(request_id=1))
        await queue.submit(_make_item(request_id=2))
        await queue.submit(_make_item(request_id=3))

        result = await queue.bump(3)
        assert result is True

        item = await queue.dequeue()
        assert item.request_id == 3

    async def test_bump_returns_false_for_missing(self) -> None:
        queue = TTSQueue(max_depth=10)
        result = await queue.bump(999)
        assert result is False

    async def test_position_returns_correct_value(self) -> None:
        queue = TTSQueue(max_depth=10)
        await queue.submit(_make_item(request_id=1))
        await queue.submit(_make_item(request_id=2))

        assert queue.position(1) == 1
        assert queue.position(2) == 2
        assert queue.position(999) is None

    async def test_mark_done_clears_processing(self) -> None:
        queue = TTSQueue(max_depth=10)
        await queue.submit(_make_item(request_id=1))

        await queue.dequeue()
        assert queue.processing is not None
        assert queue.processing.request_id == 1

        queue.mark_done()
        assert queue.processing is None

    async def test_dequeue_blocks_until_item_available(self) -> None:
        queue = TTSQueue(max_depth=10)
        result: list[QueueItem] = []

        async def consumer() -> None:
            item = await queue.dequeue()
            result.append(item)

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)
        assert not result

        await queue.submit(_make_item(request_id=1))
        await asyncio.sleep(0.05)
        assert len(result) == 1
        assert result[0].request_id == 1
        task.cancel()

    async def test_get_state_returns_correct_shape(self) -> None:
        queue = TTSQueue(max_depth=10)
        await queue.submit(_make_item(request_id=1))
        await queue.submit(_make_item(request_id=2))

        state = queue.get_state()
        assert state.depth == 2
        assert state.max_depth == 10
        assert state.processing is None
        assert len(state.pending) == 2
        assert state.pending[0].request_id == 1

    async def test_get_state_includes_processing(self) -> None:
        queue = TTSQueue(max_depth=10)
        await queue.submit(_make_item(request_id=1))
        await queue.dequeue()

        state = queue.get_state()
        assert state.processing is not None
        assert state.processing.request_id == 1
        assert state.depth == 0

    async def test_is_full_property(self) -> None:
        queue = TTSQueue(max_depth=2)
        assert queue.is_full is False
        await queue.submit(_make_item(request_id=1))
        assert queue.is_full is False
        await queue.submit(_make_item(request_id=2))
        assert queue.is_full is True
