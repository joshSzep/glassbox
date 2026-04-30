"""Task, verification-ledger, and autonomy-budget SQLite schema migrations."""

import sqlite3


def ensure_task_projection_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists tasks (
            session_id text not null,
            task_id text not null,
            title text not null,
            goal text not null,
            status text not null,
            source_turn_id text,
            current_step_id text,
            blocked_reason text,
            blocked_detail text,
            created_at text not null,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, task_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )

    connection.execute(
        """
        create index if not exists idx_tasks_session_status_updated
            on tasks (session_id, status, updated_at desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_tasks_session_blocked
            on tasks (session_id, blocked_reason, updated_at desc)
        """
    )
    connection.execute(
        """
        create table if not exists task_steps (
            session_id text not null,
            task_id text not null,
            step_id text not null,
            title text not null,
            description text,
            step_order integer not null,
            status text not null,
            blocked_reason text,
            started_at text,
            completed_at text,
            summary text,
            failure_reason text,
            last_sequence integer not null,
            primary key (session_id, step_id),
            foreign key (session_id, task_id) references tasks(session_id, task_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_task_steps_task_order
            on task_steps (session_id, task_id, step_order)
        """
    )
    connection.execute(
        """
        create index if not exists idx_task_steps_session_status
            on task_steps (session_id, status)
        """
    )
    connection.execute(
        """
        create table if not exists task_verifications (
            session_id text not null,
            task_id text not null,
            verification_id text not null,
            step_id text,
            check_name text not null,
            status text not null,
            started_at text,
            completed_at text,
            summary text,
            artifact_id text,
            last_sequence integer not null,
            primary key (session_id, verification_id),
            foreign key (session_id, task_id) references tasks(session_id, task_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_task_verifications_task
            on task_verifications (session_id, task_id, started_at)
        """
    )


def ensure_task_verification_ledger_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        create table if not exists task_verification_ledger (
            session_id text not null,
            task_id text not null,
            verification_id text not null,
            step_id text,
            status text not null,
            check_name text not null,
            kind text,
            source text,
            command_json text not null,
            changed_paths_json text not null,
            eval_case_id text,
            eval_profile_id text,
            blocking integer not null default 1,
            attempt_count integer not null default 0,
            latest_attempt integer not null default 0,
            planned_sequence integer,
            started_sequence integer,
            last_success_sequence integer,
            latest_failed_sequence integer,
            latest_failed_summary text,
            latest_failed_category text,
            latest_failed_artifact_id text,
            latest_artifact_id text,
            accepted_risk_count integer not null default 0,
            accepted_risks_json text not null,
            residual_risk_reason text,
            summary text,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, verification_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_task_verification_ledger_task
            on task_verification_ledger (session_id, task_id, last_sequence)
        """
    )
    connection.execute(
        """
        create index if not exists idx_task_verification_ledger_status
            on task_verification_ledger (session_id, task_id, status)
        """
    )


def ensure_autonomy_budget_projection_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        create table if not exists autonomy_budget_posture (
            session_id text not null,
            task_id text not null default '',
            scope text not null,
            mode text,
            budget_json text,
            usage_json text not null,
            remaining_json text,
            last_decision text not null,
            last_reason text,
            last_limit_name text,
            last_detail text,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, task_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_autonomy_budget_posture_session_updated
            on autonomy_budget_posture (session_id, updated_at desc)
        """
    )
