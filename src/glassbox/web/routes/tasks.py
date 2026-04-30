"""Task-plan inspection API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Query

from glassbox.web.app import RuntimeContextDep
from glassbox.web.routes.task_route_actions import adjust_task_budget_response
from glassbox.web.routes.task_route_actions import approve_task_plan_response
from glassbox.web.routes.task_route_actions import cancel_task_pause_window_response
from glassbox.web.routes.task_route_actions import cancel_task_response
from glassbox.web.routes.task_route_actions import continue_task_response
from glassbox.web.routes.task_route_actions import pause_task_response
from glassbox.web.routes.task_route_actions import (
    resolve_task_continuation_window_response,
)
from glassbox.web.routes.task_route_actions import resume_task_response
from glassbox.web.routes.task_route_actions import schedule_task_pause_window_response
from glassbox.web.routes.task_route_queries import get_task_detail_response
from glassbox.web.routes.task_route_queries import get_task_event_page_response
from glassbox.web.routes.task_route_queries import get_task_step_page_response
from glassbox.web.routes.task_route_queries import list_task_page_response
from glassbox.web.session_api import ActionAcceptedResponse
from glassbox.web.session_api import ErrorDetailResponse
from glassbox.web.task_api import BackgroundJobDetailResponse
from glassbox.web.task_api import TaskActionRequest
from glassbox.web.task_api import TaskBudgetAdjustmentRequest
from glassbox.web.task_api import TaskContinuationWindowActionResponse
from glassbox.web.task_api import TaskContinuationWindowRequest
from glassbox.web.task_api import TaskContinueRequest
from glassbox.web.task_api import TaskDetailResponse
from glassbox.web.task_api import TaskEventPageResponse
from glassbox.web.task_api import TaskListPageResponse
from glassbox.web.task_api import TaskPauseRequest
from glassbox.web.task_api import TaskPauseWindowCancelRequest
from glassbox.web.task_api import TaskPauseWindowRequest
from glassbox.web.task_api import TaskPauseWindowResponse
from glassbox.web.task_api import TaskStepPageResponse

router = APIRouter(prefix="/tasks")

PageCursorParam = Annotated[int, Query(ge=0)]
PageLimitParam = Annotated[int, Query(ge=1, le=500)]


@router.get("", response_model=TaskListPageResponse)
async def list_task_page(
    context: RuntimeContextDep,
    session_id: UUID | None = None,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> TaskListPageResponse:
    """Return a bounded page of durable task summaries."""

    return list_task_page_response(
        context,
        session_id=session_id,
        cursor=cursor,
        limit=limit,
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

    return get_task_detail_response(task_id, context)


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

    return get_task_step_page_response(
        task_id,
        context,
        cursor=cursor,
        limit=limit,
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

    return get_task_event_page_response(
        task_id,
        context,
        cursor=cursor,
        limit=limit,
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

    return approve_task_plan_response(task_id, request, context)


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

    return continue_task_response(task_id, request, context)


@router.post(
    "/{task_id}/continuation-window",
    response_model=TaskContinuationWindowActionResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def resolve_task_continuation_window(
    task_id: UUID,
    request: TaskContinuationWindowRequest,
    context: RuntimeContextDep,
) -> TaskContinuationWindowActionResponse:
    """Approve or deny a bounded task continuation window."""

    return resolve_task_continuation_window_response(task_id, request, context)


@router.post(
    "/{task_id}/pause-window",
    response_model=TaskPauseWindowResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def schedule_task_pause_window(
    task_id: UUID,
    request: TaskPauseWindowRequest,
    context: RuntimeContextDep,
) -> TaskPauseWindowResponse:
    """Schedule a local pause boundary for one task."""

    return schedule_task_pause_window_response(task_id, request, context)


@router.post(
    "/{task_id}/pause-window/{pause_window_id}/cancel",
    response_model=TaskPauseWindowResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def cancel_task_pause_window(
    task_id: UUID,
    pause_window_id: UUID,
    request: TaskPauseWindowCancelRequest,
    context: RuntimeContextDep,
) -> TaskPauseWindowResponse:
    """Cancel a local pause window for one task."""

    return cancel_task_pause_window_response(
        task_id,
        pause_window_id,
        request,
        context,
    )


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

    return pause_task_response(task_id, request, context)


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

    return resume_task_response(task_id, request, context)


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

    return cancel_task_response(task_id, request, context)


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

    return adjust_task_budget_response(task_id, request, context)
