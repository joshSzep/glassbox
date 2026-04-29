"""Schema bootstrap and connection lifecycle for the SQLite store."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from glassbox.store.sqlite_schema_statements import BOOTSTRAP_STATEMENTS
from glassbox.store.sqlite_schema_statements import V3_BASELINE_SCHEMA_STATEMENTS

SCHEMA_VERSION = 11
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
)


__all__ = [
    "BOOTSTRAP_STATEMENTS",
    "MIGRATIONS",
    "SCHEMA_VERSION",
    "initialize_database",
    "open_database",
]
