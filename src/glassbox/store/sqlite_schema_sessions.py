"""Session and runtime-note SQLite schema migrations."""

import sqlite3

from glassbox.store.sqlite_schema_helpers import column_names


def ensure_sessions_lineage_schema(connection: sqlite3.Connection) -> None:
    existing_columns = column_names(connection, "sessions")
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


def ensure_runtime_notes_schema(connection: sqlite3.Connection) -> None:
    existing_columns = column_names(connection, "runtime_notes")
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
