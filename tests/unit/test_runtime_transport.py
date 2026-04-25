"""Unit tests for the runtime event transport abstraction."""

import asyncio

from glassbox.runtime.transport import InProcessEventTransport


def test_in_process_event_transport_delivers_events_to_subscribers() -> None:
    async def scenario() -> None:
        transport: InProcessEventTransport[str] = InProcessEventTransport()

        async with transport.subscribe() as subscription:
            transport.publish("hello")

            assert await subscription.get() == "hello"
            assert transport.stats().subscriber_count == 1
            assert transport.stats().dropped_events == 0

        assert transport.stats().subscriber_count == 0

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
