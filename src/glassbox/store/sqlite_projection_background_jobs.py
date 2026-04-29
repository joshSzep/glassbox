"""Background job projection handlers for SQLite."""

import json
import sqlite3
from datetime import UTC
from datetime import datetime

from glassbox.core.events import BackgroundJobCancellationRequested
from glassbox.core.events import BackgroundJobCancelled
from glassbox.core.events import BackgroundJobClaimed
from glassbox.core.events import BackgroundJobCompleted
from glassbox.core.events import BackgroundJobCreated
from glassbox.core.events import BackgroundJobFailed
from glassbox.core.events import BackgroundJobHeartbeat
from glassbox.core.events import BackgroundJobPaused
from glassbox.core.events import BackgroundJobProgressRecorded
from glassbox.core.events import BackgroundJobRecoveryRecorded
from glassbox.core.events import BackgroundJobStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.types import BackgroundJobState


def _apply_background_job_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, BackgroundJobCreated):
        connection.execute(
            """
            insert or replace into background_jobs (
                job_id,
                session_id,
                state,
                kind,
                job_type,
                title,
                requested_by,
                payload_json,
                priority,
                task_id,
                parent_job_id,
                created_at,
                updated_at,
                last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(payload.job_id),
                str(event.session_id),
                BackgroundJobState.QUEUED.value,
                payload.kind.value,
                payload.job_type,
                payload.title,
                payload.requested_by,
                json.dumps(payload.payload, sort_keys=True),
                payload.priority,
                _optional_text(payload.task_id),
                _optional_text(payload.parent_job_id),
                _datetime_text(event.created_at),
                _datetime_text(event.created_at),
                event.sequence,
            ),
        )
        return

    if isinstance(payload, BackgroundJobClaimed):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.CLAIMED.value,
            worker_id=payload.worker_id,
            claim_token=payload.claim_token,
            attempt=payload.attempt,
            lease_expires_at=_datetime_text(payload.lease_expires_at),
        )
        return

    if isinstance(payload, BackgroundJobStarted):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.RUNNING.value,
            worker_id=payload.worker_id,
            claim_token=payload.claim_token,
            attempt=payload.attempt,
            started_at=_datetime_text(event.created_at),
        )
        return

    if isinstance(payload, BackgroundJobHeartbeat):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=payload.state.value,
            worker_id=payload.worker_id,
            claim_token=payload.claim_token,
            lease_expires_at=_datetime_text(payload.lease_expires_at),
            last_heartbeat_at=_datetime_text(event.created_at),
            progress_message=payload.message,
        )
        return

    if isinstance(payload, BackgroundJobProgressRecorded):
        _update_job(
            connection,
            payload.job_id,
            event,
            progress_message=payload.message,
            completed_units=payload.completed_units,
            total_units=payload.total_units,
        )
        return

    if isinstance(payload, BackgroundJobPaused):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.PAUSED.value,
            progress_message=payload.detail or payload.reason.value,
        )
        return

    if isinstance(payload, BackgroundJobCompleted):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.COMPLETED.value,
            progress_message=payload.summary,
            completed_at=_datetime_text(event.created_at),
        )
        return

    if isinstance(payload, BackgroundJobFailed):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.FAILED.value,
            failure_kind=payload.failure_kind.value,
            failure_message=payload.message,
            retryable=1 if payload.retryable else 0,
            attempt=payload.attempt,
            next_retry_at=(
                None
                if payload.next_retry_at is None
                else _datetime_text(payload.next_retry_at)
            ),
            completed_at=_datetime_text(event.created_at),
        )
        return

    if isinstance(payload, BackgroundJobCancellationRequested):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.CANCELLATION_REQUESTED.value,
            cancellation_requested_by=payload.requested_by,
            cancellation_reason=payload.reason,
        )
        return

    if isinstance(payload, BackgroundJobCancelled):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.CANCELLED.value,
            cancelled_by=payload.cancelled_by,
            cancellation_reason=payload.reason,
            completed_at=_datetime_text(event.created_at),
        )
        return

    if isinstance(payload, BackgroundJobRecoveryRecorded):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.STALE.value,
            recovery_reason=payload.reason.value,
            recovery_detail=payload.detail,
        )


def _update_job(
    connection: sqlite3.Connection,
    job_id,
    event: EventEnvelope,
    **fields,
) -> None:
    assignments = ["updated_at = ?", "last_sequence = ?"]
    values: list[object] = [_datetime_text(event.created_at), event.sequence]
    for name, value in fields.items():
        assignments.append(f"{name} = ?")
        values.append(value)
    values.append(str(job_id))
    connection.execute(
        f"""
        update background_jobs
        set {", ".join(assignments)}
        where job_id = ?
        """,
        values,
    )


def _datetime_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _optional_text(value) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = ["_apply_background_job_projection"]
