"""HTTP-local mutation helpers for task routes."""

from datetime import UTC
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import HTTPException

from glassbox.core.events import BudgetDecisionRecorded
from glassbox.core.events import EventEnvelope
from glassbox.core.events import EventPayloadType
from glassbox.core.events import TaskCancelled
from glassbox.core.events import TaskPaused
from glassbox.core.events import TaskResumed
from glassbox.core.events import TaskStatusChanged
from glassbox.core.models import AutonomyBudgetUsage
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import TaskPlanStatus
from glassbox.runtime.budgeting import evaluate_budget
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.continuation_windows import active_continuation_window_job
from glassbox.runtime.continuation_windows import approve_continuation_window
from glassbox.runtime.continuation_windows import deny_continuation_window
from glassbox.runtime.pause_windows import cancel_pause_window
from glassbox.runtime.pause_windows import schedule_pause_window
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.web.session_api import ActionAcceptedResponse
from glassbox.web.task_api import BackgroundJobDetailResponse
from glassbox.web.task_api import ContinuationWindowResponse
from glassbox.web.task_api import TaskActionRequest
from glassbox.web.task_api import TaskBudgetAdjustmentRequest
from glassbox.web.task_api import TaskContinuationWindowActionResponse
from glassbox.web.task_api import TaskContinuationWindowRequest
from glassbox.web.task_api import TaskContinueRequest
from glassbox.web.task_api import TaskPauseRequest
from glassbox.web.task_api import TaskPauseWindowCancelRequest
from glassbox.web.task_api import TaskPauseWindowRequest
from glassbox.web.task_api import TaskPauseWindowResponse
from glassbox.web.task_api import build_background_job_response

TERMINAL_TASK_STATUSES = {
    TaskPlanStatus.ABANDONED,
    TaskPlanStatus.CANCELLED,
    TaskPlanStatus.COMPLETED,
    TaskPlanStatus.FAILED,
}


def task_record(task_id: UUID, context: RuntimeContext):
    record = cast(TaskPlanRepository, context.repositories.sessions).get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"unknown task_id: {task_id}")
    return record


def ensure_mutable_task(task_id: UUID, context: RuntimeContext):
    task = task_record(task_id, context)
    if task.status in TERMINAL_TASK_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"task {task_id} is already {task.status.value}",
        )
    projection_health = context.repositories.sessions.inspect_session_projection_health(
        task.session_id
    )
    if projection_health.degraded or projection_health.state != "ok":
        raise HTTPException(
            status_code=409,
            detail=(
                "task projection is stale or unavailable; refresh/rebuild before "
                "mutating autonomous work"
            ),
        )
    return task


def append_task_event(
    context: RuntimeContext,
    session_id: UUID,
    payload: EventPayloadType,
) -> None:
    context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=payload,
        )
    )


def parse_optional_uuid(value: str | None, *, field_name: str) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be a valid UUID",
        ) from exc


def approve_task_plan_response(
    task_id: UUID,
    request: TaskActionRequest,
    context: RuntimeContext,
) -> ActionAcceptedResponse:
    task = ensure_mutable_task(task_id, context)
    if task.status != TaskPlanStatus.PROPOSED:
        raise HTTPException(
            status_code=409,
            detail=f"task {task_id} is {task.status.value}, not proposed",
        )
    append_task_event(
        context,
        task.session_id,
        TaskStatusChanged(
            task_id=task.task_id,
            status=TaskPlanStatus.ACTIVE,
            reason=request.reason or f"plan approved by {request.actor}",
        ),
    )
    return ActionAcceptedResponse(status="ok")


