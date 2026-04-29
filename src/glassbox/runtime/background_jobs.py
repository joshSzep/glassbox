"""Daemon background job runner for bounded local maintenance work."""

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from glassbox.core.events import BackgroundJobCancelled
from glassbox.core.events import BackgroundJobFailed
from glassbox.core.events import BackgroundJobProgressRecorded
from glassbox.core.events import BackgroundJobRecoveryRecorded
from glassbox.core.events import EventEnvelope
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.types import BackgroundJobFailureKind
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import BackgroundJobRecoveryReason
from glassbox.core.types import BackgroundJobState
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.store.artifact_retention import inspect_artifact_state

_READ_ONLY_KINDS = {
    BackgroundJobKind.READ_ONLY_MAINTENANCE,
    BackgroundJobKind.DERIVED_INDEX,
}
_ACTIVE_STATES = (
    BackgroundJobState.CLAIMED,
    BackgroundJobState.RUNNING,
)


@dataclass(frozen=True, slots=True)
class BackgroundJobWorkerTick:
    """Summary of one background worker polling pass."""

    claimed_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    cancelled_count: int = 0
    recovered_stale_count: int = 0


async def run_background_job_worker_loop(
    runtime_context: RuntimeContext,
    *,
    stop_event: asyncio.Event,
    worker_id: str,
    poll_interval_seconds: float = 0.25,
    lease_seconds: int = 60,
) -> None:
    """Run the daemon background job worker until the owner is stopped."""

    while not stop_event.is_set():
        run_background_job_worker_once(
            runtime_context,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)


def run_background_job_worker_once(
    runtime_context: RuntimeContext,
    *,
    worker_id: str,
    lease_seconds: int = 60,
    now: datetime | None = None,
) -> BackgroundJobWorkerTick:
    """Run one bounded worker pass for inspectable read-only background jobs."""

    current_time = now or datetime.now(UTC)
    repository = runtime_context.repositories.sessions
    cancelled_count = _acknowledge_requested_cancellations(
        runtime_context,
        worker_id=worker_id,
    )
    recovered_stale_count = _recover_stale_claims(
        runtime_context,
        worker_id=worker_id,
        now=current_time,
    )
    claimed_count = 0
    completed_count = 0
    failed_count = 0
    lease_expires_at = current_time + timedelta(seconds=lease_seconds)

    for job in repository.list_background_jobs(state=BackgroundJobState.QUEUED):
        if job.kind not in _READ_ONLY_KINDS:
            continue
        claim_token = uuid4().hex
        try:
            claimed = repository.claim_background_job(
                job.job_id,
                worker_id=worker_id,
                claim_token=claim_token,
                lease_expires_at=lease_expires_at,
                now=current_time,
            )
        except ValueError:
            continue
        claimed_count += 1
        try:
            repository.heartbeat_background_job(
                claimed.job_id,
                worker_id=worker_id,
                claim_token=claim_token,
                lease_expires_at=lease_expires_at,
                message="background job runner started",
            )
            _run_read_only_job(runtime_context, claimed, worker_id=worker_id)
            completed_count += 1
        except Exception as exc:
            _fail_job(runtime_context, claimed, exc)
            failed_count += 1

    return BackgroundJobWorkerTick(
        claimed_count=claimed_count,
        completed_count=completed_count,
        failed_count=failed_count,
        cancelled_count=cancelled_count,
        recovered_stale_count=recovered_stale_count,
    )


def _acknowledge_requested_cancellations(
    runtime_context: RuntimeContext,
    *,
    worker_id: str,
) -> int:
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


def _recover_stale_claims(
    runtime_context: RuntimeContext,
    *,
    worker_id: str,
    now: datetime,
) -> int:
    repository = runtime_context.repositories.sessions
    count = 0
    for state in _ACTIVE_STATES:
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


def _run_read_only_job(
    runtime_context: RuntimeContext,
    job: BackgroundJobRecord,
    *,
    worker_id: str,
) -> None:
    workspace_root = runtime_context.infrastructure.artifacts_root
    if job.job_type == "projection-health-refresh":
        _run_projection_health_refresh(runtime_context, job)
        return
    if job.job_type == "artifact-pressure-scan":
        _run_artifact_pressure_scan(runtime_context, workspace_root, job)
        return
    if job.job_type == "provider-evidence-freshness-scan":
        _run_provider_evidence_scan(runtime_context, workspace_root, job)
        return
    if job.job_type == "repository-index-refresh":
        _record_progress(runtime_context, job, "repository index refresh placeholder")
        runtime_context.repositories.sessions.complete_background_job(
            job.job_id,
            summary=(
                "Repository index refresh placeholder completed without mutating "
                "workspace files."
            ),
        )
        return
    raise ValueError(f"unsupported read-only background job type: {job.job_type}")


def _run_projection_health_refresh(
    runtime_context: RuntimeContext, job: BackgroundJobRecord
) -> None:
    repository = runtime_context.repositories.sessions
    sessions = repository.list_sessions()
    degraded_count = 0
    for session in sessions:
        health = repository.inspect_session_projection_health(session.session_id)
        if health.degraded:
            degraded_count += 1
    _record_progress(
        runtime_context,
        job,
        f"inspected projection health for {len(sessions)} session(s)",
    )
    repository.complete_background_job(
        job.job_id,
        summary=(
            f"Projection health refresh inspected {len(sessions)} session(s); "
            f"{degraded_count} degraded."
        ),
    )


def _run_artifact_pressure_scan(
    runtime_context: RuntimeContext,
    workspace_root: Path,
    job: BackgroundJobRecord,
) -> None:
    repository = runtime_context.repositories.sessions
    report = inspect_artifact_state(workspace_root, repository)
    _record_progress(
        runtime_context,
        job,
        f"identified {len(report.candidates)} artifact prune candidate(s)",
    )
    repository.complete_background_job(
        job.job_id,
        summary=(
            f"Artifact pressure scan found {len(report.candidates)} candidate(s), "
            f"{len(report.missing_references)} missing reference(s), and "
            f"{report.candidate_size_bytes} reclaimable byte(s)."
        ),
    )


def _run_provider_evidence_scan(
    runtime_context: RuntimeContext,
    workspace_root: Path,
    job: BackgroundJobRecord,
) -> None:
    evidence = load_provider_canary_evidence(workspace_root)
    _record_progress(
        runtime_context,
        job,
        f"loaded {evidence.summary_count} provider canary summary/summaries",
    )
    runtime_context.repositories.sessions.complete_background_job(
        job.job_id,
        summary=(
            f"Provider evidence freshness scan latest status: {evidence.latest_status}."
        ),
    )


def _record_progress(
    runtime_context: RuntimeContext,
    job: BackgroundJobRecord,
    message: str,
) -> None:
    runtime_context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=job.session_id,
            sequence=0,
            payload=BackgroundJobProgressRecorded(
                job_id=job.job_id,
                message=message,
            ),
        )
    )


def _fail_job(
    runtime_context: RuntimeContext,
    job: BackgroundJobRecord,
    exc: Exception,
) -> None:
    runtime_context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=job.session_id,
            sequence=0,
            payload=BackgroundJobFailed(
                job_id=job.job_id,
                failure_kind=BackgroundJobFailureKind.TOOL_ERROR,
                message=str(exc),
                retryable=False,
                attempt=max(job.attempt, 1),
            ),
        )
    )


__all__ = [
    "BackgroundJobWorkerTick",
    "run_background_job_worker_loop",
    "run_background_job_worker_once",
]
