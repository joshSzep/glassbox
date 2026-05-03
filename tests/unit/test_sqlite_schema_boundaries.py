"""Boundary checks for SQLite schema migration modules."""

from collections.abc import Mapping
from importlib import import_module

from glassbox.store.sqlite_schema import MIGRATIONS
from glassbox.store.sqlite_schema import SCHEMA_VERSION

MIGRATION_OWNERS: Mapping[int, str] = {
    4: "glassbox.store.sqlite_schema_sessions",
    5: "glassbox.store.sqlite_schema_sessions",
    6: "glassbox.store.sqlite_schema_tools",
    7: "glassbox.store.sqlite_schema_tasks",
    8: "glassbox.store.sqlite_schema_tasks",
    9: "glassbox.store.sqlite_schema_background_jobs",
    10: "glassbox.store.sqlite_schema_background_jobs",
    11: "glassbox.store.sqlite_schema_workspace_memory",
    12: "glassbox.store.sqlite_schema_branch_search",
    13: "glassbox.store.sqlite_schema_long_run",
    14: "glassbox.store.sqlite_schema_checkpoints",
    15: "glassbox.store.sqlite_schema_checkpoints",
    16: "glassbox.store.sqlite_schema_compactions",
    17: "glassbox.store.sqlite_schema_tools",
    18: "glassbox.store.sqlite_schema_tasks",
    19: "glassbox.store.sqlite_schema_provider_recovery",
    20: "glassbox.store.sqlite_schema_changesets",
    21: "glassbox.store.sqlite_schema_review_loop",
}


def test_sqlite_schema_registry_remains_explicit_and_ordered() -> None:
    migration_versions = [migration.version for migration in MIGRATIONS]

    assert migration_versions == list(range(4, SCHEMA_VERSION + 1))


def test_sqlite_schema_migrations_are_owned_by_domain_modules() -> None:
    for migration in MIGRATIONS:
        assert migration.apply.__module__ == MIGRATION_OWNERS[migration.version]


def test_sqlite_schema_domain_modules_are_documented() -> None:
    for module_name in set(MIGRATION_OWNERS.values()):
        module = import_module(module_name)

        assert module.__doc__
