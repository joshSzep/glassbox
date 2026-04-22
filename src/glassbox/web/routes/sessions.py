"""Session snapshot API route: GET /sessions/{session_id}."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from glassbox.core.types import ApprovalStatus, ToolExecutionStatus
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


class SessionSnapshotResponse(BaseModel):
    session_id: str
    status: str
    model_name: str
    cwd: str
    approval_mode: str
    created_at: datetime
    updated_at: datetime
    last_sequence: int
    pending_approval_id: str | None
    pending_question_id: str | None
    transcript: list[TranscriptMessageResponse]
    active_tool_calls: list[ActiveToolCallResponse]
    pending_approvals: list[PendingApprovalResponse]
    turn_metrics: list[TurnMetricsResponse]


@router.get("/{session_id}", response_model=SessionSnapshotResponse)
async def get_session_snapshot(
    session_id: UUID,
    context: RuntimeContextDep,
) -> SessionSnapshotResponse:
    """Return a full snapshot of the current session state."""

    repo = context.repositories.sessions
    record = repo.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    state = repo.get_session_state(session_id)
    transcript = repo.list_transcript_messages(session_id)
    active_tool_calls = repo.list_tool_calls(
        session_id, status=ToolExecutionStatus.RUNNING
    )
    pending_approvals = repo.list_approvals(session_id, status=ApprovalStatus.PENDING)
    turn_metrics = repo.list_turn_metrics(session_id, limit=10)

    return SessionSnapshotResponse(
        session_id=str(record.session_id),
        status=record.status,
        model_name=record.model_name,
        cwd=str(record.cwd),
        approval_mode=record.approval_mode,
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_sequence=record.last_sequence,
        pending_approval_id=(
            str(state.pending_approval_id)
            if state and state.pending_approval_id
            else None
        ),
        pending_question_id=(
            str(state.pending_question_id)
            if state and state.pending_question_id
            else None
        ),
        transcript=[
            TranscriptMessageResponse(
                message_id=str(msg.message_id),
                role=msg.role,
                parts=[
                    MessagePartResponse(kind=part.kind, text=part.text)
                    for part in msg.parts
                ],
                created_at=msg.created_at,
            )
            for msg in transcript
        ],
        active_tool_calls=[
            ActiveToolCallResponse(
                tool_call_id=str(tc.tool_call_id),
                turn_id=str(tc.turn_id),
                tool_name=tc.tool_name,
                status=tc.status,
                started_at=tc.started_at,
            )
            for tc in active_tool_calls
        ],
        pending_approvals=[
            PendingApprovalResponse(
                approval_id=str(ap.approval_id),
                turn_id=str(ap.turn_id),
                subject=ap.subject,
                reason=ap.reason,
                requested_at=ap.requested_at,
            )
            for ap in pending_approvals
        ],
        turn_metrics=[
            TurnMetricsResponse(
                turn_id=str(metrics.turn_id),
                started_at=metrics.started_at,
                completed_at=metrics.completed_at,
                turn_duration_ms=metrics.turn_duration_ms,
                model_call_count=metrics.model_call_count,
                model_duration_ms_total=metrics.model_duration_ms_total,
                model_input_tokens_total=metrics.model_input_tokens_total,
                model_output_tokens_total=metrics.model_output_tokens_total,
                tool_call_count=metrics.tool_call_count,
                tool_duration_ms_total=metrics.tool_duration_ms_total,
                succeeded_tool_call_count=metrics.succeeded_tool_call_count,
                failed_tool_call_count=metrics.failed_tool_call_count,
            )
            for metrics in turn_metrics
        ],
    )
