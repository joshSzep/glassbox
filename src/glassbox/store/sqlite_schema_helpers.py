"""Shared helpers for SQLite schema migrations."""

import sqlite3


def column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    """Return the currently declared columns for a table."""

    rows = connection.execute(f"pragma table_info({table_name})").fetchall()
    return {row[1] for row in rows}
