"""Long-running task correlation SQLite schema migrations."""

import sqlite3

from glassbox.store.sqlite_schema_helpers import column_names


def ensure_long_run_event_schema(connection: sqlite3.Connection) -> None:
    event_columns = column_names(connection, "events")
    event_correlation_columns = {
        "task_id": "text",
        "checkpoint_id": "text",
        "compaction_id": "text",
        "tool_attempt_id": "text",
        "recovery_decision_id": "text",
    }
    for column_name, column_type in event_correlation_columns.items():
        if column_name not in event_columns:
            connection.execute(
                f"alter table events add column {column_name} {column_type}"
            )

    connection.execute(
        """
        create index if not exists idx_events_task
            on events (session_id, task_id, sequence)
        """
    )
    connection.execute(
        """
        create index if not exists idx_events_checkpoint
            on events (session_id, checkpoint_id, sequence)
        """
    )
    connection.execute(
        """
        create index if not exists idx_events_compaction
            on events (session_id, compaction_id, sequence)
        """
    )
    connection.execute(
        """
        create index if not exists idx_events_tool_attempt
            on events (session_id, tool_attempt_id, sequence)
        """
    )
    connection.execute(
        """
        create index if not exists idx_events_recovery_decision
            on events (session_id, recovery_decision_id, sequence)
        """
    )
    connection.execute(
        """
        create table if not exists long_run_events (
            session_id text not null,
            sequence integer not null,
            event_type text not null,
            task_id text,
            turn_id text,
            tool_call_id text,
            tool_attempt_id text,
            checkpoint_id text,
            compaction_id text,
            recovery_decision_id text,
            phase text,
            status text,
            summary text,
            created_at text not null,
            primary key (session_id, sequence),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_long_run_events_session_created
            on long_run_events (session_id, created_at, sequence)
        """
    )
    connection.execute(
        """
        create index if not exists idx_long_run_events_task
            on long_run_events (session_id, task_id, sequence)
        """
    )
    connection.execute(
        """
        create index if not exists idx_long_run_events_checkpoint
            on long_run_events (session_id, checkpoint_id, sequence)
        """
    )
