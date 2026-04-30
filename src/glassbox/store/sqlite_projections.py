"""Projection application coordinator for the SQLite-backed event store."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.ids import SessionId
from glassbox.store.sqlite_projection_approvals import _apply_approval_projection
from glassbox.store.sqlite_projection_background_jobs import (
    _apply_background_job_projection,
)
from glassbox.store.sqlite_projection_branch_search import (
    _apply_branch_search_projection,
)
from glassbox.store.sqlite_projection_budgets import _apply_budget_projection
from glassbox.store.sqlite_projection_checkpoints import (
    _apply_task_checkpoint_projection,
)
from glassbox.store.sqlite_projection_compactions import (
    _apply_context_compaction_projection,
)
from glassbox.store.sqlite_projection_long_run import _apply_long_run_projection
from glassbox.store.sqlite_projection_provider_recovery import (
    _apply_provider_recovery_projection,
)
from glassbox.store.sqlite_projection_runtime_notes import (
    _apply_runtime_note_projection,
)
from glassbox.store.sqlite_projection_session_state import (
    _apply_session_state_projection,
)
from glassbox.store.sqlite_projection_tasks import _apply_task_projection
from glassbox.store.sqlite_projection_tool_attempts import (
    _apply_tool_attempt_projection,
)
from glassbox.store.sqlite_projection_tools import _apply_tool_call_projection
from glassbox.store.sqlite_projection_transcript import _apply_transcript_projection
from glassbox.store.sqlite_projection_turn_metrics import _apply_turn_metrics_projection
from glassbox.store.sqlite_projection_verification_ledger import (
    _apply_verification_ledger_projection,
)
from glassbox.store.sqlite_projection_workspace_memory import (
    _apply_workspace_memory_projection,
)

_PROJECTION_TABLES = (
    "session_state",
    "transcript_messages",
    "tool_calls",
    "tool_attempts",
    "approvals",
    "runtime_notes",
    "turn_metrics",
    "task_verification_ledger",
    "task_verifications",
    "task_steps",
    "tasks",
    "branch_candidates",
    "branch_searches",
    "autonomy_budget_posture",
    "background_jobs",
    "workspace_memory",
    "provider_recovery",
    "long_run_events",
    "task_checkpoints",
    "context_compactions",
)


def _apply_projection_event(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    _apply_session_state_projection(connection, event)
    _apply_transcript_projection(connection, event)
    _apply_tool_call_projection(connection, event)
    _apply_tool_attempt_projection(connection, event)
    _apply_approval_projection(connection, event)
    _apply_runtime_note_projection(connection, event)
    _apply_turn_metrics_projection(connection, event)
    _apply_task_projection(connection, event)
    _apply_verification_ledger_projection(connection, event)
    _apply_branch_search_projection(connection, event)
    _apply_budget_projection(connection, event)
    _apply_background_job_projection(connection, event)
    _apply_workspace_memory_projection(connection, event)
    _apply_provider_recovery_projection(connection, event)
    _apply_long_run_projection(connection, event)
    _apply_task_checkpoint_projection(connection, event)
    _apply_context_compaction_projection(connection, event)


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
