"""Background job projection coordinator for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.store.sqlite_projection_background_job_control import (
    _apply_background_job_control_projection,
)
from glassbox.store.sqlite_projection_background_job_creation import (
    _apply_background_job_creation_projection,
)
from glassbox.store.sqlite_projection_background_job_lifecycle import (
    _apply_background_job_lifecycle_projection,
)
from glassbox.store.sqlite_projection_background_job_recovery import (
    _apply_background_job_recovery_projection,
)


def _apply_background_job_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    if _apply_background_job_creation_projection(connection, event):
        return
    if _apply_background_job_lifecycle_projection(connection, event):
        return
    if _apply_background_job_control_projection(connection, event):
        return
    _apply_background_job_recovery_projection(connection, event)


__all__ = ["_apply_background_job_projection"]
