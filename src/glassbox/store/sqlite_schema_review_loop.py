"""Review-loop SQLite schema migrations."""

import sqlite3


def ensure_review_loop_projection_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists review_feedback (
            session_id text not null,
            feedback_id text not null,
            changeset_id text not null,
            feedback_kind text not null,
            provenance text not null,
            disposition text not null,
            summary text not null,
            body text,
            source_label text,
            reviewer_label text,
            created_by text not null,
            updated_by text,
            resolved_by text,
            archived_by text,
            accepted_by text,
            source_session_id text,
            task_id text,
            turn_id text,
            artifact_id text,
            verification_id text,
            resolution_summary text,
            residual_risk text,
            risk_summary text,
            acceptance_reason text,
            archived_reason text,
            replacement_feedback_id text,
            reopened_count integer not null default 0,
            created_at text not null,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, feedback_id),
            foreign key (session_id, changeset_id)
                references changesets(session_id, changeset_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_review_feedback_changeset_disposition
            on review_feedback (session_id, changeset_id, disposition, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_review_feedback_task
            on review_feedback (session_id, task_id, updated_at desc)
        """
    )
    connection.execute(
        """
        create table if not exists review_feedback_scopes (
            session_id text not null,
            feedback_id text not null,
            changeset_id text not null,
            scope_kind text not null,
            reason text not null,
            source_session_id text,
            task_id text,
            turn_id text,
            artifact_id text,
            verification_id text,
            branch_search_id text,
            branch_candidate_id text,
            file_path text,
            line_start integer,
            line_end integer,
            created_at text not null,
            last_sequence integer not null,
            primary key (session_id, feedback_id, last_sequence),
            foreign key (session_id, feedback_id)
                references review_feedback(session_id, feedback_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_review_feedback_scopes_changeset
            on review_feedback_scopes (session_id, changeset_id, last_sequence)
        """
    )
    connection.execute(
        """
        create index if not exists idx_review_feedback_scopes_file
            on review_feedback_scopes (session_id, file_path, last_sequence)
        """
    )


__all__ = ["ensure_review_loop_projection_schema"]
