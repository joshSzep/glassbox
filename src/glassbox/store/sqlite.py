"""SQLite connection and schema bootstrap for Glassbox."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from glassbox.core.events import (
    ApprovalRequested,
    ApprovalResolved,
    AssistantMessageCompleted,
    AssistantMessageDelta,
    AssistantMessageStarted,
    EventEnvelope,
    ModelCallCompleted,
    ModelCallStarted,
    ModelToolCallRequested,
    SessionCompleted,
    SessionFailed,
    SessionResumed,
    SessionStarted,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    TurnCompleted,
    TurnFailed,
    TurnStarted,
    UserAnswerProvided,
    UserMessageReceived,
    UserQuestionAsked,
)
from glassbox.core.ids import (
    ApprovalId,
    MessageId,
    QuestionId,
    SessionId,
    ToolCallId,
    TurnId,
)
from glassbox.core.models import (
    ApprovalRecord,
    MessagePart,
    SessionConfig,
    SessionRecord,
    SessionState,
    ToolCallRecord,
    TranscriptMessage,
    TurnMetricsRecord,
)
from glassbox.core.types import (
    ApprovalMode,
    ApprovalStatus,
    SessionStatus,
    ToolExecutionStatus,
)

SCHEMA_VERSION = 4

type CorrelationValue = TurnId | MessageId | ToolCallId | ApprovalId | QuestionId

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
        parent_session_id text,
        forked_from_turn_id text,
        forked_from_sequence integer,
        branch_label text,
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
    """
    create table if not exists session_state (
        session_id text primary key,
        status text not null,
        current_turn_id text,
        pending_approval_id text,
        pending_question_id text,
        last_sequence integer not null,
        updated_at text not null,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create table if not exists transcript_messages (
        message_id text primary key,
        session_id text not null,
        turn_id text,
        role text not null,
        status text not null,
        created_at text not null,
        completed_at text,
        content_text text not null default '',
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_transcript_messages_session_created
        on transcript_messages (session_id, created_at)
    """,
    """
    create table if not exists tool_calls (
        tool_call_id text primary key,
        session_id text not null,
        turn_id text not null,
        tool_name text not null,
        status text not null,
        started_at text,
        completed_at text,
        summary text,
        exit_code integer,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_tool_calls_session_status
        on tool_calls (session_id, status)
    """,
    """
    create index if not exists idx_tool_calls_session_turn
        on tool_calls (session_id, turn_id)
    """,
    """
    create table if not exists approvals (
        approval_id text primary key,
        session_id text not null,
        turn_id text not null,
        subject text not null,
        reason text not null,
        status text not null,
        requested_at text not null,
        resolved_at text,
        decided_by text,
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_approvals_session_status
        on approvals (session_id, status)
    """,
    """
    create table if not exists turn_metrics (
        session_id text not null,
        turn_id text not null,
        started_at text,
        completed_at text,
        turn_duration_ms integer,
        model_call_count integer not null default 0,
        model_duration_ms_total integer not null default 0,
        model_input_tokens_total integer not null default 0,
        model_output_tokens_total integer not null default 0,
        tool_call_count integer not null default 0,
        tool_duration_ms_total integer not null default 0,
        succeeded_tool_call_count integer not null default 0,
        failed_tool_call_count integer not null default 0,
        primary key (session_id, turn_id),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_turn_metrics_session_started
        on turn_metrics (session_id, started_at desc)
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

        _ensure_sessions_lineage_schema(connection)

        connection.execute(
            "insert or ignore into schema_migrations(version) values (?)",
            (SCHEMA_VERSION,),
        )


def create_session(
    connection: sqlite3.Connection,
    session_id: SessionId,
    config: SessionConfig,
    *,
    status: SessionStatus = SessionStatus.IDLE,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    last_sequence: int = 0,
) -> SessionRecord:
    """Create and return a coarse session metadata row."""

    effective_created_at = created_at or datetime.now(UTC)
    effective_updated_at = updated_at or effective_created_at
    with connection:
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
                parent_session_id,
                forked_from_turn_id,
                forked_from_sequence,
                branch_label,
                last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(session_id),
                status,
                effective_created_at.isoformat(),
                effective_updated_at.isoformat(),
                str(config.cwd),
                config.model_name,
                config.approval_mode,
                _stringify_identifier(config.parent_session_id),
                _stringify_identifier(config.forked_from_turn_id),
                config.forked_from_sequence,
                config.branch_label,
                last_sequence,
            ),
        )
    created_session = get_session(connection, session_id)
    if created_session is None:
        raise RuntimeError("create_session did not persist the session row")
    return created_session


def update_session(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    status: SessionStatus | None = None,
    updated_at: datetime | None = None,
    cwd: Path | None = None,
    model_name: str | None = None,
    approval_mode: str | None = None,
    last_sequence: int | None = None,
    parent_session_id: SessionId | None = None,
    forked_from_turn_id: TurnId | None = None,
    forked_from_sequence: int | None = None,
    branch_label: str | None = None,
) -> SessionRecord:
    """Update coarse session metadata and return the stored row."""

    session = get_session(connection, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    if approval_mode is not None:
        try:
            approval_mode = ApprovalMode(approval_mode)
        except ValueError as exc:
            raise ValueError(f"invalid approval mode: {approval_mode}") from exc

    changes: dict[str, object] = {
        "status": status or session.status,
        "updated_at": (updated_at or datetime.now(UTC)).isoformat(),
        "cwd": str(cwd or session.cwd),
        "model_name": model_name or session.model_name,
        "approval_mode": approval_mode or session.approval_mode,
        "parent_session_id": _stringify_identifier(parent_session_id)
        if parent_session_id is not None
        else _stringify_identifier(session.parent_session_id),
        "forked_from_turn_id": _stringify_identifier(forked_from_turn_id)
        if forked_from_turn_id is not None
        else _stringify_identifier(session.forked_from_turn_id),
        "forked_from_sequence": (
            session.forked_from_sequence
            if forked_from_sequence is None
            else forked_from_sequence
        ),
        "branch_label": (
            branch_label if branch_label is not None else session.branch_label
        ),
        "last_sequence": (
            session.last_sequence if last_sequence is None else last_sequence
        ),
    }
    with connection:
        connection.execute(
            """
            update sessions
            set
                status = ?,
                updated_at = ?,
                cwd = ?,
                model_name = ?,
                approval_mode = ?,
                parent_session_id = ?,
                forked_from_turn_id = ?,
                forked_from_sequence = ?,
                branch_label = ?,
                last_sequence = ?
            where session_id = ?
            """,
            (
                changes["status"],
                changes["updated_at"],
                changes["cwd"],
                changes["model_name"],
                changes["approval_mode"],
                changes["parent_session_id"],
                changes["forked_from_turn_id"],
                changes["forked_from_sequence"],
                changes["branch_label"],
                changes["last_sequence"],
                str(session_id),
            ),
        )
    updated_session = get_session(connection, session_id)
    if updated_session is None:
        raise RuntimeError("update_session did not preserve the session row")
    return updated_session


def get_session(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> SessionRecord | None:
    """Fetch a persisted session metadata row by session identifier."""

    row = connection.execute(
        """
        select
            session_id,
            status,
            created_at,
            updated_at,
            cwd,
            model_name,
            approval_mode,
            parent_session_id,
            forked_from_turn_id,
            forked_from_sequence,
            branch_label,
            last_sequence
        from sessions
        where session_id = ?
        """,
        (str(session_id),),
    ).fetchone()
    if row is None:
        return None
    return _session_from_row(row)


def get_session_state(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> SessionState | None:
    """Fetch the projected runtime-facing state for a session."""

    row = connection.execute(
        """
        select
            session_id,
            status,
            current_turn_id,
            pending_approval_id,
            pending_question_id,
            last_sequence
        from session_state
        where session_id = ?
        """,
        (str(session_id),),
    ).fetchone()
    if row is None:
        session = get_session(connection, session_id)
        if session is None:
            return None
        return SessionState(
            session_id=session.session_id,
            status=session.status,
            last_sequence=session.last_sequence,
        )

    return SessionState.model_validate(
        {
            "session_id": row["session_id"],
            "status": row["status"],
            "current_turn_id": row["current_turn_id"],
            "pending_approval_id": row["pending_approval_id"],
            "pending_question_id": row["pending_question_id"],
            "last_sequence": row["last_sequence"],
        }
    )


def list_transcript_messages(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> list[TranscriptMessage]:
    """Read transcript messages for a session in conversation order."""

    rows = connection.execute(
        """
        select
            message_id,
            role,
            content_text,
            created_at
        from transcript_messages
        where session_id = ?
        order by created_at asc
        """,
        (str(session_id),),
    ).fetchall()
    return [
        TranscriptMessage(
            message_id=row["message_id"],
            role=row["role"],
            parts=[MessagePart(kind="text", text=row["content_text"])],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def list_sessions(
    connection: sqlite3.Connection,
    *,
    status: SessionStatus | None = None,
    limit: int | None = None,
) -> list[SessionRecord]:
    """List session metadata rows by recency, optionally filtered by status."""

    query = """
        select
            session_id,
            status,
            created_at,
            updated_at,
            cwd,
            model_name,
            approval_mode,
            parent_session_id,
            forked_from_turn_id,
            forked_from_sequence,
            branch_label,
            last_sequence
        from sessions
    """
    parameters: list[object] = []
    if status is not None:
        query += " where status = ?"
        parameters.append(status)
    query += " order by updated_at desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)

    rows = connection.execute(query, parameters).fetchall()
    return [_session_from_row(row) for row in rows]


def list_tool_calls(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    status: ToolExecutionStatus | None = None,
) -> list[ToolCallRecord]:
    """Read tool call records for a session, optionally filtered by status."""

    query = """
        select
            tool_call_id,
            turn_id,
            tool_name,
            status,
            started_at,
            completed_at,
            summary
        from tool_calls
        where session_id = ?
    """
    parameters: list[object] = [str(session_id)]
    if status is not None:
        query += " and status = ?"
        parameters.append(status)
    query += " order by started_at asc"

    rows = connection.execute(query, parameters).fetchall()
    return [
        ToolCallRecord(
            tool_call_id=row["tool_call_id"],
            turn_id=row["turn_id"],
            tool_name=row["tool_name"],
            status=ToolExecutionStatus(row["status"]),
            started_at=_parse_optional_datetime(row["started_at"]),
            completed_at=_parse_optional_datetime(row["completed_at"]),
            summary=row["summary"],
        )
        for row in rows
    ]


def list_approvals(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    status: ApprovalStatus | None = None,
) -> list[ApprovalRecord]:
    """Read approval records for a session, optionally filtered by status."""

    query = """
        select
            approval_id,
            turn_id,
            subject,
            reason,
            status,
            requested_at,
            resolved_at,
            decided_by
        from approvals
        where session_id = ?
    """
    parameters: list[object] = [str(session_id)]
    if status is not None:
        query += " and status = ?"
        parameters.append(status)
    query += " order by requested_at asc"

    rows = connection.execute(query, parameters).fetchall()
    return [
        ApprovalRecord(
            approval_id=row["approval_id"],
            turn_id=row["turn_id"],
            subject=row["subject"],
            reason=row["reason"],
            status=ApprovalStatus(row["status"]),
            requested_at=datetime.fromisoformat(row["requested_at"]),
            resolved_at=_parse_optional_datetime(row["resolved_at"]),
            decided_by=row["decided_by"],
        )
        for row in rows
    ]


def list_turn_metrics(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    limit: int | None = None,
) -> list[TurnMetricsRecord]:
    """Read aggregated per-turn runtime metrics for a session."""

    query = """
        select
            turn_id,
            started_at,
            completed_at,
            turn_duration_ms,
            model_call_count,
            model_duration_ms_total,
            model_input_tokens_total,
            model_output_tokens_total,
            tool_call_count,
            tool_duration_ms_total,
            succeeded_tool_call_count,
            failed_tool_call_count
        from turn_metrics
        where session_id = ?
        order by coalesce(started_at, completed_at) desc, turn_id desc
    """
    parameters: list[object] = [str(session_id)]
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)

    rows = connection.execute(query, parameters).fetchall()
    return [
        TurnMetricsRecord(
            turn_id=row["turn_id"],
            started_at=_parse_optional_datetime(row["started_at"]),
            completed_at=_parse_optional_datetime(row["completed_at"]),
            turn_duration_ms=row["turn_duration_ms"],
            model_call_count=row["model_call_count"],
            model_duration_ms_total=row["model_duration_ms_total"],
            model_input_tokens_total=row["model_input_tokens_total"],
            model_output_tokens_total=row["model_output_tokens_total"],
            tool_call_count=row["tool_call_count"],
            tool_duration_ms_total=row["tool_duration_ms_total"],
            succeeded_tool_call_count=row["succeeded_tool_call_count"],
            failed_tool_call_count=row["failed_tool_call_count"],
        )
        for row in rows
    ]


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


def _session_from_row(row: sqlite3.Row) -> SessionRecord:
    return SessionRecord.model_validate(
        {
            "session_id": row["session_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "cwd": row["cwd"],
            "model_name": row["model_name"],
            "approval_mode": row["approval_mode"],
            "parent_session_id": row["parent_session_id"],
            "forked_from_turn_id": row["forked_from_turn_id"],
            "forked_from_sequence": row["forked_from_sequence"],
            "branch_label": row["branch_label"],
            "last_sequence": row["last_sequence"],
        }
    )


def _ensure_sessions_lineage_schema(connection: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute("pragma table_info(sessions)").fetchall()
    }
    if "parent_session_id" not in existing_columns:
        connection.execute("alter table sessions add column parent_session_id text")
    if "forked_from_turn_id" not in existing_columns:
        connection.execute("alter table sessions add column forked_from_turn_id text")
    if "forked_from_sequence" not in existing_columns:
        connection.execute(
            "alter table sessions add column forked_from_sequence integer"
        )
    if "branch_label" not in existing_columns:
        connection.execute("alter table sessions add column branch_label text")
    connection.execute(
        """
        create index if not exists idx_sessions_parent_updated
            on sessions (parent_session_id, updated_at desc)
        """
    )


def _stringify_identifier(value: CorrelationValue | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _apply_projection_event(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    _apply_session_state_projection(connection, event)
    _apply_transcript_projection(connection, event)
    _apply_tool_call_projection(connection, event)
    _apply_approval_projection(connection, event)
    _apply_turn_metrics_projection(connection, event)


def _clear_session_projections(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> None:
    session_id_value = str(session_id)
    connection.execute(
        "delete from session_state where session_id = ?",
        (session_id_value,),
    )
    connection.execute(
        "delete from transcript_messages where session_id = ?",
        (session_id_value,),
    )
    connection.execute(
        "delete from tool_calls where session_id = ?",
        (session_id_value,),
    )
    connection.execute(
        "delete from approvals where session_id = ?",
        (session_id_value,),
    )
    connection.execute(
        "delete from turn_metrics where session_id = ?",
        (session_id_value,),
    )


def _apply_session_state_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    existing_row = connection.execute(
        """
        select status, current_turn_id, pending_approval_id, pending_question_id
        from session_state
        where session_id = ?
        """,
        (str(event.session_id),),
    ).fetchone()
    current_turn_id = (
        existing_row["current_turn_id"] if existing_row is not None else None
    )
    pending_approval_id = (
        existing_row["pending_approval_id"] if existing_row is not None else None
    )
    pending_question_id = (
        existing_row["pending_question_id"] if existing_row is not None else None
    )
    status = (
        existing_row["status"] if existing_row is not None else SessionStatus.RUNNING
    )

    payload = event.payload
    if isinstance(payload, SessionStarted):
        status = SessionStatus.RUNNING
    elif isinstance(payload, TurnStarted):
        current_turn_id = str(payload.turn_id)
        status = SessionStatus.RUNNING
    elif isinstance(payload, TurnCompleted):
        current_turn_id = None
        # Only reset to RUNNING on a normal completion; suspension outcomes leave
        # the status managed by the pausing event
        # (ApprovalRequested / UserQuestionAsked).
        if payload.outcome == "completed":
            status = SessionStatus.RUNNING
    elif isinstance(payload, TurnFailed):
        current_turn_id = None
        status = SessionStatus.RUNNING
    elif isinstance(payload, ApprovalRequested):
        pending_approval_id = str(payload.approval_id)
        status = SessionStatus.AWAITING_APPROVAL
    elif isinstance(payload, ApprovalResolved):
        pending_approval_id = None
        status = SessionStatus.RUNNING
    elif isinstance(payload, UserQuestionAsked):
        pending_question_id = str(payload.question_id)
        status = SessionStatus.AWAITING_USER_INPUT
    elif isinstance(payload, UserAnswerProvided):
        pending_question_id = None
        status = SessionStatus.RUNNING
    elif isinstance(payload, SessionCompleted):
        current_turn_id = None
        pending_approval_id = None
        pending_question_id = None
        status = SessionStatus.COMPLETED
    elif isinstance(payload, SessionFailed):
        current_turn_id = None
        pending_approval_id = None
        pending_question_id = None
        status = SessionStatus.FAILED

    connection.execute(
        """
        insert into session_state (
            session_id,
            status,
            current_turn_id,
            pending_approval_id,
            pending_question_id,
            last_sequence,
            updated_at
        ) values (?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id) do update set
            status = excluded.status,
            current_turn_id = excluded.current_turn_id,
            pending_approval_id = excluded.pending_approval_id,
            pending_question_id = excluded.pending_question_id,
            last_sequence = excluded.last_sequence,
            updated_at = excluded.updated_at
        """,
        (
            str(event.session_id),
            status,
            current_turn_id,
            pending_approval_id,
            pending_question_id,
            event.sequence,
            event.created_at.isoformat(),
        ),
    )


def _apply_transcript_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, SessionStarted | TurnStarted | TurnCompleted | TurnFailed):
        return

    if isinstance(payload, UserMessageReceived):
        connection.execute(
            """
            insert into transcript_messages (
                message_id,
                session_id,
                turn_id,
                role,
                status,
                created_at,
                completed_at,
                content_text
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(message_id) do update set
                turn_id = excluded.turn_id,
                role = excluded.role,
                status = excluded.status,
                created_at = excluded.created_at,
                completed_at = excluded.completed_at,
                content_text = excluded.content_text
            """,
            (
                str(payload.message_id),
                str(event.session_id),
                _stringify_identifier(event.turn_id),
                "user",
                "completed",
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                payload.text,
            ),
        )
        return

    if isinstance(payload, AssistantMessageStarted):
        connection.execute(
            """
            insert into transcript_messages (
                message_id,
                session_id,
                turn_id,
                role,
                status,
                created_at,
                completed_at,
                content_text
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(message_id) do update set
                turn_id = excluded.turn_id,
                role = excluded.role,
                status = excluded.status,
                created_at = excluded.created_at,
                content_text = excluded.content_text
            """,
            (
                str(payload.message_id),
                str(event.session_id),
                _stringify_identifier(event.turn_id),
                "assistant",
                "streaming",
                event.created_at.isoformat(),
                None,
                "",
            ),
        )
        return

    if isinstance(payload, AssistantMessageDelta):
        connection.execute(
            """
            insert into transcript_messages (
                message_id,
                session_id,
                turn_id,
                role,
                status,
                created_at,
                completed_at,
                content_text
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(message_id) do update set
                turn_id = coalesce(excluded.turn_id, transcript_messages.turn_id),
                role = excluded.role,
                status = excluded.status,
                content_text = transcript_messages.content_text || excluded.content_text
            """,
            (
                str(payload.message_id),
                str(event.session_id),
                _stringify_identifier(event.turn_id),
                "assistant",
                "streaming",
                event.created_at.isoformat(),
                None,
                payload.delta,
            ),
        )
        return

    if isinstance(payload, AssistantMessageCompleted):
        content_text = "".join(part.text for part in payload.parts)
        connection.execute(
            """
            insert into transcript_messages (
                message_id,
                session_id,
                turn_id,
                role,
                status,
                created_at,
                completed_at,
                content_text
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(message_id) do update set
                turn_id = coalesce(excluded.turn_id, transcript_messages.turn_id),
                role = excluded.role,
                status = excluded.status,
                completed_at = excluded.completed_at,
                content_text = excluded.content_text
            """,
            (
                str(payload.message_id),
                str(event.session_id),
                _stringify_identifier(event.turn_id),
                "assistant",
                "completed",
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                content_text,
            ),
        )


def _apply_tool_call_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, ModelToolCallRequested):
        connection.execute(
            """
            insert into tool_calls (
                tool_call_id,
                session_id,
                turn_id,
                tool_name,
                status,
                started_at,
                completed_at,
                summary,
                exit_code
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(tool_call_id) do update set
                turn_id = excluded.turn_id,
                tool_name = excluded.tool_name,
                status = excluded.status
            """,
            (
                str(payload.tool_call_id),
                str(event.session_id),
                str(payload.turn_id),
                payload.tool_name,
                "requested",
                None,
                None,
                None,
                None,
            ),
        )
        return

    if isinstance(payload, ToolExecutionStarted):
        connection.execute(
            """
            insert into tool_calls (
                tool_call_id,
                session_id,
                turn_id,
                tool_name,
                status,
                started_at,
                completed_at,
                summary,
                exit_code
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(tool_call_id) do update set
                turn_id = excluded.turn_id,
                tool_name = excluded.tool_name,
                status = excluded.status,
                started_at = excluded.started_at
            """,
            (
                str(payload.tool_call_id),
                str(event.session_id),
                str(payload.turn_id),
                payload.tool_name,
                "running",
                event.created_at.isoformat(),
                None,
                None,
                None,
            ),
        )
        return

    if isinstance(payload, ToolExecutionCompleted):
        connection.execute(
            """
            update tool_calls
            set
                status = ?,
                completed_at = ?,
                summary = ?,
                exit_code = ?
            where tool_call_id = ?
            """,
            (
                "succeeded" if payload.success else "failed",
                event.created_at.isoformat(),
                payload.summary,
                payload.exit_code,
                str(payload.tool_call_id),
            ),
        )


def _apply_approval_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, ApprovalRequested):
        connection.execute(
            """
            insert into approvals (
                approval_id,
                session_id,
                turn_id,
                subject,
                reason,
                status,
                requested_at,
                resolved_at,
                decided_by
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(approval_id) do update set
                turn_id = excluded.turn_id,
                subject = excluded.subject,
                reason = excluded.reason,
                status = excluded.status,
                requested_at = excluded.requested_at
            """,
            (
                str(payload.approval_id),
                str(event.session_id),
                str(payload.turn_id),
                payload.subject,
                payload.reason,
                "pending",
                event.created_at.isoformat(),
                None,
                None,
            ),
        )
        return

    if isinstance(payload, ApprovalResolved):
        connection.execute(
            """
            update approvals
            set
                status = ?,
                resolved_at = ?,
                decided_by = ?
            where approval_id = ?
            """,
            (
                payload.decision,
                event.created_at.isoformat(),
                payload.decided_by,
                str(payload.approval_id),
            ),
        )


def _ensure_turn_metrics_row(
    connection: sqlite3.Connection,
    session_id: SessionId,
    turn_id: TurnId,
    *,
    started_at: datetime | None = None,
) -> None:
    connection.execute(
        """
        insert into turn_metrics (
            session_id,
            turn_id,
            started_at,
            completed_at,
            turn_duration_ms,
            model_call_count,
            model_duration_ms_total,
            model_input_tokens_total,
            model_output_tokens_total,
            tool_call_count,
            tool_duration_ms_total,
            succeeded_tool_call_count,
            failed_tool_call_count
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id, turn_id) do update set
            started_at = coalesce(turn_metrics.started_at, excluded.started_at)
        """,
        (
            str(session_id),
            str(turn_id),
            started_at.isoformat() if started_at is not None else None,
            None,
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
    )


def _apply_turn_metrics_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    turn_id = event.turn_id
    if turn_id is None:
        return

    payload = event.payload

    if isinstance(payload, TurnStarted):
        _ensure_turn_metrics_row(
            connection,
            event.session_id,
            turn_id,
            started_at=event.created_at,
        )
        return

    _ensure_turn_metrics_row(connection, event.session_id, turn_id)

    if isinstance(payload, ModelCallStarted):
        return

    if isinstance(payload, ModelCallCompleted):
        connection.execute(
            """
            update turn_metrics
            set
                model_call_count = model_call_count + 1,
                model_duration_ms_total = model_duration_ms_total + ?,
                model_input_tokens_total = model_input_tokens_total + ?,
                model_output_tokens_total = model_output_tokens_total + ?
            where session_id = ? and turn_id = ?
            """,
            (
                payload.duration_ms,
                payload.input_tokens or 0,
                payload.output_tokens or 0,
                str(event.session_id),
                str(turn_id),
            ),
        )
        return

    if isinstance(payload, ToolExecutionStarted):
        connection.execute(
            """
            update turn_metrics
            set tool_call_count = tool_call_count + 1
            where session_id = ? and turn_id = ?
            """,
            (str(event.session_id), str(turn_id)),
        )
        return

    if isinstance(payload, ToolExecutionCompleted):
        started_at_row = connection.execute(
            """
            select started_at from tool_calls
            where session_id = ? and tool_call_id = ?
            """,
            (str(event.session_id), str(payload.tool_call_id)),
        ).fetchone()
        tool_duration_ms = 0
        if started_at_row is not None and started_at_row["started_at"] is not None:
            started_at = datetime.fromisoformat(started_at_row["started_at"])
            tool_duration_ms = max(
                int((event.created_at - started_at).total_seconds() * 1000),
                0,
            )

        connection.execute(
            """
            update turn_metrics
            set
                tool_duration_ms_total = tool_duration_ms_total + ?,
                succeeded_tool_call_count = succeeded_tool_call_count + ?,
                failed_tool_call_count = failed_tool_call_count + ?
            where session_id = ? and turn_id = ?
            """,
            (
                tool_duration_ms,
                1 if payload.success else 0,
                0 if payload.success else 1,
                str(event.session_id),
                str(turn_id),
            ),
        )
        return

    if isinstance(payload, TurnCompleted | TurnFailed):
        started_at_row = connection.execute(
            """
            select started_at from turn_metrics
            where session_id = ? and turn_id = ?
            """,
            (str(event.session_id), str(turn_id)),
        ).fetchone()
        turn_duration_ms = None
        if started_at_row is not None and started_at_row["started_at"] is not None:
            started_at = datetime.fromisoformat(started_at_row["started_at"])
            turn_duration_ms = max(
                int((event.created_at - started_at).total_seconds() * 1000),
                0,
            )

        connection.execute(
            """
            update turn_metrics
            set completed_at = ?, turn_duration_ms = ?
            where session_id = ? and turn_id = ?
            """,
            (
                event.created_at.isoformat(),
                turn_duration_ms,
                str(event.session_id),
                str(turn_id),
            ),
        )
