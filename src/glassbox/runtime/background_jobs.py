"""Daemon background job runner for bounded local maintenance work."""

import asyncio
import traceback
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import cast
from uuid import UUID
from uuid import uuid4

from glassbox.core.events import BackgroundJobCancelled
from glassbox.core.events import BackgroundJobFailed
from glassbox.core.events import BackgroundJobProgressRecorded
from glassbox.core.events import BackgroundJobRecoveryRecorded
from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionStarted
from glassbox.core.events import TaskPaused
from glassbox.core.events import TaskStatusChanged
from glassbox.core.events import TaskStepCompleted
from glassbox.core.events import TaskStepStarted
from glassbox.core.ids import TaskId
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.models import TaskRecord
from glassbox.core.models import TaskStepRecord
from glassbox.core.types import AutonomyMode
from glassbox.core.types import BackgroundJobFailureKind
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import BackgroundJobRecoveryReason
from glassbox.core.types import BackgroundJobState
from glassbox.core.types import SessionStatus
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.workspace_memory_capture import MemoryExtractionPolicy
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureRepository
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureService
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
            await _run_task_continuation_job(
                runtime_context,
                claimed,
                worker_id=worker_id,
            )
            completed_count += 1
        except Exception as exc:
            _fail_job(runtime_context, claimed, exc)
            failed_count += 1

    return BackgroundJobWorkerTick(
        claimed_count=tick.claimed_count + claimed_count,
        completed_count=tick.completed_count + completed_count,
        failed_count=tick.failed_count + failed_count,
        cancelled_count=tick.cancelled_count,
        recovered_stale_count=tick.recovered_stale_count,
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
        snapshot = build_and_write_repository_index(workspace_root)
        index_path = repository_index_path(workspace_root)
        _record_progress(
            runtime_context,
            job,
            f"repository index refreshed {len(snapshot.entries)} entries",
        )
        runtime_context.repositories.sessions.complete_background_job(
            job.job_id,
            summary=(
                f"Repository index refresh wrote {len(snapshot.entries)} entries "
                f"to {index_path}."
            ),
        )
        return
    if job.job_type == "workspace-memory-candidate-scan":
        payload = job.payload or {}
        session_id_value = payload.get("session_id")
        if session_id_value is None:
            raise ValueError("workspace-memory-candidate-scan requires session_id")
        session_id = UUID(str(session_id_value))
        limit_value = payload.get("max_candidates")
        max_candidates = 25
        if isinstance(limit_value, int | str):
            max_candidates = int(limit_value)
        candidates = WorkspaceMemoryCaptureService(
            cast(
                WorkspaceMemoryCaptureRepository, runtime_context.repositories.sessions
            )
        ).list_candidates(
            session_id,
            policy=MemoryExtractionPolicy(max_candidates=max_candidates),
        )
        _record_progress(
            runtime_context,
            job,
            f"workspace memory scan found {len(candidates)} candidate(s)",
        )
        runtime_context.repositories.sessions.complete_background_job(
            job.job_id,
            summary=(
                f"Workspace memory candidate scan found {len(candidates)} "
                "review-gated candidate(s)."
            ),
        )
        return
    raise ValueError(f"unsupported read-only background job type: {job.job_type}")


async def _run_task_continuation_job(
    runtime_context: RuntimeContext,
    job: BackgroundJobRecord,
    *,
    worker_id: str,
) -> None:
    if job.job_type != "task-continuation-step":
        raise ValueError(f"unsupported task continuation job type: {job.job_type}")

    repository = runtime_context.repositories.sessions
    task_repository = cast(TaskPlanRepository, repository)
    task_id = _task_id_for_job(job)
    task = task_repository.get_task(task_id)
    if task is None:
        raise ValueError(f"unknown task_id for continuation job: {task_id}")
    if task.session_id != job.session_id:
        raise ValueError("task continuation job session_id does not match task")

    pause_reason = _blocked_reason_for_session(runtime_context, task)
    if pause_reason is not None:
        _pause_task(runtime_context, task, pause_reason)
        repository.complete_background_job(
            job.job_id,
            summary=f"Task continuation paused: {pause_reason.value}.",
        )
        return

    if not _session_has_explicit_autonomy_budget(repository, task.session_id):
        _pause_task(
            runtime_context,
            task,
            TaskBlockedReason.BUDGET_EXHAUSTED,
            detail=(
                "Background task continuation requires an explicit autonomy mode "
                "and budget."
            ),
        )
        repository.complete_background_job(
            job.job_id,
            summary="Task continuation paused until autonomy budget is explicit.",
        )
        return

    if task.status in {
        TaskPlanStatus.COMPLETED,
        TaskPlanStatus.CANCELLED,
        TaskPlanStatus.ABANDONED,
        TaskPlanStatus.FAILED,
    }:
        repository.complete_background_job(
            job.job_id,
            summary=f"Task continuation skipped because task is {task.status.value}.",
        )
        return

    next_step = _next_pending_step(runtime_context, task)
    if next_step is None:
        _change_task_status(
            runtime_context,
            task,
            TaskPlanStatus.COMPLETED,
            reason="all task steps are complete",
        )
        repository.complete_background_job(
            job.job_id,
            summary="Task continuation completed all pending steps.",
        )
        return

    _record_progress(
        runtime_context,
        job,
        f"continuing task step {next_step.order}: {next_step.title}",
    )
    repository.append_event(
        EventEnvelope(
            session_id=task.session_id,
            sequence=0,
            payload=TaskStepStarted(task_id=task.task_id, step_id=next_step.step_id),
        )
    )
    await runtime_context.services.session_service.submit_user_message(
        task.session_id,
        _continuation_prompt(task, next_step),
    )

    pause_reason = _blocked_reason_for_session(runtime_context, task)
    if pause_reason is not None:
        _pause_task(runtime_context, task, pause_reason)
        repository.complete_background_job(
            job.job_id,
            summary=f"Task continuation stopped at {pause_reason.value}.",
        )
        return

    repository.append_event(
        EventEnvelope(
            session_id=task.session_id,
            sequence=0,
            payload=TaskStepCompleted(
                task_id=task.task_id,
                step_id=next_step.step_id,
                summary="Completed one bounded background continuation turn.",
            ),
        )
    )

    remaining_steps = [
        step
        for step in task_repository.list_task_steps(task.session_id, task.task_id)
        if step.step_id != next_step.step_id and step.status == TaskStepStatus.PENDING
    ]
    if not remaining_steps:
        _change_task_status(
            runtime_context,
            task,
            TaskPlanStatus.COMPLETED,
            reason="all task steps are complete",
        )
    repository.complete_background_job(
        job.job_id,
        summary=(
            f"Task continuation completed step {next_step.order}: {next_step.title}."
        ),
    )


def _task_id_for_job(job: BackgroundJobRecord) -> TaskId:
    if job.task_id is not None:
        return job.task_id
    value = job.payload.get("task_id")
    if isinstance(value, str):
        return UUID(value)
    raise ValueError("task continuation job payload must include task_id")


def _blocked_reason_for_session(
    runtime_context: RuntimeContext,
    task: TaskRecord,
) -> TaskBlockedReason | None:
    state = runtime_context.repositories.sessions.get_session_state(task.session_id)
    if state is None:
        return TaskBlockedReason.UNKNOWN
    if state.status == SessionStatus.AWAITING_APPROVAL:
        return TaskBlockedReason.AWAITING_APPROVAL
    if state.status == SessionStatus.AWAITING_USER_INPUT:
        return TaskBlockedReason.AWAITING_USER_INPUT
    if state.status == SessionStatus.FAILED:
        return TaskBlockedReason.PROVIDER_UNAVAILABLE
    if state.status == SessionStatus.CANCELLED:
        return TaskBlockedReason.CANCELLED
    return None


def _session_has_explicit_autonomy_budget(repository, session_id) -> bool:
    for event in repository.read_session_events(session_id):
        payload = event.payload
        if not isinstance(payload, SessionStarted):
            continue
        if payload.autonomy_mode in (None, AutonomyMode.MANUAL):
            return False
        return payload.autonomy_budget is not None or payload.autonomy_budget_preset
    return False


def _next_pending_step(
    runtime_context: RuntimeContext,
    task: TaskRecord,
) -> TaskStepRecord | None:
    pending_steps = [
        step
        for step in cast(
            TaskPlanRepository,
            runtime_context.repositories.sessions,
        ).list_task_steps(
            task.session_id,
            task.task_id,
        )
        if step.status == TaskStepStatus.PENDING
    ]
    if not pending_steps:
        return None
    return sorted(pending_steps, key=lambda step: step.order)[0]


def _pause_task(
    runtime_context: RuntimeContext,
    task: TaskRecord,
    reason: TaskBlockedReason,
    *,
    detail: str | None = None,
) -> None:
    runtime_context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=task.session_id,
            sequence=0,
            payload=TaskPaused(
                task_id=task.task_id,
                reason=reason,
                detail=detail or f"Task continuation stopped at {reason.value}.",
            ),
        )
    )


