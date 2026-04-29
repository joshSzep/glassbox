"""Task-plan inspection API routes."""

from typing import Annotated
from typing import cast
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.core.events import BudgetDecisionRecorded
from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskCancelled
from glassbox.core.events import TaskPaused
from glassbox.core.events import TaskResumed
from glassbox.core.events import TaskStatusChanged
from glassbox.core.models import AutonomyBudgetUsage
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import TaskPlanStatus
from glassbox.runtime.budgeting import evaluate_budget
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.web.app import RuntimeContextDep
from glassbox.web.session_api import ActionAcceptedResponse
from glassbox.web.session_api import ErrorDetailResponse
from glassbox.web.session_api import PageInfoResponse
from glassbox.web.task_api import BackgroundJobDetailResponse
from glassbox.web.task_api import TaskActionRequest
from glassbox.web.task_api import TaskBudgetAdjustmentRequest
from glassbox.web.task_api import TaskContinueRequest
from glassbox.web.task_api import TaskDetailResponse
from glassbox.web.task_api import TaskEventPageResponse
from glassbox.web.task_api import TaskListPageResponse
from glassbox.web.task_api import TaskPauseRequest
from glassbox.web.task_api import TaskStepPageResponse
from glassbox.web.task_api import build_background_job_response
from glassbox.web.task_api import build_projection_health_response
from glassbox.web.task_api import build_task_detail_response
from glassbox.web.task_api import build_task_event_responses
from glassbox.web.task_api import build_task_step_responses
from glassbox.web.task_api import build_task_summary_responses

router = APIRouter(prefix="/tasks")

PageCursorParam = Annotated[int, Query(ge=0)]
PageLimitParam = Annotated[int, Query(ge=1, le=500)]
TERMINAL_TASK_STATUSES = {
    TaskPlanStatus.ABANDONED,
    TaskPlanStatus.CANCELLED,
    TaskPlanStatus.COMPLETED,
    TaskPlanStatus.FAILED,
}


def _query_service(context: RuntimeContextDep) -> TaskQueryService:
    return TaskQueryService(cast(TaskPlanRepository, context.repositories.sessions))


def _page_info(
    *,
    cursor: int,
    limit: int,
    returned_count: int,
    next_cursor: int | None,
) -> PageInfoResponse:
    return PageInfoResponse(
        cursor=cursor,
        limit=limit,
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
        returned_count=returned_count,
    )


def _ensure_session_exists(session_id: UUID, context: RuntimeContextDep) -> None:
    if context.repositories.sessions.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")


def _task_record(task_id: UUID, context: RuntimeContextDep):
    record = cast(TaskPlanRepository, context.repositories.sessions).get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"unknown task_id: {task_id}")
    return record


def _ensure_mutable_task(task_id: UUID, context: RuntimeContextDep):
    task = _task_record(task_id, context)
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


def _append_task_event(context: RuntimeContextDep, session_id: UUID, payload) -> None:
    context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=payload,
        )
    )


