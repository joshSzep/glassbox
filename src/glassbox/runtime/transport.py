"""Runtime event transport abstraction and in-process implementation."""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from contextlib import asynccontextmanager
from typing import Protocol
from typing import TypeVar

from glassbox.runtime.bus import EventBus

T = TypeVar("T")


class RuntimeEventTransportStats(Protocol):
    """Observable counters exposed by a live event transport."""

    subscriber_count: int
    dropped_events: int
    queue_capacity: int
    max_queue_depth: int
    last_published_sequence: int | None


class RuntimeEventSubscription[T](Protocol):
    """Async iterator contract for one live event subscriber."""

    def __aiter__(self) -> AsyncIterator[T]: ...

    async def __anext__(self) -> T: ...

    async def get(self) -> T: ...

    async def aclose(self) -> None: ...


class RuntimeEventTransport[T](Protocol):
    """Publish or subscribe boundary for live runtime event delivery."""

    def publish(self, event: T) -> None: ...

    def subscribe(self) -> AbstractAsyncContextManager[RuntimeEventSubscription[T]]: ...

    def stats(self) -> RuntimeEventTransportStats: ...


class InProcessEventTransport[T]:
    """Transport adapter that preserves the current in-process event-bus behavior."""

    def __init__(self, *, subscriber_queue_size: int = 64) -> None:
        self._bus: EventBus[T] = EventBus(
            subscriber_queue_size=subscriber_queue_size,
        )
        self._last_published_sequence: int | None = None

    def publish(self, event: T) -> None:
        sequence = getattr(event, "sequence", None)
        if isinstance(sequence, int):
            self._last_published_sequence = sequence
        self._bus.publish(event)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[RuntimeEventSubscription[T]]:
        async with self._bus.subscribe() as subscription:
            yield subscription

    def stats(self) -> RuntimeEventTransportStats:
        stats = self._bus.stats()
        return _InProcessEventTransportStats(
            subscriber_count=stats.subscriber_count,
            dropped_events=stats.dropped_events,
            queue_capacity=stats.queue_capacity,
            max_queue_depth=stats.max_queue_depth,
            last_published_sequence=self._last_published_sequence,
        )


class _InProcessEventTransportStats:
    def __init__(
        self,
        *,
        subscriber_count: int,
        dropped_events: int,
        queue_capacity: int,
        max_queue_depth: int,
        last_published_sequence: int | None,
    ) -> None:
        self.subscriber_count = subscriber_count
        self.dropped_events = dropped_events
        self.queue_capacity = queue_capacity
        self.max_queue_depth = max_queue_depth
        self.last_published_sequence = last_published_sequence
