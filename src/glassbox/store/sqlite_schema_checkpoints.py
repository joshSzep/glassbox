"""Task-checkpoint SQLite schema migrations."""

import sqlite3


def ensure_task_checkpoint_projection_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        create table if not exists task_checkpoints (
            checkpoint_id text not null,
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
            last_sequence integer not null,
            primary key (session_id, checkpoint_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_task_checkpoints_session_sequence
            on task_checkpoints (session_id, last_sequence desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_task_checkpoints_task_sequence
            on task_checkpoints (session_id, task_id, last_sequence desc)
        """
    )


def ensure_task_checkpoint_session_scoped_key(
    connection: sqlite3.Connection,
) -> None:
    table_info = connection.execute("pragma table_info(task_checkpoints)").fetchall()
    primary_key_columns = [
        row["name"]
        for row in sorted(table_info, key=lambda row: row["pk"])
        if row["pk"]
    ]
    if primary_key_columns == ["session_id", "checkpoint_id"]:
        return

    connection.execute("alter table task_checkpoints rename to task_checkpoints_old")
    ensure_task_checkpoint_projection_schema(connection)
    connection.execute(
        """
        insert or replace into task_checkpoints (
            checkpoint_id,
            session_id,
            task_id,
            turn_id,
            tool_attempt_id,
            compaction_id,
            artifact_id,
            objective,
            current_phase,
            completed_step,
            next_action,
            blockers_json,
            touched_files_json,
            verification_status,
            budget_status,
            recovery_guidance,
            source_start_sequence,
            source_end_sequence,
            created_at,
            last_sequence
        )
        select
            checkpoint_id,
            session_id,
            task_id,
            turn_id,
            tool_attempt_id,
            compaction_id,
            artifact_id,
            objective,
            current_phase,
            completed_step,
            next_action,
            blockers_json,
            touched_files_json,
            verification_status,
            budget_status,
            recovery_guidance,
            source_start_sequence,
            source_end_sequence,
            created_at,
            last_sequence
        from task_checkpoints_old
        """
    )
    connection.execute("drop table task_checkpoints_old")
    ensure_task_checkpoint_projection_schema(connection)
