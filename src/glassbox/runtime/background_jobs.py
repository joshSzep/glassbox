"""Daemon background job runner for bounded local maintenance work."""

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from uuid import uuid4

from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import BackgroundJobState
from glassbox.runtime.background_job_handlers import run_read_only_background_job
from glassbox.runtime.background_job_lifecycle import (
    acknowledge_requested_cancellations,
)
from glassbox.runtime.background_job_lifecycle import (
    recover_stale_background_job_claims,
)
from glassbox.runtime.background_job_records import fail_background_job
from glassbox.runtime.background_task_continuation import (
    run_task_continuation_background_job,
)
from glassbox.runtime.context import RuntimeContext

_READ_ONLY_KINDS = {
    BackgroundJobKind.READ_ONLY_MAINTENANCE,
    BackgroundJobKind.DERIVED_INDEX,
}


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
        await run_background_job_worker_once_async(
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
    cancelled_count = acknowledge_requested_cancellations(
        runtime_context,
        worker_id=worker_id,
    )
    recovered_stale_count = recover_stale_background_job_claims(
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
            run_read_only_background_job(
                runtime_context,
                claimed,
                worker_id=worker_id,
            )
            completed_count += 1
        except Exception as exc:
            fail_background_job(runtime_context, claimed, exc)
            failed_count += 1

    return BackgroundJobWorkerTick(
        claimed_count=claimed_count,
        completed_count=completed_count,
        failed_count=failed_count,
        cancelled_count=cancelled_count,
        recovered_stale_count=recovered_stale_count,
    )


async def run_background_job_worker_once_async(
    runtime_context: RuntimeContext,
    *,
    worker_id: str,
    lease_seconds: int = 60,
    now: datetime | None = None,
) -> BackgroundJobWorkerTick:
    """Run one daemon worker pass, including mutating continuation jobs."""

    tick = run_background_job_worker_once(
        runtime_context,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        now=now,
    )
    current_time = now or datetime.now(UTC)
    repository = runtime_context.repositories.sessions
    lease_expires_at = current_time + timedelta(seconds=lease_seconds)
    claimed_count = 0
    completed_count = 0
    failed_count = 0
    for job in repository.list_background_jobs(state=BackgroundJobState.QUEUED):
        if job.kind != BackgroundJobKind.MUTATING_CONTINUATION:
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
                message="task continuation job runner started",
            )
            await run_task_continuation_background_job(
                runtime_context,
                claimed,
                worker_id=worker_id,
            )
            completed_count += 1
        except Exception as exc:
            fail_background_job(runtime_context, claimed, exc)
            failed_count += 1

    return BackgroundJobWorkerTick(
        claimed_count=tick.claimed_count + claimed_count,
        completed_count=tick.completed_count + completed_count,
        failed_count=tick.failed_count + failed_count,
        cancelled_count=tick.cancelled_count,
        recovered_stale_count=tick.recovered_stale_count,
    )


__all__ = [
    "BackgroundJobWorkerTick",
    "run_background_job_worker_loop",
    "run_background_job_worker_once",
    "run_background_job_worker_once_async",
]
