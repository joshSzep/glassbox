"""Task-step projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskStepCompleted
from glassbox.core.events import TaskStepFailed
from glassbox.core.events import TaskStepSkipped
from glassbox.core.events import TaskStepStarted
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.store.sqlite_projection_task_common import _ensure_step
from glassbox.store.sqlite_projection_task_common import _touch_task
from glassbox.store.sqlite_projection_task_common import _update_task_status


def _apply_task_step_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> bool:
    payload = event.payload
    if isinstance(payload, TaskStepStarted):
        _ensure_step(connection, event, str(payload.task_id), str(payload.step_id))
        connection.execute(
            """
            update task_steps
            set status = ?, started_at = coalesce(started_at, ?), last_sequence = ?
            where session_id = ? and step_id = ?
            """,
            (
                TaskStepStatus.RUNNING.value,
                event.created_at.isoformat(),
                event.sequence,
                str(event.session_id),
                str(payload.step_id),
            ),
        )
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.ACTIVE,
            current_step_id=str(payload.step_id),
            clear_block=True,
        )
        return True
    if isinstance(payload, TaskStepCompleted):
        connection.execute(
            """
            update task_steps
            set status = ?, completed_at = ?, summary = ?, blocked_reason = null,
                failure_reason = null, last_sequence = ?
            where session_id = ? and step_id = ?
            """,
            (
                TaskStepStatus.COMPLETED.value,
                event.created_at.isoformat(),
                payload.summary,
                event.sequence,
                str(event.session_id),
                str(payload.step_id),
            ),
        )
        _touch_task(connection, event, str(payload.task_id), clear_current_step=True)
        return True
    if isinstance(payload, TaskStepFailed):
        connection.execute(
            """
            update task_steps
            set status = ?, completed_at = ?, failure_reason = ?, blocked_reason = ?,
                last_sequence = ?
            where session_id = ? and step_id = ?
            """,
            (
                TaskStepStatus.FAILED.value,
                event.created_at.isoformat(),
                payload.reason,
                payload.blocked_reason.value if payload.blocked_reason else None,
                event.sequence,
                str(event.session_id),
                str(payload.step_id),
            ),
        )
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.FAILED,
            blocked_reason=payload.blocked_reason,
            blocked_detail=payload.reason,
            clear_current_step=True,
        )
        return True
    if isinstance(payload, TaskStepSkipped):
        connection.execute(
            """
            update task_steps
            set status = ?, completed_at = ?, summary = ?, last_sequence = ?
            where session_id = ? and step_id = ?
            """,
            (
                TaskStepStatus.SKIPPED.value,
                event.created_at.isoformat(),
                payload.reason,
                event.sequence,
                str(event.session_id),
                str(payload.step_id),
            ),
        )
        _touch_task(connection, event, str(payload.task_id), clear_current_step=True)
        return True
    return False


__all__ = ["_apply_task_step_projection"]
