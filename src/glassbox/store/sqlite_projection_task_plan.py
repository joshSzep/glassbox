"""Task-plan projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskCreated
from glassbox.core.events import TaskPlanProposed
from glassbox.core.events import TaskPlanRevised
from glassbox.core.types import TaskPlanStatus
from glassbox.store.sqlite_projection_task_common import _replace_steps
from glassbox.store.sqlite_projection_task_common import _revise_task
from glassbox.store.sqlite_projection_task_common import _upsert_task


def _apply_task_plan_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> bool:
    payload = event.payload
    if isinstance(payload, TaskCreated):
        _upsert_task(
            connection,
            event,
            task_id=str(payload.task_id),
            title=payload.title,
            goal=payload.goal,
            status=TaskPlanStatus.PROPOSED,
            source_turn_id=(
                str(payload.source_turn_id) if payload.source_turn_id else None
            ),
        )
        return True
    if isinstance(payload, TaskPlanProposed):
        _upsert_task(
            connection,
            event,
            task_id=str(payload.task_id),
            title=payload.plan.title,
            goal=payload.plan.goal,
            status=payload.plan.status,
        )
        _replace_steps(connection, event, str(payload.task_id), payload.plan.steps)
        return True
    if isinstance(payload, TaskPlanRevised):
        _revise_task(connection, event, payload)
        return True
    return False


__all__ = ["_apply_task_plan_projection"]
