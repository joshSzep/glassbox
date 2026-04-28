"""Unit tests for the in-process runtime event bus."""

import asyncio

import pytest

from glassbox.runtime import EventBus


def test_event_bus_delivers_events_to_a_single_subscriber() -> None:
    async def scenario() -> None:
        bus: EventBus[str] = EventBus()

        async with bus.subscribe() as subscription:
            bus.publish("hello")

            assert await subscription.get() == "hello"
            assert bus.stats().subscriber_count == 1
            assert bus.stats().dropped_events == 0
            assert bus.stats().queue_capacity == 64
            assert bus.stats().max_queue_depth == 1

        assert bus.stats().subscriber_count == 0

    asyncio.run(scenario())


def test_event_bus_fans_out_to_multiple_subscribers() -> None:
    async def scenario() -> None:
        bus: EventBus[int] = EventBus()

        async with bus.subscribe() as first_subscription:
            async with bus.subscribe() as second_subscription:
                bus.publish(7)

                assert await first_subscription.get() == 7
                assert await second_subscription.get() == 7

    asyncio.run(scenario())


def test_event_bus_drops_oldest_item_for_slow_subscribers() -> None:
    async def scenario() -> None:
        bus: EventBus[str] = EventBus(subscriber_queue_size=1)

        async with bus.subscribe() as subscription:
            bus.publish("stale")
            bus.publish("fresh")

            assert await subscription.get() == "fresh"
            assert bus.stats().dropped_events == 1
            assert bus.stats().max_queue_depth == 1

    asyncio.run(scenario())


def test_event_bus_supports_subscriber_cancellation_and_cleanup() -> None:
    async def scenario() -> None:
        bus: EventBus[str] = EventBus()

        async with bus.subscribe() as subscription:
            waiting_task = asyncio.create_task(subscription.get())
            await asyncio.sleep(0)

            waiting_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiting_task

        assert bus.stats().subscriber_count == 0

    asyncio.run(scenario())


def test_event_bus_rejects_invalid_queue_sizes() -> None:
    with pytest.raises(ValueError):
        EventBus[int](subscriber_queue_size=0)
