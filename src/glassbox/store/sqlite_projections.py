"""Projection application coordinator for the SQLite-backed event store."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.ids import SessionId
from glassbox.store.sqlite_projection_approvals import _apply_approval_projection
from glassbox.store.sqlite_projection_budgets import _apply_budget_projection
from glassbox.store.sqlite_projection_runtime_notes import (
    _apply_runtime_note_projection,
)
from glassbox.store.sqlite_projection_session_state import (
    _apply_session_state_projection,
)
from glassbox.store.sqlite_projection_tasks import _apply_task_projection
from glassbox.store.sqlite_projection_tools import _apply_tool_call_projection
from glassbox.store.sqlite_projection_transcript import _apply_transcript_projection
from glassbox.store.sqlite_projection_turn_metrics import _apply_turn_metrics_projection

_PROJECTION_TABLES = (
    "session_state",
    "transcript_messages",
    "tool_calls",
    "approvals",
    "runtime_notes",
    "turn_metrics",
    "tasks",
    "task_steps",
    "task_verifications",
    "autonomy_budget_posture",
)


def _apply_projection_event(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    _apply_session_state_projection(connection, event)
    _apply_transcript_projection(connection, event)
    _apply_tool_call_projection(connection, event)
    _apply_approval_projection(connection, event)
    _apply_runtime_note_projection(connection, event)
    _apply_turn_metrics_projection(connection, event)
    _apply_task_projection(connection, event)
    _apply_budget_projection(connection, event)


def _clear_session_projections(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> None:
    session_id_value = str(session_id)
    for table_name in _PROJECTION_TABLES:
        connection.execute(
            f"delete from {table_name} where session_id = ?",
            (session_id_value,),
        )


__all__ = ["_apply_projection_event", "_clear_session_projections"]
