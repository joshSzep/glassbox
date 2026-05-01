"""Shared task projection SQL helpers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskPlanRevised
from glassbox.core.models import TaskStepProposal
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus


def _upsert_task(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    *,
    task_id: str,
    title: str,
    goal: str,
    status: TaskPlanStatus,
    source_turn_id: str | None = None,
) -> None:
    connection.execute(
        """
        insert into tasks (
            session_id, task_id, title, goal, status, source_turn_id, created_at,
            updated_at, last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id, task_id) do update set
            title = excluded.title,
            goal = excluded.goal,
            status = excluded.status,
            source_turn_id = coalesce(tasks.source_turn_id, excluded.source_turn_id),
            updated_at = excluded.updated_at,
            last_sequence = excluded.last_sequence
        """,
        (
            str(event.session_id),
            task_id,
            title,
            goal,
            status.value,
            source_turn_id,
            event.created_at.isoformat(),
            event.created_at.isoformat(),
            event.sequence,
        ),
    )


def _replace_steps(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    task_id: str,
    steps: list[TaskStepProposal],
) -> None:
    retained_step_ids = {str(step.step_id) for step in steps}
    if retained_step_ids:
        placeholders = ", ".join("?" for _ in retained_step_ids)
        connection.execute(
            f"""
            delete from task_steps
            where session_id = ? and task_id = ? and step_id not in ({placeholders})
            """,
            (str(event.session_id), task_id, *retained_step_ids),
        )
    else:
        connection.execute(
            "delete from task_steps where session_id = ? and task_id = ?",
            (str(event.session_id), task_id),
        )

    for step in steps:
        connection.execute(
            """
            insert into task_steps (
                session_id, task_id, step_id, title, description, step_order,
                status, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, step_id) do update set
                task_id = excluded.task_id,
                title = excluded.title,
                description = excluded.description,
                step_order = excluded.step_order,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                task_id,
                str(step.step_id),
                step.title,
                step.description,
                step.order,
                TaskStepStatus.PENDING.value,
                event.sequence,
            ),
        )


def _revise_task(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    payload: TaskPlanRevised,
) -> None:
    assignments = ["updated_at = ?", "last_sequence = ?"]
    parameters: list[object] = [event.created_at.isoformat(), event.sequence]
    if payload.title is not None:
        assignments.append("title = ?")
        parameters.append(payload.title)
    if payload.goal is not None:
        assignments.append("goal = ?")
        parameters.append(payload.goal)
    parameters.extend([str(event.session_id), str(payload.task_id)])
    connection.execute(
        f"""
        update tasks
        set {", ".join(assignments)}
        where session_id = ? and task_id = ?
        """,
        parameters,
    )
    if payload.steps is not None:
        _replace_steps(connection, event, str(payload.task_id), payload.steps)


def _ensure_step(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    task_id: str,
    step_id: str,
) -> None:
    connection.execute(
        """
        insert into task_steps (
            session_id, task_id, step_id, title, description, step_order, status,
            last_sequence
        ) values (?, ?, ?, ?, null, ?, ?, ?)
        on conflict(session_id, step_id) do nothing
        """,
        (
            str(event.session_id),
            task_id,
            step_id,
            f"Step {step_id}",
            0,
            TaskStepStatus.PENDING.value,
            event.sequence,
        ),
    )


def _touch_task(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    task_id: str,
    *,
    clear_current_step: bool = False,
) -> None:
    assignments = ["updated_at = ?", "last_sequence = ?"]
    parameters: list[object] = [event.created_at.isoformat(), event.sequence]
    if clear_current_step:
        assignments.append("current_step_id = null")
    parameters.extend([str(event.session_id), task_id])
    connection.execute(
        f"""
        update tasks
        set {", ".join(assignments)}
        where session_id = ? and task_id = ?
        """,
        parameters,
    )


def _update_task_status(
    connection: sqlite3.Connection,
    event: EventEnvelope,
    task_id: str,
    status: TaskPlanStatus,
    *,
    current_step_id: str | None = None,
    blocked_reason: TaskBlockedReason | None = None,
    blocked_detail: str | None = None,
    clear_block: bool = False,
    clear_current_step: bool = False,
) -> None:
    assignments = ["status = ?", "updated_at = ?", "last_sequence = ?"]
    parameters: list[object] = [
        status.value,
        event.created_at.isoformat(),
        event.sequence,
    ]
    if current_step_id is not None:
        assignments.append("current_step_id = ?")
        parameters.append(current_step_id)
    if clear_current_step:
        assignments.append("current_step_id = null")
    if blocked_reason is not None:
        assignments.append("blocked_reason = ?")
        parameters.append(blocked_reason.value)
    if blocked_detail is not None:
        assignments.append("blocked_detail = ?")
        parameters.append(blocked_detail)
    if clear_block:
        assignments.extend(["blocked_reason = null", "blocked_detail = null"])
    parameters.extend([str(event.session_id), task_id])
    connection.execute(
        f"""
        update tasks
        set {", ".join(assignments)}
        where session_id = ? and task_id = ?
        """,
        parameters,
    )


__all__ = [
    "_ensure_step",
    "_replace_steps",
    "_revise_task",
    "_touch_task",
    "_update_task_status",
    "_upsert_task",
]
