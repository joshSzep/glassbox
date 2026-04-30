"""Session dashboard API routes."""

from typing import Annotated
from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from fastapi import Query

from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.session_queries import OPERATOR_SORT_PRIORITY
from glassbox.web.app import RuntimeContextDep
from glassbox.web.routes.session_route_actions import (
    abandon_session_tool_attempt_response,
)
from glassbox.web.routes.session_route_actions import cancel_session_turn_response
from glassbox.web.routes.session_route_actions import fork_session_response
from glassbox.web.routes.session_route_actions import (
    inspect_session_tool_attempt_response,
)
from glassbox.web.routes.session_route_actions import (
    invalidate_session_compaction_response,
)
from glassbox.web.routes.session_route_actions import (
    refresh_session_compaction_response,
)
from glassbox.web.routes.session_route_actions import (
    retry_session_tool_attempt_response,
)
from glassbox.web.routes.session_route_actions import submit_session_answer_response
from glassbox.web.routes.session_route_actions import submit_session_message_response
from glassbox.web.routes.session_route_queries import get_session_aggregate_response
from glassbox.web.routes.session_route_queries import get_session_artifact_response
from glassbox.web.routes.session_route_queries import get_session_checkpoint_response
from glassbox.web.routes.session_route_queries import get_session_compaction_response
from glassbox.web.routes.session_route_queries import get_session_event_log_response
from glassbox.web.routes.session_route_queries import get_session_snapshot_response
from glassbox.web.routes.session_route_queries import get_session_tool_call_response
from glassbox.web.routes.session_route_queries import get_session_transcript_response
from glassbox.web.routes.session_route_queries import get_session_turn_metrics_response
from glassbox.web.routes.session_route_queries import list_session_summary_responses
from glassbox.web.session_api import ActionAcceptedResponse
from glassbox.web.session_api import CancelSessionTurnRequest
from glassbox.web.session_api import ErrorDetailResponse
from glassbox.web.session_api import ForkSessionRequest
from glassbox.web.session_api import ForkSessionResponse
from glassbox.web.session_api import InvalidateContextCompactionRequest
from glassbox.web.session_api import InvalidateContextCompactionResponse
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
from glassbox.web.session_api import ToolAttemptAbandonRequest
from glassbox.web.session_api import ToolAttemptInspectionResponse
from glassbox.web.session_api import ToolAttemptRecoveryRequest
from glassbox.web.session_api import ToolAttemptRecoveryResponse

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


@router.get("", response_model=list[SessionSummaryResponse])
async def list_session_summaries(
    context: RuntimeContextDep,
) -> list[SessionSummaryResponse]:
    """Return recent session summaries for standalone dashboard discovery."""

    return list_session_summary_responses(context)


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

    return get_session_aggregate_response(
        context,
        queue=queue,
        status=status,
        sort=sort,
        limit=limit,
        owner_status=inspect_runtime_owner(context.infrastructure.artifacts_root),
    )


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

    return await fork_session_response(
        session_id,
        context,
        turn_id=body.turn_id,
        branch_label=body.branch_label,
    )


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

    return await submit_session_message_response(
        session_id,
        context,
        text=body.text,
    )


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

    return await submit_session_answer_response(
        session_id,
        question_id,
        context,
        answer=body.answer,
    )


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

    return await cancel_session_turn_response(
        session_id,
        context,
        turn_id=body.turn_id,
        reason=body.reason,
    )


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

    return get_session_transcript_response(
        session_id,
        context,
        cursor=cursor,
        limit=limit,
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

    return get_session_event_log_response(
        session_id,
        context,
        cursor=cursor,
        limit=limit,
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

    return get_session_tool_call_response(
        session_id,
        context,
        cursor=cursor,
        limit=limit,
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

    return get_session_turn_metrics_response(
        session_id,
        context,
        cursor=cursor,
        limit=limit,
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

    return get_session_checkpoint_response(
        session_id,
        context,
        cursor=cursor,
        limit=limit,
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

    return get_session_compaction_response(
        session_id,
        context,
        cursor=cursor,
        limit=limit,
    )


@router.get(
    "/{session_id}/tool-attempts/{tool_attempt_id}",
    response_model=ToolAttemptInspectionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def inspect_session_tool_attempt(
    session_id: UUID,
    tool_attempt_id: UUID,
    context: RuntimeContextDep,
) -> ToolAttemptInspectionResponse:
    """Inspect one durable tool-attempt recovery record."""

    return inspect_session_tool_attempt_response(session_id, tool_attempt_id, context)


@router.post(
    "/{session_id}/tool-attempts/{tool_attempt_id}/retry",
    response_model=ToolAttemptRecoveryResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def retry_session_tool_attempt(
    session_id: UUID,
    tool_attempt_id: UUID,
    body: ToolAttemptRecoveryRequest,
    context: RuntimeContextDep,
) -> ToolAttemptRecoveryResponse:
    """Retry one stale or failed tool attempt after explicit confirmation."""

    return await retry_session_tool_attempt_response(
        session_id,
        tool_attempt_id,
        context,
        confirmed=body.confirmed,
        actor=body.actor,
        reason=body.reason,
    )


@router.post(
    "/{session_id}/tool-attempts/{tool_attempt_id}/abandon",
    response_model=ToolAttemptRecoveryResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def abandon_session_tool_attempt(
    session_id: UUID,
    tool_attempt_id: UUID,
    body: ToolAttemptAbandonRequest,
    context: RuntimeContextDep,
) -> ToolAttemptRecoveryResponse:
    """Abandon one stale or failed tool attempt after explicit confirmation."""

    return abandon_session_tool_attempt_response(
        session_id,
        tool_attempt_id,
        context,
        confirmed=body.confirmed,
        actor=body.actor,
        reason=body.reason,
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

    return refresh_session_compaction_response(
        session_id,
        compaction_id,
        context,
        confirmed=body.confirmed,
        reason=body.reason,
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

    return invalidate_session_compaction_response(
        session_id,
        compaction_id,
        context,
        confirmed=body.confirmed,
        reason=body.reason,
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

    return get_session_artifact_response(
        session_id,
        context,
        cursor=cursor,
        limit=limit,
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

    return get_session_snapshot_response(session_id, context)
