"""Schema bootstrap and connection lifecycle for the SQLite store."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from glassbox.store.sqlite_schema_statements import BOOTSTRAP_STATEMENTS
from glassbox.store.sqlite_schema_statements import V3_BASELINE_SCHEMA_STATEMENTS

SCHEMA_VERSION = 18
BASELINE_SCHEMA_VERSION = 3
BASELINE_MIGRATION_NAME = "baseline event store and projections"


@dataclass(frozen=True, slots=True)
class SchemaMigration:
    """One ordered SQLite schema upgrade step."""

    version: int
    name: str
    apply: Callable[[sqlite3.Connection], None]


def open_database(path: Path) -> sqlite3.Connection:
    """Open a SQLite database connection configured for local runtime use."""

    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("pragma foreign_keys = on")
    connection.execute("pragma journal_mode = wal")
    connection.execute("pragma synchronous = normal")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create or migrate the SQLite schema to the current version."""

    with connection:
        _ensure_migration_table(connection)
        _ensure_v3_baseline_schema(connection)
        _ensure_baseline_migration_record(connection)
        _apply_pending_migrations(connection)


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists schema_migrations (
            version integer primary key,
            name text not null default '',
            applied_at text not null default current_timestamp
        )
        """
    )
    existing_columns = _column_names(connection, "schema_migrations")
    if "name" not in existing_columns:
        connection.execute(
            "alter table schema_migrations add column name text not null default ''"
        )


def _ensure_v3_baseline_schema(connection: sqlite3.Connection) -> None:
    for statement in V3_BASELINE_SCHEMA_STATEMENTS:
        connection.execute(statement)


def _ensure_baseline_migration_record(connection: sqlite3.Connection) -> None:
    if BASELINE_SCHEMA_VERSION not in _applied_migration_versions(connection):
        _record_migration(
            connection,
            BASELINE_SCHEMA_VERSION,
            BASELINE_MIGRATION_NAME,
        )
        return

    _ensure_migration_name(
        connection,
        BASELINE_SCHEMA_VERSION,
        BASELINE_MIGRATION_NAME,
    )


def _apply_pending_migrations(connection: sqlite3.Connection) -> None:
    applied_versions = _applied_migration_versions(connection)
    newest_applied_version = max(applied_versions, default=0)
    if newest_applied_version > SCHEMA_VERSION:
        raise ValueError(
            f"database schema version {newest_applied_version} is newer than "
            f"this Glassbox build supports ({SCHEMA_VERSION})"
        )

    for migration in MIGRATIONS:
        migration.apply(connection)
        if migration.version not in applied_versions:
            _record_migration(connection, migration.version, migration.name)
        else:
            _ensure_migration_name(connection, migration.version, migration.name)


def _applied_migration_versions(connection: sqlite3.Connection) -> set[int]:
    rows = connection.execute("select version from schema_migrations").fetchall()
    return {int(row[0]) for row in rows}


def _record_migration(
    connection: sqlite3.Connection,
    version: int,
    name: str,
) -> None:
    connection.execute(
        """
        insert or replace into schema_migrations(version, name)
        values (?, ?)
        """,
        (version, name),
    )


def _ensure_migration_name(
    connection: sqlite3.Connection,
    version: int,
    name: str,
) -> None:
    connection.execute(
        """
        update schema_migrations
        set name = ?
        where version = ? and name = ''
        """,
        (name, version),
    )


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"pragma table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _ensure_sessions_lineage_schema(connection: sqlite3.Connection) -> None:
    existing_columns = _column_names(connection, "sessions")
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


def _ensure_runtime_notes_schema(connection: sqlite3.Connection) -> None:
    existing_columns = _column_names(connection, "runtime_notes")
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


def _ensure_policy_metadata_projection_schema(connection: sqlite3.Connection) -> None:
    tool_call_columns = _column_names(connection, "tool_calls")
    if "policy_outcome" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_outcome text")
    if "policy_risk_level" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_risk_level text")
    if "policy_source_kind" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_source_kind text")
    if "policy_source_label" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_source_label text")
    if "policy_reason" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_reason text")

    approval_columns = _column_names(connection, "approvals")
    if "policy_outcome" not in approval_columns:
        connection.execute("alter table approvals add column policy_outcome text")
    if "policy_risk_level" not in approval_columns:
        connection.execute("alter table approvals add column policy_risk_level text")
    if "policy_source_kind" not in approval_columns:
        connection.execute("alter table approvals add column policy_source_kind text")
    if "policy_source_label" not in approval_columns:
        connection.execute("alter table approvals add column policy_source_label text")


def _ensure_task_projection_schema(connection: sqlite3.Connection) -> None:
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


def _ensure_task_verification_ledger_schema(connection: sqlite3.Connection) -> None:
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


def _ensure_autonomy_budget_projection_schema(connection: sqlite3.Connection) -> None:
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


def _ensure_branch_search_projection_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists branch_searches (
            session_id text not null,
            search_id text not null,
            parent_session_id text not null,
            task_id text,
            objective text not null,
            status text not null,
            selected_candidate_id text,
            abandoned_reason text,
            created_at text not null,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, search_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_branch_searches_session_updated
            on branch_searches (session_id, updated_at desc)
        """
    )
    connection.execute(
        """
        create table if not exists branch_candidates (
            session_id text not null,
            search_id text not null,
            candidate_id text not null,
            parent_session_id text not null,
            candidate_session_id text,
            strategy_label text not null,
            status text not null,
            verification_status text not null,
            selection_state text,
            verification_summary text,
            verification_id text,
            artifact_id text,
            created_at text not null,
            updated_at text not null,
            last_sequence integer not null,
            primary key (session_id, candidate_id),
            foreign key (session_id, search_id)
                references branch_searches(session_id, search_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_branch_candidates_search
            on branch_candidates (session_id, search_id, updated_at)
        """
    )


