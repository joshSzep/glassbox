"""Integration tests for the SQLite bootstrap layer."""

import sqlite3
from pathlib import Path

from glassbox.core import SessionStatus
from glassbox.core import new_session_id
from glassbox.store.sqlite import MIGRATIONS
from glassbox.store.sqlite import SCHEMA_VERSION
from glassbox.store.sqlite import get_session
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "select name from sqlite_master where type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def _index_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "select name from sqlite_master where type = 'index'"
    ).fetchall()
    return {row[0] for row in rows}


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"pragma table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _primary_key_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"pragma table_info({table_name})").fetchall()
    return [row[1] for row in sorted(rows, key=lambda row: row[5]) if row[5]]


def _migration_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        "select version, name from schema_migrations order by version"
    ).fetchall()


def _expected_migration_versions() -> list[int]:
    return [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, SCHEMA_VERSION]


def _expected_migration_names() -> list[str]:
    return [
        "baseline event store and projections",
        "add session lineage columns",
        "add runtime note source columns",
        "add policy metadata projection columns",
        "add task plan projection tables",
        "add autonomy budget projection table",
        "add background job projection table",
        "add background job retry triage columns",
        "add workspace memory projection table",
        "add branch search projection tables",
        "add long-run event correlations and projection",
        "add task checkpoint projection table",
        "scope task checkpoint projection key by session",
        "add context compaction projection table",
        "add tool attempt projection table",
        "add task verification ledger projection table",
    ]


def test_open_database_configures_sqlite_connection(tmp_path: Path) -> None:
    database_path = tmp_path / "glassbox.sqlite3"

    connection = open_database(database_path)
    try:
        foreign_keys_enabled = connection.execute("pragma foreign_keys").fetchone()[0]
        journal_mode = connection.execute("pragma journal_mode").fetchone()[0]
    finally:
        connection.close()

    assert database_path.exists()
    assert foreign_keys_enabled == 1
    assert journal_mode == "wal"


