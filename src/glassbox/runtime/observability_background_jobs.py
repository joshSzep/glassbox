"""Background job queue observability collector."""

from glassbox.core.types import BackgroundJobState
from glassbox.runtime.observability_models import BackgroundJobObservability
from glassbox.services import SessionRepository


def build_background_job_observability(
    session_repository: SessionRepository,
) -> BackgroundJobObservability:
    counts = session_repository.count_background_jobs_by_state()
    pending_count = counts.get("queued", 0) + counts.get(
        "cancellation_requested",
        0,
    )
    running_count = counts.get("claimed", 0) + counts.get("running", 0)
    stale_count = counts.get("stale", 0)
    failed_count = counts.get("failed", 0)
    abandoned_count = counts.get("abandoned", 0)
    last_failure = session_repository.latest_failed_background_job()
    retryable_count = len(
        [
            job
            for job in session_repository.list_background_jobs(
                state=BackgroundJobState.FAILED
            )
            if job.retryable
        ]
    )
    next_actions: list[str] = []
    if pending_count:
        next_actions.append("glassbox job list --state queued")
    if running_count:
        next_actions.append("glassbox job list --state running")
    if stale_count:
        next_actions.append("glassbox job list --state stale")
    if retryable_count:
        next_actions.append("glassbox job list --state failed")
    if last_failure is not None:
        next_actions.append(f"glassbox job show {last_failure.job_id}")
    return BackgroundJobObservability(
        pending_count=pending_count,
        running_count=running_count,
        stale_count=stale_count,
        failed_count=failed_count,
        retryable_count=retryable_count,
        abandoned_count=abandoned_count,
        last_failure_job_id=(str(last_failure.job_id) if last_failure else None),
        last_failure_message=(last_failure.failure_message if last_failure else None),
        next_actions=next_actions,
    )


__all__ = ["build_background_job_observability"]