def continue_task_response(
    task_id: UUID,
    request: TaskContinueRequest,
    context: RuntimeContext,
) -> BackgroundJobDetailResponse:
    task = ensure_mutable_task(task_id, context)
    payload: dict[str, object] = {
        "reason": request.reason,
        "task_id": str(task.task_id),
        "verify_repair": request.verify_repair,
    }
    now = datetime.now(UTC)
    if request.continue_for_minutes is not None:
        active_window_job = active_continuation_window_job(
            context.repositories.sessions.list_background_jobs(),
            task_id=task.task_id,
            now=now,
        )
        if active_window_job is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "task already has an active bounded continuation window "
                    f"on job {active_window_job.job_id}"
                ),
            )
        approval = approve_continuation_window(
            task_id=task.task_id,
            minutes=request.continue_for_minutes,
            requested_by=request.requested_by,
            decided_by=request.actor,
            reason=request.reason,
            checkpoint_id=parse_optional_uuid(
                request.checkpoint_id,
                field_name="checkpoint_id",
            ),
            now=now,
        )
        context.repositories.sessions.append_events(
            [
                EventEnvelope(
                    session_id=task.session_id,
                    sequence=0,
                    payload=approval.requested_event,
                ),
                EventEnvelope(
                    session_id=task.session_id,
                    sequence=0,
                    payload=approval.resolved_event,
                ),
            ]
        )
        payload.update(approval.payload)
    job = context.repositories.sessions.enqueue_background_job(
        task.session_id,
        kind=BackgroundJobKind.MUTATING_CONTINUATION,
        job_type="task-continuation-step",
        title=f"Continue task: {task.title}",
        requested_by=request.requested_by,
        payload=payload,
        task_id=task.task_id,
    )
    return BackgroundJobDetailResponse(job=build_background_job_response(job))


def resolve_task_continuation_window_response(
    task_id: UUID,
    request: TaskContinuationWindowRequest,
    context: RuntimeContext,
) -> TaskContinuationWindowActionResponse:
    task = ensure_mutable_task(task_id, context)
    checkpoint_id = parse_optional_uuid(
        request.checkpoint_id, field_name="checkpoint_id"
    )
    if request.decision == ApprovalDecision.DENIED:
        denial = deny_continuation_window(
            task_id=task.task_id,
            minutes=request.requested_minutes,
            requested_by=request.requested_by,
            decided_by=request.decided_by,
            reason=request.reason,
            checkpoint_id=checkpoint_id,
        )
        context.repositories.sessions.append_events(
            [
                EventEnvelope(
                    session_id=task.session_id,
                    sequence=0,
                    payload=denial.requested_event,
                ),
                EventEnvelope(
                    session_id=task.session_id,
                    sequence=0,
                    payload=denial.resolved_event,
                ),
            ]
        )
        return TaskContinuationWindowActionResponse(
            status="denied",
            continuation_window=ContinuationWindowResponse(
                approval_id=str(denial.approval_id),
                decision=ApprovalDecision.DENIED.value,
                requested_minutes=request.requested_minutes,
                checkpoint_id=request.checkpoint_id,
            ),
            job=None,
        )

    now = datetime.now(UTC)
    active_window_job = active_continuation_window_job(
        context.repositories.sessions.list_background_jobs(),
        task_id=task.task_id,
        now=now,
    )
    if active_window_job is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "task already has an active bounded continuation window "
                f"on job {active_window_job.job_id}"
            ),
        )
    approval = approve_continuation_window(
        task_id=task.task_id,
        minutes=request.requested_minutes,
        requested_by=request.requested_by,
        decided_by=request.decided_by,
        reason=request.reason,
        checkpoint_id=checkpoint_id,
        now=now,
    )
    context.repositories.sessions.append_events(
        [
            EventEnvelope(
                session_id=task.session_id,
                sequence=0,
                payload=approval.requested_event,
            ),
            EventEnvelope(
                session_id=task.session_id,
                sequence=0,
                payload=approval.resolved_event,
            ),
        ]
    )
    payload: dict[str, object] = {
        "reason": request.reason,
        "task_id": str(task.task_id),
        "verify_repair": request.verify_repair,
    }
    payload.update(approval.payload)
    job = context.repositories.sessions.enqueue_background_job(
        task.session_id,
        kind=BackgroundJobKind.MUTATING_CONTINUATION,
        job_type="task-continuation-step",
        title=f"Continue task for {request.requested_minutes} minutes: {task.title}",
        requested_by=request.requested_by,
        payload=payload,
        task_id=task.task_id,
    )
    return TaskContinuationWindowActionResponse(
        status="approved",
        continuation_window=ContinuationWindowResponse(
            approval_id=str(approval.approval_id),
            decision=ApprovalDecision.APPROVED.value,
            requested_minutes=request.requested_minutes,
            approved_until=approval.approved_until,
            checkpoint_id=request.checkpoint_id,
        ),
        job=build_background_job_response(job),
    )


