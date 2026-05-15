"""Handoff workflow SQLite projection schema."""

import sqlite3


def ensure_handoff_projection_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists handoffs (
            session_id text not null,
            package_id text not null,
            source_kind text not null,
            source_id text,
            task_id text,
            changeset_id text,
            package_kind text,
            intent text,
            artifact_id text,
            package_digest text,
            compatibility_state text,
            redaction_posture text,
            local_only_count integer not null default 0,
            custody_state text not null,
            expected_custodian text,
            current_custodian text,
            exported_by text,
            decision_by text,
            decision_reason text,
            follow_up_intent text,
            safe_next_actions_json text not null default '[]',
            note text,
            imported integer not null default 0,
            archived integer not null default 0,
            created_at text not null,
            updated_at text not null,
            last_event_type text not null,
            last_sequence integer not null,
            primary key (session_id, package_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_handoffs_source
            on handoffs (session_id, source_kind, source_id, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_handoffs_task
            on handoffs (session_id, task_id, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_handoffs_changeset
            on handoffs (session_id, changeset_id, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_handoffs_custody
            on handoffs (session_id, custody_state, updated_at desc)
        """
    )


__all__ = ["ensure_handoff_projection_schema"]
