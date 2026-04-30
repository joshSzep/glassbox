"""Workspace-memory SQLite schema migrations."""

import sqlite3


def ensure_workspace_memory_projection_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        create table if not exists workspace_memory (
            memory_id text primary key,
            session_id text not null,
            kind text not null,
            state text not null,
            content text not null,
            summary text,
            provenance_json text not null,
            created_by text not null,
            created_at text not null,
            updated_at text not null,
            confirmed_by text,
            confirmed_at text,
            invalidated_by text,
            invalidated_at text,
            invalidation_reason text,
            last_used_at text,
            use_count integer not null default 0,
            tags_json text not null,
            redacted integer not null default 0,
            import_source text,
            pruned_by text,
            pruned_at text,
            prune_reason text,
            last_sequence integer not null,
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_workspace_memory_state_updated
            on workspace_memory (state, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_workspace_memory_kind_updated
            on workspace_memory (kind, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_workspace_memory_session_sequence
            on workspace_memory (session_id, last_sequence)
        """
    )
