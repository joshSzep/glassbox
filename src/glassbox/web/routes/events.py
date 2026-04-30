"""SSE event stream route: GET /sessions/{session_id}/events."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated
from typing import Protocol
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse

from glassbox.core.events import EventEnvelope
from glassbox.web.app import RuntimeContextDep

router = APIRouter(prefix="/sessions")

# How long to wait between keepalive comment frames (seconds).
_KEEPALIVE_INTERVAL = 15
_DEFAULT_HISTORY_LIMIT = 500
_STREAM_STATUS_EVENT = "glassbox.stream.status"


class _HasIsDisconnected(Protocol):
    """Minimal protocol for the request object used by _event_stream."""

    async def is_disconnected(self) -> bool: ...


def _serialize_event(event: EventEnvelope) -> str:
    """Serialize one event envelope to an SSE frame string.

    Format:
        id: <sequence>
        event: <event_type>
        data: <json payload>
        \\n
    """
    data = json.dumps(
        {
            "event_id": str(event.event_id),
            "session_id": str(event.session_id),
            "sequence": event.sequence,
            "event_type": event.event_type,
            "created_at": event.created_at.isoformat(),
            "payload": event.payload.model_dump(mode="json"),
        }
    )
    return f"id: {event.sequence}\nevent: {event.event_type}\ndata: {data}\n\n"


def _serialize_stream_status(
    *,
    status: str,
    after_sequence: int,
    last_delivered_sequence: int,
    canonical_last_sequence: int,
    replayed_count: int = 0,
    history_truncated: bool = False,
    message: str | None = None,
    projection_health=None,
    transport_stats=None,
) -> str:
    data = json.dumps(
        {
            "status": status,
            "after_sequence": after_sequence,
            "last_delivered_sequence": last_delivered_sequence,
            "canonical_last_sequence": canonical_last_sequence,
            "replayed_count": replayed_count,
            "history_truncated": history_truncated,
            "message": message,
            "projection_health": (
                projection_health.model_dump(mode="json")
                if projection_health is not None
                else None
            ),
            "transport": (
                {
                    "subscriber_count": transport_stats.subscriber_count,
                    "dropped_events": transport_stats.dropped_events,
                    "queue_capacity": transport_stats.queue_capacity,
                    "max_queue_depth": transport_stats.max_queue_depth,
                    "last_published_sequence": transport_stats.last_published_sequence,
                }
                if transport_stats is not None
                else None
            ),
        }
    )
    return f"event: {_STREAM_STATUS_EVENT}\ndata: {data}\n\n"


async def _event_stream(
    request: _HasIsDisconnected,
    context: RuntimeContextDep,
    session_id: UUID,
    after_sequence: int,
    *,
    history_limit: int = _DEFAULT_HISTORY_LIMIT,
) -> AsyncIterator[str]:
    """Yield SSE frames: first replay historical events, then stream live ones."""

    repo = context.repositories.sessions
    transport = context.infrastructure.event_transport

    # Verify session exists before opening a subscription.
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    if after_sequence < 0:
        raise HTTPException(status_code=422, detail="after must be non-negative")

    projection_health = repo.inspect_session_projection_health(session_id)
    canonical_last_sequence = projection_health.canonical_last_sequence
    cursor_ahead = after_sequence > canonical_last_sequence
    last_delivered_sequence = (
        canonical_last_sequence if cursor_ahead else after_sequence
    )

    async with transport.subscribe() as subscription:
        if cursor_ahead:
            yield _serialize_stream_status(
                status="degraded",
                after_sequence=after_sequence,
                last_delivered_sequence=last_delivered_sequence,
                canonical_last_sequence=canonical_last_sequence,
                message=(
                    "Requested cursor is ahead of canonical events; recovered "
                    "to the latest persisted sequence"
                ),
                projection_health=projection_health,
                transport_stats=transport.stats(),
            )

        yield _serialize_stream_status(
            status="replaying_history",
            after_sequence=after_sequence,
            last_delivered_sequence=last_delivered_sequence,
            canonical_last_sequence=canonical_last_sequence,
            projection_health=projection_health,
            transport_stats=transport.stats(),
        )

        # Replay all persisted events after the requested sequence.
        historical = repo.read_session_events_after(
            session_id,
            last_delivered_sequence,
            limit=history_limit + 1,
        )
        replayed_count = 0
        history_truncated = len(historical) > history_limit
        for event in historical[:history_limit]:
            if event.session_id == session_id:
                last_delivered_sequence = max(last_delivered_sequence, event.sequence)
                replayed_count += 1
                yield _serialize_event(event)

        if history_truncated:
            yield _serialize_stream_status(
                status="degraded",
                after_sequence=after_sequence,
                last_delivered_sequence=last_delivered_sequence,
                canonical_last_sequence=canonical_last_sequence,
                replayed_count=replayed_count,
                history_truncated=True,
                message=(
                    "Historical replay was bounded; reconnect with the last "
                    "delivered sequence to continue replaying canonical events"
                ),
                projection_health=projection_health,
                transport_stats=transport.stats(),
            )
            return

        live_status = "degraded" if projection_health.degraded else "live"
        yield _serialize_stream_status(
            status=live_status,
            after_sequence=after_sequence,
            last_delivered_sequence=last_delivered_sequence,
            canonical_last_sequence=canonical_last_sequence,
            replayed_count=replayed_count,
            projection_health=projection_health,
            transport_stats=transport.stats(),
        )

        # Stream live events until the client disconnects.
        while not await request.is_disconnected():
            try:
                event = await asyncio.wait_for(
                    subscription.get(), timeout=_KEEPALIVE_INTERVAL
                )
            except TimeoutError:
                # Send a keepalive comment so the connection stays alive.
                yield ": keepalive\n\n"
                continue

            if event.session_id != session_id:
                continue
            if event.sequence <= last_delivered_sequence:
                continue

            last_delivered_sequence = event.sequence
            yield _serialize_event(event)


@router.get("/{session_id}/events")
async def stream_session_events(
    session_id: UUID,
    context: RuntimeContextDep,
    request: Request,
    after: int = 0,
    limit: Annotated[int, Query(ge=1, le=5000)] = _DEFAULT_HISTORY_LIMIT,
) -> StreamingResponse:
    """Stream live session events as Server-Sent Events.

    Query parameters:
        after (int): Only return events with sequence > after.  Defaults to 0
            (send all events).  Use the ``sequence`` field from a prior event
            to reconnect without replaying the full history.
    """

    repo = context.repositories.sessions
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    return StreamingResponse(
        _event_stream(request, context, session_id, after, history_limit=limit),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Glassbox-Stream-Contract": "cursor-v1",
            "X-Accel-Buffering": "no",
        },
    )
