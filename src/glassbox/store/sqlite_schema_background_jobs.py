"""Background-job SQLite schema migrations."""

import sqlite3

from glassbox.store.sqlite_schema_helpers import column_names


def ensure_background_job_projection_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        create table if not exists background_jobs (
            job_id text primary key,
            session_id text not null,
            state text not null,
            kind text not null,
            job_type text not null,
            title text not null,
            requested_by text not null,
            payload_json text not null,
            priority integer not null,
            task_id text,
            parent_job_id text,
            worker_id text,
            claim_token text,
            attempt integer not null default 0,
            lease_expires_at text,
            last_heartbeat_at text,
            progress_message text,
            completed_units integer,
            total_units integer,
            failure_kind text,
            failure_message text,
            retryable integer not null default 0,
            next_retry_at text,
            cancellation_requested_by text,
            cancellation_reason text,
            cancelled_by text,
            recovery_reason text,
            recovery_detail text,
            created_at text not null,
            updated_at text not null,
            started_at text,
            completed_at text,
            last_sequence integer not null,
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_background_jobs_state_updated
            on background_jobs (state, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_background_jobs_session_updated
            on background_jobs (session_id, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_background_jobs_lease
            on background_jobs (state, lease_expires_at)
        """
    )


def ensure_background_job_retry_schema(connection: sqlite3.Connection) -> None:
    existing_columns = column_names(connection, "background_jobs")
    columns = {
        "failure_artifact_id": "text",
        "failure_artifact_path": "text",
        "retry_requested_by": "text",
        "retry_reason": "text",
        "retry_exhausted_reason": "text",
        "retry_budget": "integer",
        "abandoned_by": "text",
        "abandoned_reason": "text",
    }
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            connection.execute(
                f"alter table background_jobs add column {column_name} {column_type}"
            )
