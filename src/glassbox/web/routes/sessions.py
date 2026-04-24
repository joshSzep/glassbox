"""Session snapshot API route: GET /sessions/{session_id}."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from glassbox.runtime import RuntimeContextSnapshot
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.web.app import RuntimeContextDep

router = APIRouter(prefix="/sessions")


class MessagePartResponse(BaseModel):
    kind: str
    text: str


class TranscriptMessageResponse(BaseModel):
    message_id: str
    role: str
    parts: list[MessagePartResponse]
    created_at: datetime


class ActiveToolCallResponse(BaseModel):
    tool_call_id: str
    turn_id: str
    tool_name: str
    status: str
    started_at: datetime | None


class PendingApprovalResponse(BaseModel):
    approval_id: str
    turn_id: str
    subject: str
    reason: str
    requested_at: datetime


class TurnMetricsResponse(BaseModel):
    turn_id: str
    started_at: datetime | None
    completed_at: datetime | None
    turn_duration_ms: int | None
    model_call_count: int
    model_duration_ms_total: int
    model_input_tokens_total: int
    model_output_tokens_total: int
    tool_call_count: int
    tool_duration_ms_total: int
    succeeded_tool_call_count: int
    failed_tool_call_count: int


class ChildSessionSummaryResponse(BaseModel):
    session_id: str
    status: str
    branch_label: str | None
    updated_at: datetime
    latest_message_summary: str | None


class BranchableTurnResponse(BaseModel):
    turn_id: str
    sequence: int
    created_at: datetime
    label: str


class ForkSessionRequest(BaseModel):
    turn_id: UUID | None = None
    branch_label: str | None = None


class ForkSessionResponse(BaseModel):
    child_session_id: str
    parent_session_id: str
    forked_from_turn_id: str
    forked_from_sequence: int
    branch_label: str | None
    inherited_message_count: int
    last_sequence: int


class SubmitSessionMessageRequest(BaseModel):
    text: str


class SubmitSessionAnswerRequest(BaseModel):
    answer: str


class ActionAcceptedResponse(BaseModel):
    status: str


class SessionSummaryResponse(BaseModel):
    session_id: str
    status: str
    model_name: str
    cwd: str
    approval_mode: str
    parent_session_id: str | None
    forked_from_turn_id: str | None
    forked_from_sequence: int | None
    branch_label: str | None
    child_session_count: int
    can_fork: bool
    latest_fork_point_turn_id: str | None
    latest_fork_point_sequence: int | None
    fork_blocked_reason: str | None
    dashboard_url: str | None
    created_at: datetime
    updated_at: datetime
    last_sequence: int
    pending_approval_id: str | None
    pending_question_id: str | None
    pending_question_text: str | None
    session_failure_message: str | None
    session_failure_retryable: bool | None
    latest_message_summary: str | None
    next_action_summary: str


class SessionSnapshotResponse(BaseModel):
    session_id: str
    status: str
    current_turn_id: str | None
    model_name: str
    cwd: str
    approval_mode: str
    parent_session_id: str | None
    forked_from_turn_id: str | None
    forked_from_sequence: int | None
    branch_label: str | None
    child_sessions: list[ChildSessionSummaryResponse]
    branchable_turns: list[BranchableTurnResponse]
    can_fork: bool
    latest_fork_point_turn_id: str | None
    latest_fork_point_sequence: int | None
    fork_blocked_reason: str | None
    dashboard_url: str | None
    created_at: datetime
    updated_at: datetime
    last_sequence: int
    pending_approval_id: str | None
    pending_question_id: str | None
    pending_question_text: str | None
    session_failure_message: str | None
    session_failure_retryable: bool | None
    transcript: list[TranscriptMessageResponse]
    active_tool_calls: list[ActiveToolCallResponse]
    pending_approvals: list[PendingApprovalResponse]
    turn_metrics: list[TurnMetricsResponse]
    runtime_context: RuntimeContextSnapshot


@router.get("", response_model=list[SessionSummaryResponse])
async def list_session_summaries(
    context: RuntimeContextDep,
) -> list[SessionSummaryResponse]:
    """Return recent session summaries for standalone dashboard discovery."""

    query_service = SessionQueryService(
        context.repositories.sessions,
        context.repositories.artifacts,
    )
    return [
        SessionSummaryResponse.model_validate(summary.model_dump(mode="json"))
        for summary in query_service.list_session_summaries()
    ]


@router.post(
    "/{session_id}/fork",
    response_model=ForkSessionResponse,
    status_code=201,
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

    return ForkSessionResponse(
        child_session_id=str(forked_session.child_session_id),
        parent_session_id=str(forked_session.parent_session_id),
        forked_from_turn_id=str(forked_session.forked_from_turn_id),
        forked_from_sequence=forked_session.forked_from_sequence,
        branch_label=forked_session.branch_label,
        inherited_message_count=forked_session.inherited_message_count,
        last_sequence=forked_session.last_sequence,
    )


@router.post(
    "/{session_id}/messages",
    response_model=ActionAcceptedResponse,
    status_code=200,
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


@router.get("/{session_id}", response_model=SessionSnapshotResponse)
async def get_session_snapshot(
    session_id: UUID,
    context: RuntimeContextDep,
) -> SessionSnapshotResponse:
    """Return a full snapshot of the current session state."""

    query_service = SessionQueryService(
        context.repositories.sessions,
        context.repositories.artifacts,
    )
    try:
        snapshot = query_service.get_session_snapshot(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SessionSnapshotResponse.model_validate(snapshot.model_dump(mode="json"))
