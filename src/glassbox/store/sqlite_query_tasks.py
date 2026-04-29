"""Task projection read helpers for SQLite-backed stores."""

import sqlite3
from datetime import datetime

from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import TaskRecord
from glassbox.core.models import TaskStepRecord
from glassbox.core.models import TaskVerificationRecord
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.core.types import TaskVerificationStatus


def list_tasks(
    connection: sqlite3.Connection,
    *,
    session_id: SessionId | None = None,
    status: TaskPlanStatus | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[TaskRecord]:
    """Read task summaries, optionally scoped to one session."""

    query = _task_record_select_sql() + " where 1 = 1"
    parameters: list[object] = []
    if session_id is not None:
        query += " and tasks.session_id = ?"
        parameters.append(str(session_id))
    if status is not None:
        query += " and tasks.status = ?"
        parameters.append(status.value)
    query += " group by tasks.session_id, tasks.task_id order by tasks.updated_at desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    if offset:
        query += " offset ?"
        parameters.append(offset)

    rows = connection.execute(query, parameters).fetchall()
    return [_task_record_from_row(row) for row in rows]


def get_task(
    connection: sqlite3.Connection,
    task_id: TaskId,
) -> TaskRecord | None:
    """Read one task summary by ID."""

    row = connection.execute(
        _task_record_select_sql()
        + """
        where tasks.task_id = ?
        group by tasks.session_id, tasks.task_id
        """,
        (str(task_id),),
    ).fetchone()
    if row is None:
        return None
    return _task_record_from_row(row)


def list_task_steps(
    connection: sqlite3.Connection,
    session_id: SessionId,
    task_id: TaskId,
) -> list[TaskStepRecord]:
    """Read task steps in plan order."""

    rows = connection.execute(
        """
        select
            task_id,
            step_id,
            title,
            description,
            step_order,
            status,
            blocked_reason
        from task_steps
        where session_id = ? and task_id = ?
        order by step_order asc, step_id asc
        """,
        (str(session_id), str(task_id)),
    ).fetchall()
    return [
        TaskStepRecord(
            task_id=row["task_id"],
            step_id=row["step_id"],
            title=row["title"],
            description=row["description"],
            order=row["step_order"],
            status=TaskStepStatus(row["status"]),
            blocked_reason=(
                TaskBlockedReason(row["blocked_reason"])
                if row["blocked_reason"]
                else None
            ),
        )
        for row in rows
    ]


def list_task_verifications(
    connection: sqlite3.Connection,
    session_id: SessionId,
    task_id: TaskId,
) -> list[TaskVerificationRecord]:
    """Read verification runs for a task."""

    rows = connection.execute(
        """
        select
            task_id,
            verification_id,
            step_id,
            status,
            check_name,
            summary
        from task_verifications
        where session_id = ? and task_id = ?
        order by coalesce(started_at, completed_at) asc, verification_id asc
        """,
        (str(session_id), str(task_id)),
    ).fetchall()
    return [
        TaskVerificationRecord(
            task_id=row["task_id"],
            verification_id=row["verification_id"],
            step_id=row["step_id"],
            status=TaskVerificationStatus(row["status"]),
            check_name=row["check_name"],
            summary=row["summary"],
        )
        for row in rows
    ]


def list_open_blocked_tasks(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> list[TaskRecord]:
    """Read paused or failed tasks with a blocked reason."""

    rows = connection.execute(
        _task_record_select_sql()
        + """
        where tasks.session_id = ?
          and tasks.blocked_reason is not null
          and tasks.status in (?, ?)
        group by tasks.session_id, tasks.task_id
        order by tasks.updated_at desc
        """,
        (
            str(session_id),
            TaskPlanStatus.PAUSED.value,
            TaskPlanStatus.FAILED.value,
        ),
    ).fetchall()
    return [_task_record_from_row(row) for row in rows]


def _task_record_select_sql() -> str:
    return """
        select
            tasks.task_id,
            tasks.session_id,
            tasks.title,
            tasks.goal,
            tasks.status,
            tasks.source_turn_id,
            tasks.current_step_id,
            tasks.blocked_reason,
            tasks.blocked_detail,
            tasks.created_at,
            tasks.updated_at,
            tasks.last_sequence,
            count(task_steps.step_id) as step_count
        from tasks
        left join task_steps
          on task_steps.session_id = tasks.session_id
         and task_steps.task_id = tasks.task_id
    """


def _task_record_from_row(row: sqlite3.Row) -> TaskRecord:
    return TaskRecord(
        task_id=row["task_id"],
        session_id=row["session_id"],
        title=row["title"],
        goal=row["goal"],
        status=TaskPlanStatus(row["status"]),
        source_turn_id=row["source_turn_id"],
        current_step_id=row["current_step_id"],
        blocked_reason=(
            TaskBlockedReason(row["blocked_reason"]) if row["blocked_reason"] else None
        ),
        blocked_detail=row["blocked_detail"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
        step_count=row["step_count"],
    )


__all__ = [
    "get_task",
    "list_open_blocked_tasks",
    "list_task_steps",
    "list_task_verifications",
    "list_tasks",
]
