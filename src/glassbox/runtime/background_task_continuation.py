"""Mutating task continuation background job handling."""

from typing import cast
from uuid import UUID

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
from glassbox.core.types import SessionStatus
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.runtime.background_job_records import record_background_job_progress
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.task_queries import TaskPlanRepository


async def run_task_continuation_background_job(
    runtime_context: RuntimeContext,
    job: BackgroundJobRecord,
    *,
    worker_id: str,
) -> None:
    """Run one bounded mutating task continuation job."""

    del worker_id
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

    record_background_job_progress(
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


__all__ = ["run_task_continuation_background_job"]
