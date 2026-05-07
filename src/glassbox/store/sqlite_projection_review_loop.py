"""Review-loop projection coordinator for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.store.sqlite_projection_manual_evidence import (
    _apply_manual_evidence_projection,
)
from glassbox.store.sqlite_projection_review_feedback import (
    _apply_review_feedback_projection,
)


def _apply_review_loop_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    _apply_review_feedback_projection(connection, event)
    _apply_manual_evidence_projection(connection, event)


__all__ = ["_apply_review_loop_projection"]
