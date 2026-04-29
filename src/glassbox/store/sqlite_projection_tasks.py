"""Task-plan projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskAbandoned
from glassbox.core.events import TaskCancelled
from glassbox.core.events import TaskCreated
from glassbox.core.events import TaskPaused
from glassbox.core.events import TaskPlanProposed
from glassbox.core.events import TaskPlanRevised
from glassbox.core.events import TaskResumed
from glassbox.core.events import TaskStatusChanged
from glassbox.core.events import TaskStepCompleted
from glassbox.core.events import TaskStepFailed
from glassbox.core.events import TaskStepSkipped
from glassbox.core.events import TaskStepStarted
from glassbox.core.events import TaskVerificationCompleted
from glassbox.core.events import TaskVerificationFailed
from glassbox.core.events import TaskVerificationPlanned
from glassbox.core.events import TaskVerificationResidualRiskAccepted
from glassbox.core.events import TaskVerificationRetried
from glassbox.core.events import TaskVerificationSkipped
from glassbox.core.events import TaskVerificationStarted
from glassbox.core.models import TaskStepProposal
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.core.types import TaskVerificationStatus


def _apply_task_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
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
        return
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
        return
    if isinstance(payload, TaskPlanRevised):
        _revise_task(connection, event, payload)
        return
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
        return
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
        return
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
        return
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
        return
    if isinstance(payload, TaskVerificationStarted):
        connection.execute(
            """
            insert into task_verifications (
                session_id, task_id, verification_id, step_id, check_name, status,
                started_at, last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, verification_id) do update set
                task_id = excluded.task_id,
                step_id = excluded.step_id,
                check_name = excluded.check_name,
                status = excluded.status,
                started_at = coalesce(
                    task_verifications.started_at,
                    excluded.started_at
                ),
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.task_id),
                str(payload.verification_id),
                str(payload.step_id) if payload.step_id else None,
                payload.check_name,
                TaskVerificationStatus.RUNNING.value,
                event.created_at.isoformat(),
                event.sequence,
            ),
        )
        _touch_task(connection, event, str(payload.task_id))
        return
    if isinstance(payload, TaskVerificationPlanned):
        connection.execute(
            """
            insert into task_verifications (
                session_id, task_id, verification_id, step_id, check_name, status,
                last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id, verification_id) do update set
                task_id = excluded.task_id,
                step_id = excluded.step_id,
                check_name = excluded.check_name,
                status = excluded.status,
                last_sequence = excluded.last_sequence
            """,
            (
                str(event.session_id),
                str(payload.task_id),
                str(payload.verification.verification_id),
                str(payload.step_id) if payload.step_id else None,
                payload.verification.check_name,
                TaskVerificationStatus.PLANNED.value,
                event.sequence,
            ),
        )
        _touch_task(connection, event, str(payload.task_id))
        return
    if isinstance(payload, TaskVerificationFailed):
        connection.execute(
            """
            update task_verifications
            set status = ?, completed_at = ?, summary = ?, artifact_id = ?,
                last_sequence = ?
            where session_id = ? and verification_id = ?
            """,
            (
                TaskVerificationStatus.FAILED.value,
                event.created_at.isoformat(),
                payload.failure.summary,
                str(payload.failure.artifact_id)
                if payload.failure.artifact_id
                else None,
                event.sequence,
                str(event.session_id),
                str(payload.verification_id),
            ),
        )
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.PAUSED,
            blocked_reason=TaskBlockedReason.VERIFICATION_FAILED,
            blocked_detail=payload.failure.summary,
        )
        return
    if isinstance(payload, TaskVerificationSkipped):
        connection.execute(
            """
            update task_verifications
            set status = ?, completed_at = ?, summary = ?, last_sequence = ?
            where session_id = ? and verification_id = ?
            """,
            (
                TaskVerificationStatus.SKIPPED.value,
                event.created_at.isoformat(),
                payload.reason,
                event.sequence,
                str(event.session_id),
                str(payload.verification_id),
            ),
        )
        _touch_task(connection, event, str(payload.task_id))
        return
    if isinstance(payload, TaskVerificationRetried):
        connection.execute(
            """
            update task_verifications
            set status = ?, summary = ?, last_sequence = ?
            where session_id = ? and verification_id = ?
            """,
            (
                TaskVerificationStatus.RETRIED.value,
                payload.reason,
                event.sequence,
                str(event.session_id),
                str(payload.verification_id),
            ),
        )
        _touch_task(connection, event, str(payload.task_id))
        return
    if isinstance(payload, TaskVerificationCompleted):
        connection.execute(
            """
            update task_verifications
            set status = ?, completed_at = ?, summary = ?, artifact_id = ?,
                last_sequence = ?
            where session_id = ? and verification_id = ?
            """,
            (
                payload.status.value,
                event.created_at.isoformat(),
                payload.summary,
                str(payload.artifact_id) if payload.artifact_id else None,
                event.sequence,
                str(event.session_id),
                str(payload.verification_id),
            ),
        )
        if payload.status == TaskVerificationStatus.FAILED:
            _update_task_status(
                connection,
                event,
                str(payload.task_id),
                TaskPlanStatus.PAUSED,
                blocked_reason=TaskBlockedReason.VERIFICATION_FAILED,
                blocked_detail=payload.summary,
            )
        else:
            _touch_task(connection, event, str(payload.task_id))
        return
    if isinstance(payload, TaskVerificationResidualRiskAccepted):
        connection.execute(
            """
            update task_verifications
            set status = ?, summary = ?, last_sequence = ?
            where session_id = ? and verification_id = ?
            """,
            (
                TaskVerificationStatus.ACCEPTED_WITH_RISK.value,
                payload.reason,
                event.sequence,
                str(event.session_id),
                str(payload.verification_id),
            ),
        )
        _touch_task(connection, event, str(payload.task_id))
        return
    if isinstance(payload, TaskPaused):
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.PAUSED,
            blocked_reason=payload.reason,
            blocked_detail=payload.detail,
        )
        return
    if isinstance(payload, TaskResumed):
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.ACTIVE,
            clear_block=True,
        )
        return
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
        return
    if isinstance(payload, TaskAbandoned):
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            TaskPlanStatus.ABANDONED,
            blocked_detail=payload.reason,
            clear_current_step=True,
        )
        return
    if isinstance(payload, TaskStatusChanged):
        _update_task_status(
            connection,
            event,
            str(payload.task_id),
            payload.status,
            blocked_detail=payload.reason,
        )


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


__all__ = ["_apply_task_projection"]
