"""SSE event stream route: GET /sessions/{session_id}/events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import StreamingResponse

from glassbox.core.events import EventEnvelope
from glassbox.web.app import RuntimeContextDep

router = APIRouter(prefix="/sessions")

# How long to wait between keepalive comment frames (seconds).
_KEEPALIVE_INTERVAL = 15


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


async def _event_stream(
    request: _HasIsDisconnected,
    context: RuntimeContextDep,
    session_id: UUID,
    after_sequence: int,
) -> AsyncIterator[str]:
    """Yield SSE frames: first replay historical events, then stream live ones."""

    repo = context.repositories.sessions
    bus = context.infrastructure.event_bus

    # Verify session exists before opening a subscription.
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    async with bus.subscribe() as subscription:
        # Replay all persisted events after the requested sequence.
        historical = repo.read_session_events_after(session_id, after_sequence)
        for event in historical:
            if event.session_id == session_id:
                yield _serialize_event(event)

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

            yield _serialize_event(event)


@router.get("/{session_id}/events")
async def stream_session_events(
    session_id: UUID,
    context: RuntimeContextDep,
    request: Request,
    after: int = 0,
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
        _event_stream(request, context, session_id, after),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
