"""Context-compaction SQLite schema migrations."""

import sqlite3

from glassbox.store.sqlite_schema_helpers import column_names


def ensure_context_compaction_projection_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        create table if not exists context_compactions (
            compaction_id text not null,
            session_id text not null,
            scope text not null,
            task_id text,
            turn_id text,
            checkpoint_id text,
            artifact_id text not null,
            artifact_schema_version integer not null,
            source_start_sequence integer not null,
            source_end_sequence integer not null,
            summary text not null,
            freshness text not null,
            freshness_reason text,
            superseded_by_compaction_id text,
            limitations_json text not null,
            source_artifact_ids_json text not null,
            decision_count integer not null,
            unresolved_question_count integer not null,
            accepted_risk_count integer not null,
            created_at text not null,
            last_sequence integer not null,
            primary key (session_id, compaction_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_context_compactions_session_sequence
            on context_compactions (session_id, last_sequence desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_context_compactions_task_sequence
            on context_compactions (session_id, task_id, last_sequence desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_context_compactions_checkpoint
            on context_compactions (session_id, checkpoint_id, last_sequence desc)
        """
    )
    existing_columns = column_names(connection, "context_compactions")
    if "freshness_reason" not in existing_columns:
        connection.execute(
            "alter table context_compactions add column freshness_reason text"
        )
    if "superseded_by_compaction_id" not in existing_columns:
        connection.execute(
            "alter table context_compactions add column "
            "superseded_by_compaction_id text"
        )
