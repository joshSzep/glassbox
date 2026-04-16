"""In-process event fanout for runtime consumers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class EventBusStats:
    """Observable counters for event bus health."""

    subscriber_count: int
    dropped_events: int


class EventBusSubscription[T]:
    """Async iterator over events for one subscriber."""

    def __init__(self, bus: EventBus[T], queue: asyncio.Queue[T]) -> None:
        self._bus = bus
        self._queue = queue
        self._closed = False

    def __aiter__(self) -> AsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        if self._closed:
            raise StopAsyncIteration
        return await self._queue.get()

    async def get(self) -> T:
        """Read one event from the subscription queue."""

        return await self.__anext__()

    async def aclose(self) -> None:
        """Detach the subscriber from the parent bus."""

        if self._closed:
            return
        self._closed = True
        self._bus._unsubscribe(self._queue)


class EventBus[T]:
    """Bounded in-process pub-sub with non-blocking publish semantics."""

    def __init__(self, *, subscriber_queue_size: int = 64) -> None:
        if subscriber_queue_size < 1:
            raise ValueError("subscriber_queue_size must be at least 1")

        self._subscriber_queue_size = subscriber_queue_size
        self._subscribers: set[asyncio.Queue[T]] = set()
        self._dropped_events = 0

    def publish(self, event: T) -> None:
        """Fan out an event to all subscribers without blocking the caller."""

        for queue in tuple(self._subscribers):
            self._publish_to_queue(queue, event)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[EventBusSubscription[T]]:
        """Register a subscriber for the duration of the async context."""

        queue: asyncio.Queue[T] = asyncio.Queue(maxsize=self._subscriber_queue_size)
        self._subscribers.add(queue)
        subscription = EventBusSubscription(self, queue)
        try:
            yield subscription
        finally:
            await subscription.aclose()

    def stats(self) -> EventBusStats:
        """Return a snapshot of current subscriber and drop counts."""

        return EventBusStats(
            subscriber_count=len(self._subscribers),
            dropped_events=self._dropped_events,
        )

    def _publish_to_queue(self, queue: asyncio.Queue[T], event: T) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            # Prefer recent runtime state over stale items
            # when a subscriber falls behind.
            _ = queue.get_nowait()
            self._dropped_events += 1
            queue.put_nowait(event)

    def _unsubscribe(self, queue: asyncio.Queue[T]) -> None:
        self._subscribers.discard(queue)
