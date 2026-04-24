"""Schema bootstrap and connection lifecycle for the SQLite store."""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 5

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
    create table if not exists runtime_notes (
        session_id text not null,
        sequence integer not null,
        source_session_id text,
        source_sequence integer,
        category text not null,
        message text not null,
        created_at text not null,
        primary key (session_id, sequence),
        foreign key (session_id) references sessions(session_id)
    )
    """,
    """
    create index if not exists idx_runtime_notes_session_created
        on runtime_notes (session_id, created_at, sequence)
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
        _ensure_runtime_notes_schema(connection)

        connection.execute(
            "insert or ignore into schema_migrations(version) values (?)",
            (SCHEMA_VERSION,),
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


def _ensure_runtime_notes_schema(connection: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute("pragma table_info(runtime_notes)").fetchall()
    }
    if "source_session_id" not in existing_columns:
        connection.execute(
            "alter table runtime_notes add column source_session_id text"
        )
    if "source_sequence" not in existing_columns:
        connection.execute(
            "alter table runtime_notes add column source_sequence integer"
        )
    connection.execute(
        """
        update runtime_notes
        set source_session_id = coalesce(source_session_id, session_id),
            source_sequence = coalesce(source_sequence, sequence)
        where source_session_id is null or source_sequence is null
        """
    )


__all__ = [
    "BOOTSTRAP_STATEMENTS",
    "SCHEMA_VERSION",
    "initialize_database",
    "open_database",
]
