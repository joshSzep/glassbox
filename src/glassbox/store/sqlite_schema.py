"""Schema bootstrap, migration registry, and connection lifecycle."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from glassbox.store.sqlite_schema_background_jobs import (
    ensure_background_job_projection_schema,
)
from glassbox.store.sqlite_schema_background_jobs import (
    ensure_background_job_retry_schema,
)
from glassbox.store.sqlite_schema_branch_search import (
    ensure_branch_search_projection_schema,
)
from glassbox.store.sqlite_schema_changesets import ensure_changeset_projection_schema
from glassbox.store.sqlite_schema_checkpoints import (
    ensure_task_checkpoint_projection_schema,
)
from glassbox.store.sqlite_schema_checkpoints import (
    ensure_task_checkpoint_session_scoped_key,
)
from glassbox.store.sqlite_schema_compactions import (
    ensure_context_compaction_projection_schema,
)
from glassbox.store.sqlite_schema_helpers import column_names
from glassbox.store.sqlite_schema_long_run import ensure_long_run_event_schema
from glassbox.store.sqlite_schema_provider_recovery import (
    ensure_provider_recovery_projection_schema,
)
from glassbox.store.sqlite_schema_review_loop import (
    ensure_review_loop_projection_schema,
)
from glassbox.store.sqlite_schema_sessions import ensure_runtime_notes_schema
from glassbox.store.sqlite_schema_sessions import ensure_sessions_lineage_schema
from glassbox.store.sqlite_schema_statements import BOOTSTRAP_STATEMENTS
from glassbox.store.sqlite_schema_statements import V3_BASELINE_SCHEMA_STATEMENTS
from glassbox.store.sqlite_schema_tasks import ensure_autonomy_budget_projection_schema
from glassbox.store.sqlite_schema_tasks import ensure_task_projection_schema
from glassbox.store.sqlite_schema_tasks import ensure_task_verification_ledger_schema
from glassbox.store.sqlite_schema_tools import ensure_policy_metadata_projection_schema
from glassbox.store.sqlite_schema_tools import ensure_tool_attempt_projection_schema
from glassbox.store.sqlite_schema_workspace_memory import (
    ensure_workspace_memory_projection_schema,
)

SCHEMA_VERSION = 21
BASELINE_SCHEMA_VERSION = 3
BASELINE_MIGRATION_NAME = "baseline event store and projections"


@dataclass(frozen=True, slots=True)
class SchemaMigration:
    """One ordered SQLite schema upgrade step."""

    version: int
    name: str
    apply: Callable[[sqlite3.Connection], None]


MIGRATIONS = (
    SchemaMigration(
        version=4,
        name="add session lineage columns",
        apply=ensure_sessions_lineage_schema,
    ),
    SchemaMigration(
        version=5,
        name="add runtime note source columns",
        apply=ensure_runtime_notes_schema,
    ),
    SchemaMigration(
        version=6,
        name="add policy metadata projection columns",
        apply=ensure_policy_metadata_projection_schema,
    ),
    SchemaMigration(
        version=7,
        name="add task plan projection tables",
        apply=ensure_task_projection_schema,
    ),
    SchemaMigration(
        version=8,
        name="add autonomy budget projection table",
        apply=ensure_autonomy_budget_projection_schema,
    ),
    SchemaMigration(
        version=9,
        name="add background job projection table",
        apply=ensure_background_job_projection_schema,
    ),
    SchemaMigration(
        version=10,
        name="add background job retry triage columns",
        apply=ensure_background_job_retry_schema,
    ),
    SchemaMigration(
        version=11,
        name="add workspace memory projection table",
        apply=ensure_workspace_memory_projection_schema,
    ),
    SchemaMigration(
        version=12,
        name="add branch search projection tables",
        apply=ensure_branch_search_projection_schema,
    ),
    SchemaMigration(
        version=13,
        name="add long-run event correlations and projection",
        apply=ensure_long_run_event_schema,
    ),
    SchemaMigration(
        version=14,
        name="add task checkpoint projection table",
        apply=ensure_task_checkpoint_projection_schema,
    ),
    SchemaMigration(
        version=15,
        name="scope task checkpoint projection key by session",
        apply=ensure_task_checkpoint_session_scoped_key,
    ),
    SchemaMigration(
        version=16,
        name="add context compaction projection table",
        apply=ensure_context_compaction_projection_schema,
    ),
    SchemaMigration(
        version=17,
        name="add tool attempt projection table",
        apply=ensure_tool_attempt_projection_schema,
    ),
    SchemaMigration(
        version=18,
        name="add task verification ledger projection table",
        apply=ensure_task_verification_ledger_schema,
    ),
    SchemaMigration(
        version=19,
        name="add provider recovery projection table",
        apply=ensure_provider_recovery_projection_schema,
    ),
    SchemaMigration(
        version=20,
        name="add changeset projection tables",
        apply=ensure_changeset_projection_schema,
    ),
    SchemaMigration(
        version=21,
        name="add review feedback projection tables",
        apply=ensure_review_loop_projection_schema,
    ),
)


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
    existing_columns = column_names(connection, "schema_migrations")
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


__all__ = [
    "BOOTSTRAP_STATEMENTS",
    "MIGRATIONS",
    "SCHEMA_VERSION",
    "initialize_database",
    "open_database",
]
