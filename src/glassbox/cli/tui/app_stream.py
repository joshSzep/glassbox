"""Live event stream lifecycle helpers for the terminal app."""

import asyncio
from typing import Any

from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import with_stream_status

STREAM_RECONNECT_RETRY_COUNT = 3
STREAM_RECONNECT_RETRY_DELAYS_SECONDS = (0.0, 0.0, 0.0)


async def consume_live_events(app: Any) -> None:
    reconnect_attempts = 0
    while True:
        try:
            async for event in app.client_adapter.stream_events(
                after_sequence=app.state.header.last_sequence,
            ):
                app.apply_runtime_event(event)
            if reconnect_attempts > 0:
                app.update_conversation_state(
                    with_stream_status(
                        app.state,
                        TerminalStreamStatus.LIVE,
                        detail="reconnected",
                    )
                )
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            reconnect_attempts += 1
            if reconnect_attempts > STREAM_RECONNECT_RETRY_COUNT:
                app.update_conversation_state(
                    with_stream_status(
                        app.state,
                        TerminalStreamStatus.UNAVAILABLE,
                        detail=(
                            "stream unavailable after "
                            f"{STREAM_RECONNECT_RETRY_COUNT} retries: {exc}"
                        ),
                    )
                )
                return
            app.update_conversation_state(
                with_stream_status(
                    app.state,
                    TerminalStreamStatus.RECONNECTING,
                    detail=(
                        f"retry {reconnect_attempts}/"
                        f"{STREAM_RECONNECT_RETRY_COUNT}: {exc}"
                    ),
                )
            )
            delay = STREAM_RECONNECT_RETRY_DELAYS_SECONDS[
                min(
                    reconnect_attempts - 1,
                    len(STREAM_RECONNECT_RETRY_DELAYS_SECONDS) - 1,
                )
            ]
            if delay > 0:
                await asyncio.sleep(delay)
