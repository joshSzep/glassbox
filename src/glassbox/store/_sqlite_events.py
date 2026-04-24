"""Canonical event-log reads, writes, and rebuild helpers for SQLite."""

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionResumed
from glassbox.core.events import SessionStarted
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import MessageId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.models import SessionConfig
from glassbox.core.types import SessionStatus
from glassbox.store._sqlite_projections import _apply_projection_event
from glassbox.store._sqlite_projections import _clear_session_projections
from glassbox.store._sqlite_sessions import create_session
from glassbox.store._sqlite_sessions import get_session
from glassbox.store._sqlite_sessions import get_session_state
from glassbox.store._sqlite_sessions import update_session
from glassbox.store._sqlite_utils import CorrelationValue
from glassbox.store._sqlite_utils import _event_from_row
from glassbox.store._sqlite_utils import _stringify_identifier


def append_event(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> EventEnvelope:
    """Append a single event and return the stored envelope with its sequence."""

    stored_events = append_events(connection, [event])
    return stored_events[0]


def append_events(
    connection: sqlite3.Connection,
    events: Sequence[EventEnvelope],
) -> list[EventEnvelope]:
    """Append events transactionally and assign monotonically increasing sequences."""

    if not events:
        return []

    session_id = events[0].session_id
    if any(event.session_id != session_id for event in events):
        raise ValueError("append_events requires all events to share one session_id")

    with connection:
        current_sequence = _ensure_session_row_for_append(connection, events[0])
        stored_events: list[EventEnvelope] = []

        for offset, event in enumerate(events, start=1):
            stored_event = event.model_copy(
                update={
                    "sequence": current_sequence + offset,
                    "event_type": event.payload.event_type,
                }
            )
            stored_events.append(stored_event)
            connection.execute(
                """
                insert into events (
                    session_id,
                    sequence,
                    event_id,
                    event_type,
                    event_version,
                    created_at,
                    turn_id,
                    message_id,
                    tool_call_id,
                    approval_id,
                    actor,
                    payload_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(stored_event.session_id),
                    stored_event.sequence,
                    str(stored_event.event_id),
                    stored_event.event_type,
                    stored_event.event_version,
                    stored_event.created_at.isoformat(),
                    _stringify_identifier(stored_event.turn_id),
                    _stringify_identifier(stored_event.message_id),
                    _stringify_identifier(stored_event.tool_call_id),
                    _stringify_identifier(stored_event.approval_id),
                    _actor_for_event(stored_event),
                    stored_event.payload.model_dump_json(),
                ),
            )
            _apply_projection_event(connection, stored_event)

        _update_session_row_after_append(connection, stored_events[-1])

    return stored_events


def read_session_events(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> list[EventEnvelope]:
    """Read all events for a session in ascending sequence order."""

    rows = connection.execute(
        """
        select
            session_id,
            sequence,
            event_id,
            event_type,
            event_version,
            created_at,
            payload_json
        from events
        where session_id = ?
        order by sequence asc
        """,
        (str(session_id),),
    ).fetchall()
    return [_event_from_row(row) for row in rows]


def read_session_events_after(
    connection: sqlite3.Connection,
    session_id: SessionId,
    after_sequence: int,
) -> list[EventEnvelope]:
    """Read session events with a sequence greater than ``after_sequence``."""

    rows = connection.execute(
        """
        select
            session_id,
            sequence,
            event_id,
            event_type,
            event_version,
            created_at,
            payload_json
        from events
        where session_id = ? and sequence > ?
        order by sequence asc
        """,
        (str(session_id), after_sequence),
    ).fetchall()
    return [_event_from_row(row) for row in rows]


def read_events_by_correlation_id(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    turn_id: TurnId | None = None,
    message_id: MessageId | None = None,
    tool_call_id: ToolCallId | None = None,
    approval_id: ApprovalId | None = None,
) -> list[EventEnvelope]:
    """Read session events filtered by exactly one correlation identifier."""

    correlation_filters: dict[str, CorrelationValue | None] = {
        "turn_id": turn_id,
        "message_id": message_id,
        "tool_call_id": tool_call_id,
        "approval_id": approval_id,
    }
    active_filters = [
        (column_name, value)
        for column_name, value in correlation_filters.items()
        if value is not None
    ]
    if len(active_filters) != 1:
        raise ValueError(
            "read_events_by_correlation_id requires exactly one correlation filter"
        )

    column_name, correlation_value = active_filters[0]
    query = f"""
        select
            session_id,
            sequence,
            event_id,
            event_type,
            event_version,
            created_at,
            payload_json
        from events
        where session_id = ? and {column_name} = ?
        order by sequence asc
    """
    rows = connection.execute(
        query,
        (str(session_id), str(correlation_value)),
    ).fetchall()
    return [_event_from_row(row) for row in rows]


def rebuild_session_projections(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> None:
    """Rebuild all projection tables for a session from canonical events."""

    session_events = read_session_events(connection, session_id)
    with connection:
        _clear_session_projections(connection, session_id)
        for event in session_events:
            _apply_projection_event(connection, event)
        if session_events:
            _update_session_row_after_append(connection, session_events[-1])


def _ensure_session_row_for_append(
    connection: sqlite3.Connection,
    first_event: EventEnvelope,
) -> int:
    session = get_session(connection, first_event.session_id)
    if session is not None:
        return session.last_sequence

    payload = first_event.payload
    if not isinstance(payload, SessionStarted):
        raise ValueError(
            "cannot append non-SessionStarted event before a session row exists"
        )

    create_session(
        connection,
        first_event.session_id,
        SessionConfig(
            model_name=payload.model_name,
            cwd=Path(payload.cwd),
            approval_mode=payload.approval_mode,
            parent_session_id=payload.parent_session_id,
            forked_from_turn_id=payload.forked_from_turn_id,
            forked_from_sequence=payload.forked_from_sequence,
            branch_label=payload.branch_label,
        ),
        status=SessionStatus.RUNNING,
        created_at=first_event.created_at,
        updated_at=first_event.created_at,
        last_sequence=0,
    )
    return 0


def _update_session_row_after_append(
    connection: sqlite3.Connection,
    last_event: EventEnvelope,
) -> None:
    session = get_session(connection, last_event.session_id)
    current_status = session.status if session is not None else SessionStatus.RUNNING
    session_state = get_session_state(connection, last_event.session_id)
    update_session(
        connection,
        last_event.session_id,
        status=(
            session_state.status
            if session_state is not None
            else _session_status_for_event(last_event, current_status)
        ),
        updated_at=last_event.created_at,
        last_sequence=last_event.sequence,
    )


def _session_status_for_event(
    event: EventEnvelope,
    current_status: SessionStatus,
) -> SessionStatus:
    if isinstance(event.payload, SessionResumed):
        return current_status
    if isinstance(event.payload, SessionCompleted):
        return SessionStatus.COMPLETED
    if isinstance(event.payload, SessionFailed):
        return SessionStatus.FAILED
    return SessionStatus.RUNNING


def _actor_for_event(event: EventEnvelope) -> str | None:
    payload_type = event.payload.event_type
    if payload_type == "UserMessageReceived":
        return "user"
    if payload_type == "TranscriptMessageImported":
        return getattr(event.payload, "role", None)
    if payload_type.startswith("AssistantMessage"):
        return "assistant"
    if payload_type == "ApprovalResolved":
        return getattr(event.payload, "decided_by", None)
    return "runtime"


__all__ = [
    "append_event",
    "append_events",
    "read_events_by_correlation_id",
    "read_session_events",
    "read_session_events_after",
    "rebuild_session_projections",
]
