"""Integration tests for the SQLite bootstrap layer."""

import sqlite3
from pathlib import Path

from glassbox.core import SessionStatus
from glassbox.core import new_session_id
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
        migration_versions = connection.execute(
            "select version from schema_migrations"
        ).fetchall()
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
        "idx_transcript_messages_session_created",
        "idx_tool_calls_session_status",
        "idx_tool_calls_session_turn",
        "idx_approvals_session_status",
    }.issubset(indexes)
    assert [row[0] for row in migration_versions] == [SCHEMA_VERSION]


def test_initialize_database_is_idempotent(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        initialize_database(connection)
        initialize_database(connection)
        migration_count = connection.execute(
            "select count(*) from schema_migrations where version = ?",
            (SCHEMA_VERSION,),
        ).fetchone()[0]
    finally:
        connection.close()

    assert migration_count == 1


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
        migration_versions = connection.execute(
            "select version from schema_migrations order by version"
        ).fetchall()
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
    assert [row[0] for row in migration_versions] == [3, SCHEMA_VERSION]
