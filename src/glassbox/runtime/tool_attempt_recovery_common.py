"""Shared lookup helpers for durable tool-attempt recovery."""

import json
from typing import Any

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.models import ToolAttemptRecord
from glassbox.runtime.tool_attempt_recovery_models import ToolAttemptRecoveryError
from glassbox.services import SessionRepository


def require_attempt(
    repository: SessionRepository,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
) -> ToolAttemptRecord:
    """Return a projected attempt or raise an operator-facing recovery error."""

    attempt = repository.get_tool_attempt(session_id, tool_attempt_id)
    if attempt is None:
        raise ToolAttemptRecoveryError(
            f"tool attempt {tool_attempt_id} not found in session {session_id}"
        )
    return attempt


def source_tool_call_payload(
    repository: SessionRepository,
    session_id: SessionId,
    attempt: ToolAttemptRecord,
) -> ModelToolCallRequested | None:
    """Find the retained model tool-call request for one attempt."""

    if attempt.tool_call_id is None:
        return None
    for event in repository.read_events_by_correlation_id(
        session_id,
        tool_call_id=attempt.tool_call_id,
    ):
        if isinstance(event.payload, ModelToolCallRequested):
            return event.payload
    return None


def decode_arguments_json(value: str) -> dict[str, object] | None:
    """Decode retained tool-call arguments when they are object-shaped JSON."""

    try:
        decoded: Any = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return {str(key): value for key, value in decoded.items()}


def correlated_attempt_events(
    repository: SessionRepository,
    session_id: SessionId,
    attempt: ToolAttemptRecord,
) -> list[EventEnvelope]:
    """Return events correlated by attempt id or source tool-call id."""

    events_by_id = {
        event.event_id: event
        for event in repository.read_events_by_correlation_id(
            session_id,
            tool_attempt_id=attempt.tool_attempt_id,
        )
    }
    if attempt.tool_call_id is not None:
        for event in repository.read_events_by_correlation_id(
            session_id,
            tool_call_id=attempt.tool_call_id,
        ):
            events_by_id[event.event_id] = event
    return sorted(events_by_id.values(), key=lambda event: event.sequence)


__all__ = [
    "correlated_attempt_events",
    "decode_arguments_json",
    "require_attempt",
    "source_tool_call_payload",
]
