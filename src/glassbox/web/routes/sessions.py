"""Session snapshot API route: GET /sessions/{session_id}."""

from pathlib import Path
from typing import Annotated
from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import ToolArtifactRecorded
from glassbox.runtime.context_compaction_service import invalidate_context_compaction
from glassbox.runtime.context_compaction_service import refresh_context_compaction
from glassbox.runtime.daemon import RuntimeOwnerStatus
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.observability import build_background_job_observability
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.session_queries import OPERATOR_SORT_PRIORITY
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import WorkspaceRuntimeSummaryView
from glassbox.services import SessionRepository
from glassbox.web.app import RuntimeContextDep
from glassbox.web.session_api import ActionAcceptedResponse
from glassbox.web.session_api import ArtifactDetailResponse
from glassbox.web.session_api import CancelSessionTurnRequest
from glassbox.web.session_api import ContextCompactionResponse
from glassbox.web.session_api import ErrorDetailResponse
from glassbox.web.session_api import EventLogEntryResponse
from glassbox.web.session_api import ForkSessionRequest
from glassbox.web.session_api import ForkSessionResponse
from glassbox.web.session_api import InvalidateContextCompactionRequest
from glassbox.web.session_api import InvalidateContextCompactionResponse
from glassbox.web.session_api import PageInfoResponse
from glassbox.web.session_api import RefreshContextCompactionRequest
from glassbox.web.session_api import RefreshContextCompactionResponse
from glassbox.web.session_api import SessionAggregateResponse
from glassbox.web.session_api import SessionArtifactPageResponse
from glassbox.web.session_api import SessionCheckpointPageResponse
from glassbox.web.session_api import SessionCompactionPageResponse
from glassbox.web.session_api import SessionEventLogPageResponse
from glassbox.web.session_api import SessionSnapshotResponse
from glassbox.web.session_api import SessionSummaryResponse
from glassbox.web.session_api import SessionToolCallPageResponse
from glassbox.web.session_api import SessionTranscriptPageResponse
from glassbox.web.session_api import SessionTurnMetricsPageResponse
from glassbox.web.session_api import SubmitSessionAnswerRequest
from glassbox.web.session_api import SubmitSessionMessageRequest
from glassbox.web.session_api import TaskCheckpointResponse
from glassbox.web.session_api import ToolCallResponse
from glassbox.web.session_api import TranscriptMessageResponse
from glassbox.web.session_api import TurnMetricsResponse
from glassbox.web.session_api import build_fork_session_response
from glassbox.web.session_api import build_provider_evidence_summary_response
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
PageCursorParam = Annotated[int, Query(ge=0)]
PageLimitParam = Annotated[int, Query(ge=1, le=500)]


def _query_service(context: RuntimeContextDep) -> SessionQueryService:
    return SessionQueryService(
        context.repositories.sessions,
        context.repositories.artifacts,
    )


