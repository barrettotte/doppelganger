"""TTS request queue and per-user rate limiter."""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QueueItemState:
    """Serializable snapshot of a single queue item for API responses."""

    request_id: int
    user_id: int
    discord_id: str
    character: str
    text: str
    submitted_at: float


@dataclass
class QueueState:
    """Serializable snapshot of the full queue for API responses."""

    depth: int
    max_depth: int
    processing: QueueItemState | None
    pending: list[QueueItemState]


@dataclass
class QueueItem:
    """A single TTS request waiting in the queue."""

    request_id: int
    user_id: int
    discord_id: str
    character: str
    text: str
    channel: Any
    interaction: Any
    submitted_at: float = field(default_factory=time.monotonic)


class RateLimiter:
    """Sliding-window per-user rate limiter."""

    def __init__(self, requests_per_minute: int) -> None:
        self._max_rpm = requests_per_minute
        self._timestamps: dict[str, deque[float]] = {}

    def try_acquire(self, user_id: str) -> bool:
        """Check if the user is within rate limits and record the attempt if allowed."""
        if self._max_rpm <= 0:
            return True

        now = time.monotonic()

        if user_id not in self._timestamps:
            self._timestamps[user_id] = deque()

        timestamps = self._timestamps[user_id]
        while timestamps and now - timestamps[0] > 60:
            timestamps.popleft()

        if len(timestamps) >= self._max_rpm:
            return False

        timestamps.append(now)
        return True

    def remaining(self, user_id: str) -> int:
        """Return how many requests the user has left in the current window."""
        if self._max_rpm <= 0:
            return 999

        now = time.monotonic()

        timestamps = self._timestamps.get(user_id)
        if timestamps is None:
            return self._max_rpm

        while timestamps and now - timestamps[0] > 60:
            timestamps.popleft()

        return max(0, self._max_rpm - len(timestamps))


class TTSQueue:
    """Async TTS request queue with cancel and bump support."""

    def __init__(self, max_depth: int = 20) -> None:
        self._items: deque[QueueItem] = deque()
        self._max_depth = max_depth
        self._condition = asyncio.Condition()
        self._processing: QueueItem | None = None

    @property
    def depth(self) -> int:
        """Number of items waiting in the queue (not including the one being processed)."""
        return len(self._items)

    @property
    def is_full(self) -> bool:
        """Check if the queue has reached max depth."""
        return len(self._items) >= self._max_depth

    @property
    def processing(self) -> QueueItem | None:
        """The item currently being processed, if any."""
        return self._processing

    async def submit(self, item: QueueItem) -> int:
        """Add a request to the queue. Returns 1-based queue position."""
        async with self._condition:
            if self.is_full:
                raise QueueFullError(self._max_depth)

            self._items.append(item)
            position = len(self._items)

            self._condition.notify()
            logger.info("Queued request %d at position %d", item.request_id, position)
            return position

    async def dequeue(self) -> QueueItem:
        """Wait for and return the next item. Blocks until an item is available."""
        async with self._condition:
            while not self._items:
                await self._condition.wait()

            item = self._items.popleft()
            self._processing = item
            return item

    def mark_done(self) -> None:
        """Mark the currently-processing item as finished."""
        self._processing = None

    async def cancel(self, request_id: int) -> bool:
        """Remove a pending request from the queue. Returns True if found and removed."""
        async with self._condition:
            for i, item in enumerate(self._items):
                if item.request_id == request_id:
                    del self._items[i]
                    logger.info("Cancelled request %d", request_id)
                    return True

        return False

    async def bump(self, request_id: int) -> bool:
        """Move a pending request to the front of the queue. Returns True if found."""
        async with self._condition:
            for i, item in enumerate(self._items):
                if item.request_id == request_id:
                    del self._items[i]
                    self._items.appendleft(item)
                    logger.info("Bumped request %d to front", request_id)
                    return True

        return False

    def position(self, request_id: int) -> int | None:
        """Get the 1-based queue position of a request, or None if not found."""
        for i, item in enumerate(self._items):
            if item.request_id == request_id:
                return i + 1
        return None

    def _item_to_state(self, item: QueueItem) -> QueueItemState:
        """Convert a QueueItem to a serializable state dict."""
        return QueueItemState(
            request_id=item.request_id,
            user_id=item.user_id,
            discord_id=item.discord_id,
            character=item.character,
            text=item.text[:50],
            submitted_at=item.submitted_at,
        )

    def get_state(self) -> QueueState:
        """Return the current queue state for API consumption."""
        pending = [self._item_to_state(item) for item in self._items]

        processing = None
        if self._processing is not None:
            processing = self._item_to_state(self._processing)

        return QueueState(
            depth=self.depth,
            max_depth=self._max_depth,
            processing=processing,
            pending=pending,
        )


class QueueFullError(Exception):
    """Raised when the queue has reached its maximum depth."""

    def __init__(self, max_depth: int) -> None:
        self.max_depth = max_depth
        super().__init__(f"Queue is full ({max_depth} items)")
