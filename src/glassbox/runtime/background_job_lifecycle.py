"""Lease, recovery, and cancellation helpers for background job workers."""

from datetime import UTC
from datetime import datetime

from glassbox.core.events import BackgroundJobCancelled
from glassbox.core.events import BackgroundJobRecoveryRecorded
from glassbox.core.events import EventEnvelope
from glassbox.core.types import BackgroundJobRecoveryReason
from glassbox.core.types import BackgroundJobState
from glassbox.runtime.context import RuntimeContext

ACTIVE_BACKGROUND_JOB_STATES = (
    BackgroundJobState.CLAIMED,
    BackgroundJobState.RUNNING,
)


def acknowledge_requested_cancellations(
    runtime_context: RuntimeContext,
    *,
    worker_id: str,
) -> int:
    """Acknowledge operator-requested cancellations for queued worker passes."""

    repository = runtime_context.repositories.sessions
    count = 0
    for job in repository.list_background_jobs(
        state=BackgroundJobState.CANCELLATION_REQUESTED
    ):
        repository.append_event(
            EventEnvelope(
                session_id=job.session_id,
                sequence=0,
                payload=BackgroundJobCancelled(
                    job_id=job.job_id,
                    cancelled_by=worker_id,
                    reason=job.cancellation_reason or "operator requested cancellation",
                ),
            )
        )
        count += 1
    return count


def recover_stale_background_job_claims(
    runtime_context: RuntimeContext,
    *,
    worker_id: str,
    now: datetime,
) -> int:
    """Mark active background jobs stale when their leases have expired."""

    repository = runtime_context.repositories.sessions
    count = 0
    for state in ACTIVE_BACKGROUND_JOB_STATES:
        for job in repository.list_background_jobs(state=state):
            lease_expires_at = job.lease_expires_at
            if lease_expires_at is None:
                continue
            if lease_expires_at.tzinfo is None:
                lease_expires_at = lease_expires_at.replace(tzinfo=UTC)
            if lease_expires_at > now:
                continue
            repository.append_event(
                EventEnvelope(
                    session_id=job.session_id,
                    sequence=0,
                    payload=BackgroundJobRecoveryRecorded(
                        job_id=job.job_id,
                        reason=BackgroundJobRecoveryReason.STALE_CLAIM,
                        previous_state=job.state,
                        recovered_by=worker_id,
                        detail="background job lease expired before daemon heartbeat",
                    ),
                )
            )
            count += 1
    return count


__all__ = [
    "ACTIVE_BACKGROUND_JOB_STATES",
    "acknowledge_requested_cancellations",
    "recover_stale_background_job_claims",
]
