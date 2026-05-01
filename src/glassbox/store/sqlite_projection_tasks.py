"""Task projection coordinator for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.store.sqlite_projection_task_lifecycle import (
    _apply_task_lifecycle_projection,
)
from glassbox.store.sqlite_projection_task_plan import _apply_task_plan_projection
from glassbox.store.sqlite_projection_task_steps import _apply_task_step_projection
from glassbox.store.sqlite_projection_task_verifications import (
    _apply_task_verification_projection,
)


def _apply_task_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    if _apply_task_plan_projection(connection, event):
        return
    if _apply_task_step_projection(connection, event):
        return
    if _apply_task_verification_projection(connection, event):
        return
    _apply_task_lifecycle_projection(connection, event)


__all__ = ["_apply_task_projection"]
