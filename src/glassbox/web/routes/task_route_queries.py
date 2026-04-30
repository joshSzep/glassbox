"""HTTP-local read helpers for task routes."""

from typing import cast
from uuid import UUID

from fastapi import HTTPException

from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.web.routes.pagination import page_info
from glassbox.web.task_api import TaskDetailResponse
from glassbox.web.task_api import TaskEventPageResponse
from glassbox.web.task_api import TaskListPageResponse
from glassbox.web.task_api import TaskStepPageResponse
from glassbox.web.task_api import build_projection_health_response
from glassbox.web.task_api import build_task_detail_response
from glassbox.web.task_api import build_task_event_responses
from glassbox.web.task_api import build_task_step_responses
from glassbox.web.task_api import build_task_summary_responses


def task_query_service(context: RuntimeContext) -> TaskQueryService:
    return TaskQueryService(
        cast(TaskPlanRepository, context.repositories.sessions),
        workspace_root=context.infrastructure.artifacts_root,
    )


def ensure_session_exists(session_id: UUID, context: RuntimeContext) -> None:
    if context.repositories.sessions.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")


def list_task_page_response(
    context: RuntimeContext,
    *,
    session_id: UUID | None,
    cursor: int,
    limit: int,
) -> TaskListPageResponse:
    projection_health = None
    if session_id is not None:
        ensure_session_exists(session_id, context)
        projection_health = (
            context.repositories.sessions.inspect_session_projection_health(session_id)
        )

    rows = task_query_service(context).list_task_summaries(
        session_id=session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return TaskListPageResponse(
        session_id=str(session_id) if session_id is not None else None,
        page=page_info(
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


def get_task_detail_response(
    task_id: UUID,
    context: RuntimeContext,
) -> TaskDetailResponse:
    try:
        detail = task_query_service(context).get_task_detail(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    projection_health = context.repositories.sessions.inspect_session_projection_health(
        detail.task.session_id
    )
    return build_task_detail_response(detail, projection_health)


def get_task_step_page_response(
    task_id: UUID,
    context: RuntimeContext,
    *,
    cursor: int,
    limit: int,
) -> TaskStepPageResponse:
    try:
        detail = task_query_service(context).get_task_detail(task_id)
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
        page=page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        projection_health=build_projection_health_response(projection_health),
        items=build_task_step_responses(items),
    )


def get_task_event_page_response(
    task_id: UUID,
    context: RuntimeContext,
    *,
    cursor: int,
    limit: int,
) -> TaskEventPageResponse:
    query_service = task_query_service(context)
    try:
        detail = query_service.get_task_detail(task_id)
        rows = query_service.list_task_events(
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
        page=page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        projection_health=build_projection_health_response(projection_health),
        items=build_task_event_responses(items),
    )