def test_initialize_database_creates_bootstrap_schema(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        initialize_database(connection)
        tables = _table_names(connection)
        indexes = _index_names(connection)
        migration_rows = _migration_rows(connection)
    finally:
        connection.close()

    assert {
        "schema_migrations",
        "sessions",
        "events",
        "session_state",
        "transcript_messages",
        "tool_calls",
        "approvals",
        "tasks",
        "task_steps",
        "task_verifications",
        "task_verification_ledger",
        "branch_searches",
        "branch_candidates",
        "background_jobs",
        "workspace_memory",
        "long_run_events",
        "task_checkpoints",
        "context_compactions",
        "tool_attempts",
    }.issubset(tables)
    assert {
        "idx_sessions_status_updated",
        "idx_sessions_parent_updated",
        "idx_events_session_created",
        "idx_events_session_type_sequence",
        "idx_events_turn",
        "idx_events_message",
        "idx_events_tool_call",
        "idx_events_approval",
        "idx_events_task",
        "idx_events_checkpoint",
        "idx_events_compaction",
        "idx_events_tool_attempt",
        "idx_events_recovery_decision",
        "idx_transcript_messages_session_created",
        "idx_tool_calls_session_status",
        "idx_tool_calls_session_turn",
        "idx_approvals_session_status",
        "idx_tasks_session_status_updated",
        "idx_tasks_session_blocked",
        "idx_task_steps_task_order",
        "idx_task_steps_session_status",
        "idx_task_verifications_task",
        "idx_task_verification_ledger_task",
        "idx_task_verification_ledger_status",
        "idx_branch_searches_session_updated",
        "idx_branch_candidates_search",
        "idx_autonomy_budget_posture_session_updated",
        "idx_background_jobs_state_updated",
        "idx_background_jobs_session_updated",
        "idx_background_jobs_lease",
        "idx_workspace_memory_state_updated",
        "idx_workspace_memory_kind_updated",
        "idx_workspace_memory_session_sequence",
        "idx_long_run_events_session_created",
        "idx_long_run_events_task",
        "idx_long_run_events_checkpoint",
        "idx_task_checkpoints_session_sequence",
        "idx_task_checkpoints_task_sequence",
        "idx_context_compactions_session_sequence",
        "idx_context_compactions_task_sequence",
        "idx_context_compactions_checkpoint",
        "idx_tool_attempts_session_status",
        "idx_tool_attempts_turn",
        "idx_tool_attempts_tool_call",
    }.issubset(indexes)
    assert [row[0] for row in migration_rows] == _expected_migration_versions()
    assert [row[1] for row in migration_rows] == _expected_migration_names()


def test_initialize_database_is_idempotent(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        initialize_database(connection)
        initialize_database(connection)
        migration_rows = _migration_rows(connection)
    finally:
        connection.close()

    assert [row[0] for row in migration_rows] == _expected_migration_versions()


def test_initialize_database_migrates_existing_sessions_table_for_lineage(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        with connection:
            connection.execute(
                """
                create table schema_migrations (
                    version integer primary key,
                    applied_at text not null default current_timestamp
                )
                """
            )
            connection.execute("insert into schema_migrations(version) values (3)")
            connection.execute(
                """
                create table sessions (
                    session_id text primary key,
                    status text not null,
                    created_at text not null,
                    updated_at text not null,
                    cwd text not null,
                    model_name text not null,
                    approval_mode text not null,
                    last_sequence integer not null default 0
                )
                """
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
                    str(session_id),
                    SessionStatus.RUNNING,
                    "2026-04-16T12:00:00+00:00",
                    "2026-04-16T12:05:00+00:00",
                    "/tmp/glassbox",
                    "openai:gpt-5.4",
                    "confirm",
                    4,
                ),
            )

        initialize_database(connection)
        session = get_session(connection, session_id)
        columns = _column_names(connection, "sessions")
        migration_rows = _migration_rows(connection)
    finally:
        connection.close()

    assert {
        "parent_session_id",
        "forked_from_turn_id",
        "forked_from_sequence",
        "branch_label",
    }.issubset(columns)
    assert session is not None
    assert session.parent_session_id is None
    assert session.forked_from_turn_id is None
    assert session.forked_from_sequence is None
    assert session.branch_label is None
    assert [row[0] for row in migration_rows] == _expected_migration_versions()


def test_initialize_database_migrates_runtime_note_source_columns(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        with connection:
            connection.execute(
                """
                create table schema_migrations (
                    version integer primary key,
                    name text not null default '',
                    applied_at text not null default current_timestamp
                )
                """
            )
            connection.execute(
                "insert into schema_migrations(version, name) values (3, 'baseline')"
            )
            connection.execute(
                """
                insert into schema_migrations(version, name)
                values (4, 'add session lineage columns')
                """
            )
            connection.execute(
                """
                create table sessions (
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
                """
            )
            connection.execute(
                """
                create table runtime_notes (
                    session_id text not null,
                    sequence integer not null,
                    category text not null,
                    message text not null,
                    created_at text not null,
                    primary key (session_id, sequence),
                    foreign key (session_id) references sessions(session_id)
                )
                """
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
                    str(session_id),
                    SessionStatus.RUNNING,
                    "2026-04-16T12:00:00+00:00",
                    "2026-04-16T12:05:00+00:00",
                    "/tmp/glassbox",
                    "openai:gpt-5.4",
                    "confirm",
                    4,
                ),
            )
            connection.execute(
                """
                insert into runtime_notes (
                    session_id,
                    sequence,
                    category,
                    message,
                    created_at
                ) values (?, ?, ?, ?, ?)
                """,
                (
                    str(session_id),
                    2,
                    "summary",
                    "Existing note",
                    "2026-04-16T12:06:00+00:00",
                ),
            )

        initialize_database(connection)
        columns = _column_names(connection, "runtime_notes")
        note_row = connection.execute(
            """
            select source_session_id, source_sequence
            from runtime_notes
            where session_id = ? and sequence = 2
            """,
            (str(session_id),),
        ).fetchone()
        migration_rows = _migration_rows(connection)
    finally:
        connection.close()

    assert {"source_session_id", "source_sequence"}.issubset(columns)
    assert note_row[0] == str(session_id)
    assert note_row[1] == 2
    assert [row[0] for row in migration_rows] == _expected_migration_versions()


def test_initialize_database_normalizes_legacy_current_version_stamp(
    tmp_path: Path,
) -> None:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        with connection:
            connection.execute(
                """
                create table schema_migrations (
                    version integer primary key,
                    applied_at text not null default current_timestamp
                )
                """
            )
            connection.execute(
                "insert into schema_migrations(version) values (?)",
                (SCHEMA_VERSION,),
            )

        initialize_database(connection)
        migration_rows = _migration_rows(connection)
        session_columns = _column_names(connection, "sessions")
        note_columns = _column_names(connection, "runtime_notes")
        event_columns = _column_names(connection, "events")
    finally:
        connection.close()

    assert [row[0] for row in migration_rows] == _expected_migration_versions()
    assert [row[1] for row in migration_rows] == _expected_migration_names()
    assert "parent_session_id" in session_columns
    assert "source_session_id" in note_columns
    assert "checkpoint_id" in event_columns


def test_initialize_database_migrates_checkpoint_projection_key(
    tmp_path: Path,
) -> None:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        with connection:
            connection.execute(
                """
                create table task_checkpoints (
                    checkpoint_id text primary key,
                    session_id text not null,
                    task_id text,
                    turn_id text,
                    tool_attempt_id text,
                    compaction_id text,
                    artifact_id text,
                    objective text not null,
                    current_phase text,
                    completed_step text,
                    next_action text not null,
                    blockers_json text not null,
                    touched_files_json text not null,
                    verification_status text,
                    budget_status text,
                    recovery_guidance text not null,
                    source_start_sequence integer not null,
                    source_end_sequence integer not null,
                    created_at text not null,
                    last_sequence integer not null
                )
                """
            )

        initialize_database(connection)
        primary_key_columns = _primary_key_columns(connection, "task_checkpoints")
        indexes = _index_names(connection)
        migration_rows = _migration_rows(connection)
    finally:
        connection.close()

    assert primary_key_columns == ["session_id", "checkpoint_id"]
    assert "idx_task_checkpoints_session_sequence" in indexes
    assert "idx_task_checkpoints_task_sequence" in indexes
    assert [row[0] for row in migration_rows] == _expected_migration_versions()


def test_initialize_database_rejects_newer_schema_version(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        with connection:
            connection.execute(
                """
                create table schema_migrations (
                    version integer primary key,
                    name text not null default '',
                    applied_at text not null default current_timestamp
                )
                """
            )
            connection.execute(
                "insert into schema_migrations(version, name) values (?, ?)",
                (SCHEMA_VERSION + 1, "future migration"),
            )

        try:
            initialize_database(connection)
        except ValueError as exc:
            message = str(exc)
        else:
            raise AssertionError("newer schema version was accepted")
    finally:
        connection.close()

    assert f"database schema version {SCHEMA_VERSION + 1} is newer" in message


def test_migrations_are_ordered_to_current_schema_version() -> None:
    assert [migration.version for migration in MIGRATIONS] == [
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        SCHEMA_VERSION,
    ]