def schedule_task_pause_window_response(
    task_id: UUID,
    request: TaskPauseWindowRequest,
    context: RuntimeContext,
) -> TaskPauseWindowResponse:
    task = ensure_mutable_task(task_id, context)
    checkpoint_id = parse_optional_uuid(
        request.checkpoint_id,
        field_name="checkpoint_id",
    )
    try:
        event = schedule_pause_window(
            scope="task",
            task_id=task.task_id,
            policy=request.policy,
            scheduled_by=request.actor,
            reason=request.reason or f"pause window scheduled by {request.actor}",
            checkpoint_id=checkpoint_id,
            pause_before=request.pause_before,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    append_task_event(context, task.session_id, event)
    return TaskPauseWindowResponse(
        pause_window_id=str(event.pause_window_id),
        policy=event.policy.value,
        reason=event.reason,
        pause_before=event.pause_before,
        checkpoint_id=(
            str(event.checkpoint_id) if event.checkpoint_id is not None else None
        ),
    )


def cancel_task_pause_window_response(
    task_id: UUID,
    pause_window_id: UUID,
    request: TaskPauseWindowCancelRequest,
    context: RuntimeContext,
) -> TaskPauseWindowResponse:
    task = ensure_mutable_task(task_id, context)
    event = cancel_pause_window(
        pause_window_id=pause_window_id,
        task_id=task.task_id,
        cancelled_by=request.actor,
        reason=request.reason,
    )
    append_task_event(context, task.session_id, event)
    return TaskPauseWindowResponse(
        pause_window_id=str(event.pause_window_id),
        reason=event.reason,
        status="cancelled",
    )


def pause_task_response(
    task_id: UUID,
    request: TaskPauseRequest,
    context: RuntimeContext,
) -> ActionAcceptedResponse:
    task = ensure_mutable_task(task_id, context)
    append_task_event(
        context,
        task.session_id,
        TaskPaused(task_id=task.task_id, reason=request.reason, detail=request.detail),
    )
    return ActionAcceptedResponse(status="ok")


def resume_task_response(
    task_id: UUID,
    request: TaskActionRequest,
    context: RuntimeContext,
) -> ActionAcceptedResponse:
    task = ensure_mutable_task(task_id, context)
    if task.status != TaskPlanStatus.PAUSED:
        raise HTTPException(
            status_code=409,
            detail=f"task {task_id} is {task.status.value}, not paused",
        )
    context.repositories.sessions.append_events(
        [
            EventEnvelope(
                session_id=task.session_id,
                sequence=0,
                payload=TaskResumed(task_id=task.task_id, resumed_by=request.actor),
            ),
            EventEnvelope(
                session_id=task.session_id,
                sequence=0,
                payload=TaskStatusChanged(
                    task_id=task.task_id,
                    status=TaskPlanStatus.ACTIVE,
                    reason=request.reason or f"resumed by {request.actor}",
                ),
            ),
        ]
    )
    return ActionAcceptedResponse(status="ok")


def cancel_task_response(
    task_id: UUID,
    request: TaskActionRequest,
    context: RuntimeContext,
) -> ActionAcceptedResponse:
    task = ensure_mutable_task(task_id, context)
    append_task_event(
        context,
        task.session_id,
        TaskCancelled(
            task_id=task.task_id,
            requested_by=request.actor,
            reason=request.reason,
        ),
    )
    return ActionAcceptedResponse(status="ok")


def adjust_task_budget_response(
    task_id: UUID,
    request: TaskBudgetAdjustmentRequest,
    context: RuntimeContext,
) -> ActionAcceptedResponse:
    task = ensure_mutable_task(task_id, context)
    current_posture = context.repositories.sessions.get_budget_posture(
        task.session_id,
        task_id=task.task_id,
    )
    usage = (
        current_posture.usage if current_posture is not None else AutonomyBudgetUsage()
    )
    evaluation = evaluate_budget(request.budget, usage)
    append_task_event(
        context,
        task.session_id,
        BudgetDecisionRecorded(
            scope="task",
            mode=request.mode,
            budget=request.budget,
            usage=evaluation.usage,
            remaining=evaluation.remaining,
            decision="allowed",
            task_id=task.task_id,
            detail=(
                request.detail
                or request.reason
                or f"budget adjusted by {request.actor}"
            ),
        ),
    )
    return ActionAcceptedResponse(status="ok")
