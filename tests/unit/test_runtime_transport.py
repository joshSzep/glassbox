"""Unit tests for the runtime event transport abstraction."""

import asyncio
from dataclasses import dataclass

from glassbox.runtime.transport import InProcessEventTransport


@dataclass(frozen=True, slots=True)
class _SequencedEvent:
    sequence: int


def test_in_process_event_transport_delivers_events_to_subscribers() -> None:
    async def scenario() -> None:
        transport: InProcessEventTransport[str] = InProcessEventTransport()

        async with transport.subscribe() as subscription:
            transport.publish("hello")

            assert await subscription.get() == "hello"
            assert transport.stats().subscriber_count == 1
            assert transport.stats().dropped_events == 0
            assert transport.stats().queue_capacity == 64
            assert transport.stats().max_queue_depth == 1
            assert transport.stats().last_published_sequence is None

        assert transport.stats().subscriber_count == 0

    asyncio.run(scenario())


def test_in_process_event_transport_tracks_last_published_sequence() -> None:
    async def scenario() -> None:
        transport: InProcessEventTransport[_SequencedEvent] = InProcessEventTransport()

        async with transport.subscribe() as subscription:
            transport.publish(_SequencedEvent(sequence=41))
            transport.publish(_SequencedEvent(sequence=42))

            assert (await subscription.get()).sequence == 41
            assert transport.stats().last_published_sequence == 42
            assert transport.stats().max_queue_depth == 2

    asyncio.run(scenario())


def test_in_process_event_transport_drops_oldest_item_for_slow_subscribers() -> None:
    async def scenario() -> None:
        transport: InProcessEventTransport[_SequencedEvent] = InProcessEventTransport(
            subscriber_queue_size=2
        )

        async with transport.subscribe() as subscription:
            transport.publish(_SequencedEvent(sequence=1))
            transport.publish(_SequencedEvent(sequence=2))
            transport.publish(_SequencedEvent(sequence=3))

            assert (await subscription.get()).sequence == 2
            assert (await subscription.get()).sequence == 3
            stats = transport.stats()
            assert stats.dropped_events == 1
            assert stats.queue_capacity == 2
            assert stats.max_queue_depth == 2
            assert stats.last_published_sequence == 3

    asyncio.run(scenario())


def test_in_process_event_transport_fans_out_to_multiple_subscribers() -> None:
    async def scenario() -> None:
        transport: InProcessEventTransport[int] = InProcessEventTransport()

        async with transport.subscribe() as first_subscription:
            async with transport.subscribe() as second_subscription:
                transport.publish(7)

                assert await first_subscription.get() == 7
                assert await second_subscription.get() == 7

    asyncio.run(scenario())