def _ensure_background_job_projection_schema(connection: sqlite3.Connection) -> None:
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


def _ensure_background_job_retry_schema(connection: sqlite3.Connection) -> None:
    existing_columns = _column_names(connection, "background_jobs")
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


def _ensure_long_run_event_schema(connection: sqlite3.Connection) -> None:
    event_columns = _column_names(connection, "events")
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


def _ensure_task_checkpoint_projection_schema(connection: sqlite3.Connection) -> None:
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


def _ensure_context_compaction_projection_schema(
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
    existing_columns = _column_names(connection, "context_compactions")
    if "freshness_reason" not in existing_columns:
        connection.execute(
            "alter table context_compactions add column freshness_reason text"
        )
    if "superseded_by_compaction_id" not in existing_columns:
        connection.execute(
            "alter table context_compactions add column "
            "superseded_by_compaction_id text"
        )


def _ensure_tool_attempt_projection_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists tool_attempts (
            tool_attempt_id text not null,
            session_id text not null,
            turn_id text not null,
            tool_call_id text,
            task_id text,
            tool_name text not null,
            status text not null,
            message text,
            started_at text,
            last_heartbeat_at text,
            heartbeat_expires_at text,
            completed_at text,
            completed_units integer,
            total_units integer,
            output_artifact_id text,
            safe_to_retry integer,
            retry_classification text,
            retry_requires_approval integer,
            retry_reason text,
            retry_policy_reason text,
            last_sequence integer not null,
            primary key (session_id, tool_attempt_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_tool_attempts_session_status
            on tool_attempts (session_id, status, last_sequence desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_tool_attempts_turn
            on tool_attempts (session_id, turn_id, last_sequence desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_tool_attempts_tool_call
            on tool_attempts (session_id, tool_call_id, last_sequence desc)
        """
    )
    existing_columns = _column_names(connection, "tool_attempts")
    if "retry_classification" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column retry_classification text"
        )
    if "retry_requires_approval" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column retry_requires_approval integer"
        )
    if "retry_policy_reason" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column retry_policy_reason text"
        )


def _ensure_task_checkpoint_session_scoped_key(
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
    _ensure_task_checkpoint_projection_schema(connection)
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
    _ensure_task_checkpoint_projection_schema(connection)


def _ensure_workspace_memory_projection_schema(connection: sqlite3.Connection) -> None:
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


MIGRATIONS = (
    SchemaMigration(
        version=4,
        name="add session lineage columns",
        apply=_ensure_sessions_lineage_schema,
    ),
    SchemaMigration(
        version=5,
        name="add runtime note source columns",
        apply=_ensure_runtime_notes_schema,
    ),
    SchemaMigration(
        version=6,
        name="add policy metadata projection columns",
        apply=_ensure_policy_metadata_projection_schema,
    ),
    SchemaMigration(
        version=7,
        name="add task plan projection tables",
        apply=_ensure_task_projection_schema,
    ),
    SchemaMigration(
        version=8,
        name="add autonomy budget projection table",
        apply=_ensure_autonomy_budget_projection_schema,
    ),
    SchemaMigration(
        version=9,
        name="add background job projection table",
        apply=_ensure_background_job_projection_schema,
    ),
    SchemaMigration(
        version=10,
        name="add background job retry triage columns",
        apply=_ensure_background_job_retry_schema,
    ),
    SchemaMigration(
        version=11,
        name="add workspace memory projection table",
        apply=_ensure_workspace_memory_projection_schema,
    ),
    SchemaMigration(
        version=12,
        name="add branch search projection tables",
        apply=_ensure_branch_search_projection_schema,
    ),
    SchemaMigration(
        version=13,
        name="add long-run event correlations and projection",
        apply=_ensure_long_run_event_schema,
    ),
    SchemaMigration(
        version=14,
        name="add task checkpoint projection table",
        apply=_ensure_task_checkpoint_projection_schema,
    ),
    SchemaMigration(
        version=15,
        name="scope task checkpoint projection key by session",
        apply=_ensure_task_checkpoint_session_scoped_key,
    ),
    SchemaMigration(
        version=16,
        name="add context compaction projection table",
        apply=_ensure_context_compaction_projection_schema,
    ),
    SchemaMigration(
        version=17,
        name="add tool attempt projection table",
        apply=_ensure_tool_attempt_projection_schema,
    ),
    SchemaMigration(
        version=18,
        name="add task verification ledger projection table",
        apply=_ensure_task_verification_ledger_schema,
    ),
)


__all__ = [
    "BOOTSTRAP_STATEMENTS",
    "MIGRATIONS",
    "SCHEMA_VERSION",
    "initialize_database",
    "open_database",
]
