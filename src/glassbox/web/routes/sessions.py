"""Session snapshot API route: GET /sessions/{session_id}."""

from pathlib import Path
from typing import Annotated
from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.runtime.daemon import RuntimeOwnerStatus
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.session_queries import OPERATOR_SORT_PRIORITY
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import WorkspaceRuntimeSummaryView
from glassbox.web.app import RuntimeContextDep
from glassbox.web.session_api import ActionAcceptedResponse
from glassbox.web.session_api import CancelSessionTurnRequest
from glassbox.web.session_api import ErrorDetailResponse
from glassbox.web.session_api import ForkSessionRequest
from glassbox.web.session_api import ForkSessionResponse
from glassbox.web.session_api import SessionAggregateResponse
from glassbox.web.session_api import SessionSnapshotResponse
from glassbox.web.session_api import SessionSummaryResponse
from glassbox.web.session_api import SubmitSessionAnswerRequest
from glassbox.web.session_api import SubmitSessionMessageRequest
from glassbox.web.session_api import build_fork_session_response
from glassbox.web.session_api import build_session_aggregate_response
from glassbox.web.session_api import build_session_snapshot_response
from glassbox.web.session_api import build_session_summary_responses

router = APIRouter(prefix="/sessions")


AggregateQueueParam = Literal[
    "all",
    "approvals",
    "questions",
    "failures",
    "degraded",
    "active",
    "action-needed",
    "historical",
]

AggregateSortParam = Literal["priority", "updated_at"]


def _query_service(context: RuntimeContextDep) -> SessionQueryService:
    return SessionQueryService(
        context.repositories.sessions,
        context.repositories.artifacts,
    )


@router.get("", response_model=list[SessionSummaryResponse])
async def list_session_summaries(
    context: RuntimeContextDep,
) -> list[SessionSummaryResponse]:
    """Return recent session summaries for standalone dashboard discovery."""

    query_service = _query_service(context)
    return build_session_summary_responses(query_service.list_session_summaries())


@router.get("/aggregate", response_model=SessionAggregateResponse)
async def get_session_aggregate(
    context: RuntimeContextDep,
    queue: Annotated[
        AggregateQueueParam | None,
        Query(),
    ] = None,
    status: str | None = None,
    sort: Annotated[AggregateSortParam, Query()] = OPERATOR_SORT_PRIORITY,
    limit: Annotated[int | None, Query(ge=1)] = None,
) -> SessionAggregateResponse:
    """Return operator-console queue, health, and priority data."""

    query_service = _query_service(context)
    workspace_root = context.infrastructure.artifacts_root
    owner_status = inspect_runtime_owner(workspace_root)
    aggregate = query_service.get_session_aggregate(
        runtime=_build_workspace_runtime_summary(workspace_root, owner_status),
        queue=queue,
        status=status,
        sort=sort,
        limit=limit,
    )
    return build_session_aggregate_response(aggregate)


@router.post(
    "/{session_id}/fork",
    response_model=ForkSessionResponse,
    status_code=201,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def fork_session(
    session_id: UUID,
    body: ForkSessionRequest,
    context: RuntimeContextDep,
) -> ForkSessionResponse:
    """Create a child session from a stable historical fork point."""

    repo = context.repositories.sessions
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    try:
        forked_session = await context.services.session_service.fork_session(
            session_id,
            turn_id=body.turn_id,
            branch_label=body.branch_label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return build_fork_session_response(forked_session)


@router.post(
    "/{session_id}/messages",
    response_model=ActionAcceptedResponse,
    status_code=200,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def submit_session_message(
    session_id: UUID,
    body: SubmitSessionMessageRequest,
    context: RuntimeContextDep,
) -> ActionAcceptedResponse:
    """Submit a new user message into an existing session."""

    repo = context.repositories.sessions
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    try:
        await context.services.session_service.submit_user_message(
            session_id,
            body.text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ActionAcceptedResponse(status="ok")


@router.post(
    "/{session_id}/questions/{question_id}",
    response_model=ActionAcceptedResponse,
    status_code=200,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def submit_session_answer(
    session_id: UUID,
    question_id: UUID,
    body: SubmitSessionAnswerRequest,
    context: RuntimeContextDep,
) -> ActionAcceptedResponse:
    """Submit an answer for a pending ask_user question."""

    repo = context.repositories.sessions
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    try:
        await context.services.session_service.provide_user_answer(
            session_id,
            question_id,
            body.answer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ActionAcceptedResponse(status="ok")


@router.post(
    "/{session_id}/cancel",
    response_model=ActionAcceptedResponse,
    status_code=200,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def cancel_session_turn(
    session_id: UUID,
    body: CancelSessionTurnRequest,
    context: RuntimeContextDep,
) -> ActionAcceptedResponse:
    """Request cancellation of the active live turn for a session."""

    repo = context.repositories.sessions
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    try:
        await context.services.session_service.cancel_turn(
            session_id,
            turn_id=body.turn_id,
            requested_by="api",
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ActionAcceptedResponse(status="ok")


@router.get(
    "/{session_id}",
    response_model=SessionSnapshotResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_session_snapshot(
    session_id: UUID,
    context: RuntimeContextDep,
) -> SessionSnapshotResponse:
    """Return a full snapshot of the current session state."""

    query_service = _query_service(context)
    try:
        snapshot = query_service.get_session_snapshot(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return build_session_snapshot_response(snapshot)


def _build_workspace_runtime_summary(
    workspace_root: Path,
    owner_status: RuntimeOwnerStatus,
) -> WorkspaceRuntimeSummaryView:
    record = owner_status.record
    dashboard_url = record.dashboard_url if record is not None else None
    return WorkspaceRuntimeSummaryView(
        workspace_root=str(workspace_root),
        state=owner_status.state,
        health=owner_status.health,
        pid=record.pid if record is not None else None,
        dashboard_url=dashboard_url,
        health_url=(dashboard_url.rstrip("/") + "/healthz") if dashboard_url else None,
        session_index_url=dashboard_url,
        started_at=record.started_at if record is not None else None,
    )
