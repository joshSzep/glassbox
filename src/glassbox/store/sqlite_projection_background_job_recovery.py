"""Background-job recovery and retry projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import BackgroundJobRecoveryRecorded
from glassbox.core.events import BackgroundJobRetryExhausted
from glassbox.core.events import BackgroundJobRetryRequested
from glassbox.core.events import EventEnvelope
from glassbox.core.types import BackgroundJobState
from glassbox.store.sqlite_projection_background_job_common import _update_job


def _apply_background_job_recovery_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> bool:
    payload = event.payload
    if isinstance(payload, BackgroundJobRecoveryRecorded):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.STALE.value,
            recovery_reason=payload.reason.value,
            recovery_detail=payload.detail,
        )
        return True

    if isinstance(payload, BackgroundJobRetryRequested):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.QUEUED.value,
            worker_id=None,
            claim_token=None,
            lease_expires_at=None,
            last_heartbeat_at=None,
            started_at=None,
            completed_at=None,
            progress_message=None,
            failure_kind=None,
            failure_message=None,
            failure_artifact_id=None,
            failure_artifact_path=None,
            retryable=0,
            next_retry_at=None,
            retry_requested_by=payload.requested_by,
            retry_reason=payload.reason,
            retry_exhausted_reason=None,
            retry_budget=None,
            abandoned_by=None,
            abandoned_reason=None,
        )
        return True

    if isinstance(payload, BackgroundJobRetryExhausted):
        _update_job(
            connection,
            payload.job_id,
            event,
            retry_budget=payload.retry_budget,
            retry_exhausted_reason=payload.reason,
        )
        return True

    return False


__all__ = ["_apply_background_job_recovery_projection"]
