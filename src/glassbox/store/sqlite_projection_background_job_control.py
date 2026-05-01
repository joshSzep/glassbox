"""Background-job pause and cancellation projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import BackgroundJobCancellationRequested
from glassbox.core.events import BackgroundJobCancelled
from glassbox.core.events import BackgroundJobPaused
from glassbox.core.events import EventEnvelope
from glassbox.core.types import BackgroundJobState
from glassbox.store.sqlite_projection_background_job_common import _datetime_text
from glassbox.store.sqlite_projection_background_job_common import _update_job


def _apply_background_job_control_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> bool:
    payload = event.payload
    if isinstance(payload, BackgroundJobPaused):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.PAUSED.value,
            progress_message=payload.detail or payload.reason.value,
        )
        return True

    if isinstance(payload, BackgroundJobCancellationRequested):
        _update_job(
            connection,
            payload.job_id,
            event,
            state=BackgroundJobState.CANCELLATION_REQUESTED.value,
            cancellation_requested_by=payload.requested_by,
            cancellation_reason=payload.reason,
        )
        return True

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
        return True

    return False


__all__ = ["_apply_background_job_control_projection"]