def _change_task_status(
    runtime_context: RuntimeContext,
    task: TaskRecord,
    status: TaskPlanStatus,
    *,
    reason: str,
) -> None:
    runtime_context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=task.session_id,
            sequence=0,
            payload=TaskStatusChanged(
                task_id=task.task_id,
                status=status,
                reason=reason,
            ),
        )
    )


def _continuation_prompt(task: TaskRecord, step: TaskStepRecord) -> str:
    detail = f"\nStep detail: {step.description}" if step.description else ""
    return (
        f"Continue task '{task.title}' with one bounded background step.\n"
        f"Goal: {task.goal}\n"
        f"Step {step.order}: {step.title}{detail}\n"
        "Stop after this step if approval, user input, policy, budget, or "
        "verification blocks further progress."
    )


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
    failure_artifact_id = None
    failure_artifact_path = None
    with suppress(Exception):
        artifact = runtime_context.repositories.artifacts.write_text_artifact(
            job.session_id,
            _failure_artifact_content(job, exc),
            suffix="background-job-failure.txt",
        )
        failure_artifact_id = artifact.artifact_id
        failure_artifact_path = artifact.relative_path.as_posix()
    runtime_context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=job.session_id,
            sequence=0,
            payload=BackgroundJobFailed(
                job_id=job.job_id,
                failure_kind=BackgroundJobFailureKind.TOOL_ERROR,
                message=str(exc),
                retryable=job.kind != BackgroundJobKind.MUTATING_CONTINUATION,
                attempt=max(job.attempt, 1),
                artifact_id=failure_artifact_id,
                artifact_path=failure_artifact_path,
            ),
        )
    )


def _failure_artifact_content(job: BackgroundJobRecord, exc: Exception) -> str:
    traceback_text = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    return (
        f"Background job failure\n"
        f"job_id: {job.job_id}\n"
        f"session_id: {job.session_id}\n"
        f"kind: {job.kind.value}\n"
        f"job_type: {job.job_type}\n"
        f"attempt: {max(job.attempt, 1)}\n"
        f"failure_kind: {BackgroundJobFailureKind.TOOL_ERROR.value}\n\n"
        f"{traceback_text}"
    )


__all__ = [
    "BackgroundJobWorkerTick",
    "run_background_job_worker_loop",
    "run_background_job_worker_once",
    "run_background_job_worker_once_async",
]