def _ensure_session_exists(session_id: UUID, context: RuntimeContextDep) -> None:
    if context.repositories.sessions.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")


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
        runtime=_build_workspace_runtime_summary(
            workspace_root,
            owner_status,
            context.repositories.sessions,
        ),
        queue=queue,
        status=status,
        sort=sort,
        limit=limit,
    )
    response = build_session_aggregate_response(aggregate)
    response.provider_evidence = build_provider_evidence_summary_response(
        load_provider_canary_evidence(workspace_root)
    )
    return response


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
    "/{session_id}/transcript",
    response_model=SessionTranscriptPageResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_session_transcript_page(
    session_id: UUID,
    context: RuntimeContextDep,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> SessionTranscriptPageResponse:
    """Return a bounded transcript page for a session."""

    _ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_transcript_messages(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionTranscriptPageResponse(
        session_id=str(session_id),
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            TranscriptMessageResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


@router.get(
    "/{session_id}/event-log",
    response_model=SessionEventLogPageResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_session_event_log_page(
    session_id: UUID,
    context: RuntimeContextDep,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> SessionEventLogPageResponse:
    """Return canonical events after ``cursor`` sequence for a session."""

    _ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.read_session_events_after(
        session_id,
        cursor,
        limit=limit + 1,
    )
    items = rows[:limit]
    next_cursor = items[-1].sequence if len(rows) > limit and items else None
    return SessionEventLogPageResponse(
        session_id=str(session_id),
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            EventLogEntryResponse(
                event_id=str(event.event_id),
                session_id=str(event.session_id),
                sequence=event.sequence,
                event_type=event.event_type,
                event_version=event.event_version,
                created_at=event.created_at,
                payload=event.payload.model_dump(mode="json"),
            )
            for event in items
        ],
    )


@router.get(
    "/{session_id}/tool-calls",
    response_model=SessionToolCallPageResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_session_tool_call_page(
    session_id: UUID,
    context: RuntimeContextDep,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> SessionToolCallPageResponse:
    """Return a bounded page of projected tool-call details."""

    _ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_tool_calls(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionToolCallPageResponse(
        session_id=str(session_id),
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            ToolCallResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


@router.get(
    "/{session_id}/turn-metrics",
    response_model=SessionTurnMetricsPageResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_session_turn_metrics_page(
    session_id: UUID,
    context: RuntimeContextDep,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> SessionTurnMetricsPageResponse:
    """Return a bounded page of projected turn metrics."""

    _ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_turn_metrics(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionTurnMetricsPageResponse(
        session_id=str(session_id),
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            TurnMetricsResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


@router.get(
    "/{session_id}/checkpoints",
    response_model=SessionCheckpointPageResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_session_checkpoint_page(
    session_id: UUID,
    context: RuntimeContextDep,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> SessionCheckpointPageResponse:
    """Return a bounded page of projected task/session checkpoints."""

    _ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_task_checkpoints(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionCheckpointPageResponse(
        session_id=str(session_id),
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            TaskCheckpointResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


@router.get(
    "/{session_id}/compactions",
    response_model=SessionCompactionPageResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_session_compaction_page(
    session_id: UUID,
    context: RuntimeContextDep,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> SessionCompactionPageResponse:
    """Return a bounded page of projected context compactions."""

    _ensure_session_exists(session_id, context)
    rows = context.repositories.sessions.list_context_compactions(
        session_id,
        limit=limit + 1,
        offset=cursor,
    )
    items = rows[:limit]
    next_cursor = cursor + len(items) if len(rows) > limit else None
    return SessionCompactionPageResponse(
        session_id=str(session_id),
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=[
            ContextCompactionResponse.model_validate(item.model_dump(mode="json"))
            for item in items
        ],
    )


@router.post(
    "/{session_id}/compactions/{compaction_id}/refresh",
    response_model=RefreshContextCompactionResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def refresh_session_compaction(
    session_id: UUID,
    compaction_id: UUID,
    body: RefreshContextCompactionRequest,
    context: RuntimeContextDep,
) -> RefreshContextCompactionResponse:
    """Create a replacement compaction after explicit operator confirmation."""

    _ensure_session_exists(session_id, context)
    if not body.confirmed:
        raise HTTPException(
            status_code=409,
            detail="refresh requires confirmed=true",
        )
    try:
        refreshed, change = refresh_context_compaction(
            context.repositories.sessions,
            context.repositories.artifacts,
            session_id,
            compaction_id,
            changed_by="api",
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    refreshed_record = context.repositories.sessions.get_context_compaction(
        session_id,
        refreshed.compaction_id,
    )
    if refreshed_record is None:
        raise HTTPException(
            status_code=409,
            detail="refreshed compaction projection is unavailable",
        )
    return RefreshContextCompactionResponse(
        refreshed_compaction=ContextCompactionResponse.model_validate(
            refreshed_record.model_dump(mode="json")
        ),
        previous_compaction_id=str(change.compaction_id),
        previous_freshness=change.freshness.value,
        previous_freshness_reason=change.reason,
        superseded_by_compaction_id=str(refreshed.compaction_id),
    )


@router.post(
    "/{session_id}/compactions/{compaction_id}/invalidate",
    response_model=InvalidateContextCompactionResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def invalidate_session_compaction(
    session_id: UUID,
    compaction_id: UUID,
    body: InvalidateContextCompactionRequest,
    context: RuntimeContextDep,
) -> InvalidateContextCompactionResponse:
    """Mark a compaction as invalidated after explicit confirmation."""

    _ensure_session_exists(session_id, context)
    if not body.confirmed:
        raise HTTPException(
            status_code=409,
            detail="invalidation requires confirmed=true",
        )
    try:
        change = invalidate_context_compaction(
            context.repositories.sessions,
            session_id,
            compaction_id,
            reason=body.reason,
            changed_by="api",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return InvalidateContextCompactionResponse(
        compaction_id=str(change.compaction_id),
        freshness=change.freshness.value,
        freshness_reason=change.reason,
    )


@router.get(
    "/{session_id}/artifacts",
    response_model=SessionArtifactPageResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_session_artifact_page(
    session_id: UUID,
    context: RuntimeContextDep,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> SessionArtifactPageResponse:
    """Return event-referenced artifact details for a session."""

    _ensure_session_exists(session_id, context)
    artifacts = [
        _artifact_detail_from_event(event)
        for event in context.repositories.sessions.read_session_events(session_id)
        if isinstance(event.payload, ToolArtifactRecorded | ReplayArtifactRecorded)
    ]
    items = artifacts[cursor : cursor + limit]
    next_cursor = cursor + len(items) if cursor + limit < len(artifacts) else None
    return SessionArtifactPageResponse(
        session_id=str(session_id),
        page=_page_info(
            cursor=cursor,
            limit=limit,
            returned_count=len(items),
            next_cursor=next_cursor,
        ),
        items=items,
    )


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


def _artifact_detail_from_event(event) -> ArtifactDetailResponse:
    payload = event.payload
    return ArtifactDetailResponse(
        sequence=event.sequence,
        event_type=event.event_type,
        artifact_id=str(payload.artifact_id),
        artifact_kind=payload.artifact_kind,
        path=payload.path,
        tool_call_id=str(payload.tool_call_id) if payload.tool_call_id else None,
        turn_id=str(payload.turn_id),
        content_sha256=payload.content_sha256,
        size_bytes=payload.size_bytes,
    )


def _build_workspace_runtime_summary(
    workspace_root: Path,
    owner_status: RuntimeOwnerStatus,
    session_repository: SessionRepository,
) -> WorkspaceRuntimeSummaryView:
    record = owner_status.record
    dashboard_url = record.dashboard_url if record is not None else None
    background_jobs = build_background_job_observability(session_repository)
    return WorkspaceRuntimeSummaryView(
        workspace_root=str(workspace_root),
        state=owner_status.state,
        health=owner_status.health,
        pid=record.pid if record is not None else None,
        dashboard_url=dashboard_url,
        health_url=(dashboard_url.rstrip("/") + "/healthz") if dashboard_url else None,
        session_index_url=dashboard_url,
        started_at=record.started_at if record is not None else None,
        background_job_failed_count=background_jobs.failed_count,
        background_job_retryable_count=background_jobs.retryable_count,
        background_job_abandoned_count=background_jobs.abandoned_count,
    )
