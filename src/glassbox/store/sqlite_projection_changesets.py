"""Changeset projection coordinator for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.store.sqlite_projection_changeset_inventory import (
    _apply_changeset_inventory_projection,
)
from glassbox.store.sqlite_projection_changeset_lifecycle import (
    _apply_changeset_lifecycle_projection,
)


def _apply_changeset_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    _apply_changeset_lifecycle_projection(connection, event)
    _apply_changeset_inventory_projection(connection, event)


__all__ = ["_apply_changeset_projection"]
