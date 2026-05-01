"""Task pause, resume, and terminal-state projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskAbandoned
from glassbox.core.events import TaskCancelled
from glassbox.core.events import TaskPaused
from glassbox.core.events import TaskResumed
from glassbox.core.events import TaskStatusChanged
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.store.sqlite_projection_task_common import _update_task_status


def _apply_task_lifecycle_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> bool:
    payload = event.payload
    if isinstance(payload, TaskPaused):
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.PAUSED,
            blocked_reason=payload.reason,
            blocked_detail=payload.detail,
        )
        return True
    if isinstance(payload, TaskResumed):
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.ACTIVE,
            clear_block=True,
        )
        return True
    if isinstance(payload, TaskCancelled):
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.CANCELLED,
            blocked_reason=TaskBlockedReason.CANCELLED,
            blocked_detail=payload.reason,
            clear_current_step=True,
        )
        return True
    if isinstance(payload, TaskAbandoned):
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.ABANDONED,
            blocked_detail=payload.reason,
            clear_current_step=True,
        )
        return True
    if isinstance(payload, TaskStatusChanged):
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            payload.status,
            blocked_detail=payload.reason,
        )
        return True
    return False


__all__ = ["_apply_task_lifecycle_projection"]
