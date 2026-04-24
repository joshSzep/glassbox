"""Storage bootstrap helpers for runtime entrypoints."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database


@dataclass(frozen=True, slots=True)
class RuntimeStoragePaths:
    """Resolved workspace and database paths for one runtime entrypoint."""

    workspace_root: Path
    database_path: Path


def default_database_path(cwd: Path) -> Path:
    """Return the default SQLite database path for a workspace root."""

    return cwd / ".glassbox" / "glassbox.sqlite3"


def resolve_runtime_storage_paths(
    cwd: Path,
    *,
    db_path: Path | None = None,
) -> RuntimeStoragePaths:
    """Resolve the workspace root and database path for runtime bootstrap."""

    workspace_root = cwd.resolve()
    database_path = (db_path or default_database_path(workspace_root)).resolve()
    return RuntimeStoragePaths(
        workspace_root=workspace_root,
        database_path=database_path,
    )


def open_initialized_runtime_database(paths: RuntimeStoragePaths) -> sqlite3.Connection:
    """Open the SQLite database and ensure the schema exists."""

    connection = open_database(paths.database_path)
    initialize_database(connection)
    return connection
