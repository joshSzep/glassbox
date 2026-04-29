"""Task-plan inspection API routes."""

from typing import Annotated
from typing import cast
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.web.app import RuntimeContextDep
from glassbox.web.session_api import ErrorDetailResponse
from glassbox.web.session_api import PageInfoResponse
from glassbox.web.task_api import TaskDetailResponse
from glassbox.web.task_api import TaskEventPageResponse
from glassbox.web.task_api import TaskListPageResponse
from glassbox.web.task_api import TaskStepPageResponse
from glassbox.web.task_api import build_projection_health_response
from glassbox.web.task_api import build_task_detail_response
from glassbox.web.task_api import build_task_event_responses
from glassbox.web.task_api import build_task_step_responses
from glassbox.web.task_api import build_task_summary_responses

router = APIRouter(prefix="/tasks")

PageCursorParam = Annotated[int, Query(ge=0)]
PageLimitParam = Annotated[int, Query(ge=1, le=500)]


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
