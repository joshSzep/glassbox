"""SQLite connection and schema bootstrap for Glassbox."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from glassbox.core.events import (
    EventEnvelope,
    SessionCompleted,
    SessionFailed,
    SessionStarted,
)
from glassbox.core.ids import ApprovalId, MessageId, SessionId, ToolCallId, TurnId
from glassbox.core.types import SessionStatus

SCHEMA_VERSION = 1

type CorrelationValue = TurnId | MessageId | ToolCallId | ApprovalId

BOOTSTRAP_STATEMENTS = (
    """
    create table if not exists schema_migrations (
        version integer primary key,
        applied_at text not null default current_timestamp
    )
    """,
    """
    create table if not exists sessions (
        session_id text primary key,
        status text not null,
        created_at text not null,
        updated_at text not null,
        cwd text not null,
        model_name text not null,
        approval_mode text not null,
        last_sequence integer not null default 0
    )
    """,
    """
    create index if not exists idx_sessions_status_updated
        on sessions (status, updated_at desc)
    """,
    """
    create table if not exists events (
        session_id text not null,
        sequence integer not null,
        event_id text not null,
        event_type text not null,
        event_version integer not null,
        created_at text not null,
        turn_id text,
        message_id text,
        tool_call_id text,
        approval_id text,
        actor text,
        payload_json text not null,
        primary key (session_id, sequence),
        unique (event_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_events_session_created
        on events (session_id, created_at)
    """,
    """
    create index if not exists idx_events_session_type_sequence
        on events (session_id, event_type, sequence)
    """,
    """
    create index if not exists idx_events_turn
        on events (session_id, turn_id, sequence)
    """,
    """
    create index if not exists idx_events_message
        on events (session_id, message_id, sequence)
    """,
    """
    create index if not exists idx_events_tool_call
        on events (session_id, tool_call_id, sequence)
    """,
    """
    create index if not exists idx_events_approval
        on events (session_id, approval_id, sequence)
    """,
)


def open_database(path: Path) -> sqlite3.Connection:
    """Open a SQLite database connection configured for local runtime use."""

    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("pragma foreign_keys = on")
    connection.execute("pragma journal_mode = wal")
    connection.execute("pragma synchronous = normal")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create the bootstrap schema if it does not already exist."""

    with connection:
        for statement in BOOTSTRAP_STATEMENTS:
            connection.execute(statement)

        connection.execute(
            "insert or ignore into schema_migrations(version) values (?)",
            (SCHEMA_VERSION,),
        )


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


def _ensure_session_row_for_append(
    connection: sqlite3.Connection,
    first_event: EventEnvelope,
) -> int:
    row = connection.execute(
        "select last_sequence from sessions where session_id = ?",
        (str(first_event.session_id),),
    ).fetchone()
    if row is not None:
        return int(row[0])

    payload = first_event.payload
    if not isinstance(payload, SessionStarted):
        raise ValueError(
            "cannot append non-SessionStarted event before a session row exists"
        )

    connection.execute(
        """
        insert into sessions (
            session_id,
            status,
            created_at,
            updated_at,
            cwd,
            model_name,
            approval_mode,
            last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(first_event.session_id),
            SessionStatus.RUNNING,
            first_event.created_at.isoformat(),
            first_event.created_at.isoformat(),
            payload.cwd,
            payload.model_name,
            payload.approval_mode,
            0,
        ),
    )
    return 0


def _update_session_row_after_append(
    connection: sqlite3.Connection,
    last_event: EventEnvelope,
) -> None:
    connection.execute(
        """
        update sessions
        set status = ?, updated_at = ?, last_sequence = ?
        where session_id = ?
        """,
        (
            _session_status_for_event(last_event),
            last_event.created_at.isoformat(),
            last_event.sequence,
            str(last_event.session_id),
        ),
    )


def _session_status_for_event(event: EventEnvelope) -> SessionStatus:
    if isinstance(event.payload, SessionCompleted):
        return SessionStatus.COMPLETED
    if isinstance(event.payload, SessionFailed):
        return SessionStatus.FAILED
    return SessionStatus.RUNNING


def _actor_for_event(event: EventEnvelope) -> str | None:
    payload_type = event.payload.event_type
    if payload_type == "UserMessageReceived":
        return "user"
    if payload_type.startswith("AssistantMessage"):
        return "assistant"
    if payload_type == "ApprovalResolved":
        return getattr(event.payload, "decided_by", None)
    return "runtime"


def _event_from_row(row: sqlite3.Row) -> EventEnvelope:
    payload_data = json.loads(row["payload_json"])
    return EventEnvelope.model_validate(
        {
            "event_id": row["event_id"],
            "session_id": row["session_id"],
            "sequence": row["sequence"],
            "event_type": row["event_type"],
            "event_version": row["event_version"],
            "created_at": row["created_at"],
            "payload": payload_data,
        }
    )


def _stringify_identifier(value: CorrelationValue | None) -> str | None:
    if value is None:
        return None
    return str(value)
