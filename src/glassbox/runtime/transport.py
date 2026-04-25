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

    def publish(self, event: T) -> None:
        self._bus.publish(event)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[RuntimeEventSubscription[T]]:
        async with self._bus.subscribe() as subscription:
            yield subscription

    def stats(self) -> RuntimeEventTransportStats:
        return self._bus.stats()