@router.get("", response_model=TaskListPageResponse)
async def list_task_page(
    context: RuntimeContextDep,
    session_id: UUID | None = None,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> TaskListPageResponse:
    """Return a bounded page of durable task summaries."""

    projection_health = None
    if session_id is not None:
        _ensure_session_exists(session_id, context)
        projection_health = (
            context.repositories.sessions.inspect_session_projection_health(session_id)
        )

    rows = _query_service(context).list_task_summaries(
        session_id=session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return TaskListPageResponse(
        session_id=str(session_id) if session_id is not None else None,
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        projection_health=(
            build_projection_health_response(projection_health)
            if projection_health is not None
            else None
        ),
        items=build_task_summary_responses(items),
    )


@router.get(
    "/{task_id}",
    response_model=TaskDetailResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_task_detail(
    task_id: UUID,
    context: RuntimeContextDep,
) -> TaskDetailResponse:
    """Return projected task detail by task ID."""

    try:
        detail = _query_service(context).get_task_detail(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    projection_health = context.repositories.sessions.inspect_session_projection_health(
        detail.task.session_id
    )
    return build_task_detail_response(detail, projection_health)


@router.get(
    "/{task_id}/steps",
    response_model=TaskStepPageResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_task_step_page(
    task_id: UUID,
    context: RuntimeContextDep,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> TaskStepPageResponse:
    """Return a bounded page of projected task steps."""

    try:
        detail = _query_service(context).get_task_detail(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    steps = detail.steps[cursor : cursor + limit + 1]
    items = steps[:limit]
    next_cursor = cursor + len(items) if len(steps) > limit else None
    projection_health = context.repositories.sessions.inspect_session_projection_health(
        detail.task.session_id
    )
    return TaskStepPageResponse(
        task_id=str(task_id),
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        projection_health=build_projection_health_response(projection_health),
        items=build_task_step_responses(items),
    )


@router.get(
    "/{task_id}/events",
    response_model=TaskEventPageResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_task_event_page(
    task_id: UUID,
    context: RuntimeContextDep,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> TaskEventPageResponse:
    """Return canonical task-plan events after the sequence cursor."""

    try:
        detail = _query_service(context).get_task_detail(task_id)
        rows = _query_service(context).list_task_events(
            task_id,
            after_sequence=cursor,
            limit=limit + 1,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    items = rows[:limit]
    next_cursor = items[-1].sequence if len(rows) > limit and items else None
    projection_health = context.repositories.sessions.inspect_session_projection_health(
        detail.task.session_id
    )
    return TaskEventPageResponse(
        task_id=str(task_id),
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        projection_health=build_projection_health_response(projection_health),
        items=build_task_event_responses(items),
    )


@router.post(
    "/{task_id}/approve-plan",
    response_model=ActionAcceptedResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def approve_task_plan(
    task_id: UUID,
    request: TaskActionRequest,
    context: RuntimeContextDep,
) -> ActionAcceptedResponse:
    """Approve a proposed task plan and mark it active."""

    task = _ensure_mutable_task(task_id, context)
    if task.status != TaskPlanStatus.PROPOSED:
        raise HTTPException(
            status_code=409,
            detail=f"task {task_id} is {task.status.value}, not proposed",
        )
    _append_task_event(
        context,
        task.session_id,
        TaskStatusChanged(
            task_id=task.task_id,
            status=TaskPlanStatus.ACTIVE,
            reason=request.reason or f"plan approved by {request.actor}",
        ),
    )
    return ActionAcceptedResponse(status="ok")


@router.post(
    "/{task_id}/continue",
    response_model=BackgroundJobDetailResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def continue_task(
    task_id: UUID,
    request: TaskContinueRequest,
    context: RuntimeContextDep,
) -> BackgroundJobDetailResponse:
    """Start a bounded background continuation job for one task."""

    task = _ensure_mutable_task(task_id, context)
    job = context.repositories.sessions.enqueue_background_job(
        task.session_id,
        kind=BackgroundJobKind.MUTATING_CONTINUATION,
        job_type="task-continuation-step",
        title=f"Continue task: {task.title}",
        requested_by=request.requested_by,
        payload={
            "reason": request.reason,
            "task_id": str(task.task_id),
            "verify_repair": request.verify_repair,
        },
        task_id=task.task_id,
    )
    return BackgroundJobDetailResponse(job=build_background_job_response(job))


@router.post(
    "/{task_id}/pause",
    response_model=ActionAcceptedResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def pause_task(
    task_id: UUID,
    request: TaskPauseRequest,
    context: RuntimeContextDep,
) -> ActionAcceptedResponse:
    """Pause one mutable task."""

    task = _ensure_mutable_task(task_id, context)
    _append_task_event(
        context,
        task.session_id,
        TaskPaused(task_id=task.task_id, reason=request.reason, detail=request.detail),
    )
    return ActionAcceptedResponse(status="ok")


@router.post(
    "/{task_id}/resume",
    response_model=ActionAcceptedResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def resume_task(
    task_id: UUID,
    request: TaskActionRequest,
    context: RuntimeContextDep,
) -> ActionAcceptedResponse:
    """Resume one paused task."""

    task = _ensure_mutable_task(task_id, context)
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


@router.post(
    "/{task_id}/cancel",
    response_model=ActionAcceptedResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def cancel_task(
    task_id: UUID,
    request: TaskActionRequest,
    context: RuntimeContextDep,
) -> ActionAcceptedResponse:
    """Cancel one mutable task."""

    task = _ensure_mutable_task(task_id, context)
    _append_task_event(
        context,
        task.session_id,
        TaskCancelled(
            task_id=task.task_id,
            requested_by=request.actor,
            reason=request.reason,
        ),
    )
    return ActionAcceptedResponse(status="ok")


@router.post(
    "/{task_id}/budget",
    response_model=ActionAcceptedResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def adjust_task_budget(
    task_id: UUID,
    request: TaskBudgetAdjustmentRequest,
    context: RuntimeContextDep,
) -> ActionAcceptedResponse:
    """Record an operator-approved task budget adjustment."""

    task = _ensure_mutable_task(task_id, context)
    current_posture = context.repositories.sessions.get_budget_posture(
        task.session_id,
        task_id=task.task_id,
    )
    usage = (
        current_posture.usage if current_posture is not None else AutonomyBudgetUsage()
    )
    evaluation = evaluate_budget(request.budget, usage)
    _append_task_event(
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
