"""Integration tests for the SQLite bootstrap layer."""

import sqlite3
from pathlib import Path

from glassbox.store import SCHEMA_VERSION, initialize_database, open_database


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "select name from sqlite_master where type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def test_open_database_configures_sqlite_connection(tmp_path: Path) -> None:
    database_path = tmp_path / "glassbox.sqlite3"

    connection = open_database(database_path)
    try:
        foreign_keys_enabled = connection.execute("pragma foreign_keys").fetchone()[0]
        journal_mode = connection.execute("pragma journal_mode").fetchone()[0]
    finally:
        connection.close()

    assert database_path.exists()
    assert foreign_keys_enabled == 1
    assert journal_mode == "wal"


def test_initialize_database_creates_bootstrap_schema(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        initialize_database(connection)
        tables = _table_names(connection)
        migration_versions = connection.execute(
            "select version from schema_migrations"
        ).fetchall()
    finally:
        connection.close()

    assert {"schema_migrations", "sessions", "events"}.issubset(tables)
    assert [row[0] for row in migration_versions] == [SCHEMA_VERSION]


def test_initialize_database_is_idempotent(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    try:
        initialize_database(connection)
        initialize_database(connection)
        migration_count = connection.execute(
            "select count(*) from schema_migrations where version = ?",
            (SCHEMA_VERSION,),
        ).fetchone()[0]
    finally:
        connection.close()

    assert migration_count == 1
