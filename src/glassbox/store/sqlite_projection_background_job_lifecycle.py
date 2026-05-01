"""Background-job lifecycle projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import BackgroundJobAbandoned
from glassbox.core.events import BackgroundJobClaimed
from glassbox.core.events import BackgroundJobCompleted
from glassbox.core.events import BackgroundJobFailed
from glassbox.core.events import BackgroundJobHeartbeat
from glassbox.core.events import BackgroundJobProgressRecorded
from glassbox.core.events import BackgroundJobStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.types import BackgroundJobState
from glassbox.store.sqlite_projection_background_job_common import _datetime_text
from glassbox.store.sqlite_projection_background_job_common import _optional_text
from glassbox.store.sqlite_projection_background_job_common import _update_job


def _apply_background_job_lifecycle_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> bool:
    payload = event.payload
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
        return True

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
        return True

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
        return True

    if isinstance(payload, BackgroundJobProgressRecorded):
        _update_job(
            connection,
            payload.job_id,
            event,
            progress_message=payload.message,
            completed_units=payload.completed_units,
            total_units=payload.total_units,
        )
        return True

    if isinstance(payload, BackgroundJobCompleted):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.COMPLETED.value,
            progress_message=payload.summary,
            completed_at=_datetime_text(event.created_at),
        )
        return True

    if isinstance(payload, BackgroundJobFailed):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.FAILED.value,
            failure_kind=payload.failure_kind.value,
            failure_message=payload.message,
            failure_artifact_id=_optional_text(payload.artifact_id),
            failure_artifact_path=payload.artifact_path,
            retryable=1 if payload.retryable else 0,
            attempt=payload.attempt,
            next_retry_at=(
                None
                if payload.next_retry_at is None
                else _datetime_text(payload.next_retry_at)
            ),
            completed_at=_datetime_text(event.created_at),
        )
        return True

    if isinstance(payload, BackgroundJobAbandoned):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.ABANDONED.value,
            abandoned_by=payload.abandoned_by,
            abandoned_reason=payload.reason,
            completed_at=_datetime_text(event.created_at),
        )
        return True

    return False


__all__ = ["_apply_background_job_lifecycle_projection"]
