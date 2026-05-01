"""Task-verification projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskVerificationCompleted
from glassbox.core.events import TaskVerificationFailed
from glassbox.core.events import TaskVerificationPlanned
from glassbox.core.events import TaskVerificationResidualRiskAccepted
from glassbox.core.events import TaskVerificationRetried
from glassbox.core.events import TaskVerificationSkipped
from glassbox.core.events import TaskVerificationStarted
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.store.sqlite_projection_task_common import _touch_task
from glassbox.store.sqlite_projection_task_common import _update_task_status


def _apply_task_verification_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> bool:
    payload = event.payload
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
        return True
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
        return True
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
        return True
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
        return True
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
        return True
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
        return True
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
        return True
    return False


__all__ = ["_apply_task_verification_projection"]
