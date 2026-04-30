"""Provider-recovery SQLite schema migrations."""

import sqlite3


def ensure_provider_recovery_projection_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        create table if not exists provider_recovery (
            session_id text not null,
            sequence integer not null,
            turn_id text,
            task_id text,
            checkpoint_id text,
            provider text not null,
            model_name text not null,
            failure_kind text not null,
            action text not null,
            retryable integer not null,
            safe_to_continue integer not null,
            degraded integer not null default 0,
            attempt integer not null,
            max_attempts integer,
            backoff_seconds integer,
            next_retry_at text,
            reason text not null,
            operator_next_action text not null,
            created_at text not null,
            primary key (session_id, sequence),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_provider_recovery_session_sequence
            on provider_recovery (session_id, sequence desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_provider_recovery_session_action
            on provider_recovery (session_id, action, sequence desc)
        """
    )
