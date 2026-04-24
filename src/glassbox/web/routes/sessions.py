"""Session snapshot API route: GET /sessions/{session_id}."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from glassbox.core.events import (
    EventEnvelope,
    SessionFailed,
    SessionStarted,
    TurnCompleted,
    TurnStarted,
    UserMessageReceived,
    UserQuestionAsked,
)
from glassbox.core.models import TranscriptMessage
from glassbox.core.types import ApprovalStatus, ToolExecutionStatus
from glassbox.runtime import (
    ArtifactBackedContextSnapshot,
    ArtifactBackedContextSummarySnapshot,
    RuntimeContextNoteSnapshot,
    RuntimeContextSnapshot,
    WorkingSetItemSnapshot,
    WorkingSetSnapshot,
)
from glassbox.runtime.context_builder import (
    build_artifact_backed_context_snapshot,
    build_runtime_context_snapshot,
    build_working_set_snapshot,
)
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

    repo = context.repositories.sessions
    records = repo.list_sessions()
    summaries: list[SessionSummaryResponse] = []
    child_counts_by_parent = _child_counts_by_parent(records)

    for record in records:
        state = repo.get_session_state(record.session_id)
        session_events = repo.read_session_events(record.session_id)
        transcript = repo.list_transcript_messages(record.session_id)
        dashboard_url = _dashboard_url_from_events(session_events)
        latest_session_failure = _latest_session_failure(session_events)
        pending_question_id = state.pending_question_id if state is not None else None
        pending_question_text = _pending_question_text_from_events(
            session_events,
            pending_question_id,
        )
        (
            can_fork,
            latest_fork_point_turn_id,
            latest_fork_point_sequence,
            fork_blocked_reason,
        ) = _fork_capability(repo, record.session_id)

        summaries.append(
            SessionSummaryResponse(
                session_id=str(record.session_id),
                status=state.status if state is not None else record.status,
                model_name=record.model_name,
                cwd=str(record.cwd),
                approval_mode=record.approval_mode,
                parent_session_id=(
                    str(record.parent_session_id)
                    if record.parent_session_id is not None
                    else None
                ),
                forked_from_turn_id=(
                    str(record.forked_from_turn_id)
                    if record.forked_from_turn_id is not None
                    else None
                ),
                forked_from_sequence=record.forked_from_sequence,
                branch_label=record.branch_label,
                child_session_count=child_counts_by_parent.get(
                    str(record.session_id),
                    0,
                ),
                can_fork=can_fork,
                latest_fork_point_turn_id=(
                    str(latest_fork_point_turn_id)
                    if latest_fork_point_turn_id is not None
                    else None
                ),
                latest_fork_point_sequence=latest_fork_point_sequence,
                fork_blocked_reason=fork_blocked_reason,
                dashboard_url=dashboard_url,
                created_at=record.created_at,
                updated_at=record.updated_at,
                last_sequence=record.last_sequence,
                pending_approval_id=(
                    str(state.pending_approval_id)
                    if state is not None and state.pending_approval_id is not None
                    else None
                ),
                pending_question_id=(
                    str(pending_question_id)
                    if pending_question_id is not None
                    else None
                ),
                pending_question_text=pending_question_text,
                session_failure_message=(
                    latest_session_failure.error_message
                    if latest_session_failure is not None
                    else None
                ),
                session_failure_retryable=(
                    latest_session_failure.retryable
                    if latest_session_failure is not None
                    else None
                ),
                latest_message_summary=_latest_message_summary(transcript),
                next_action_summary=_next_action_summary(
                    state.status if state is not None else record.status,
                    pending_question_text=pending_question_text,
                    session_failure=latest_session_failure,
                    current_turn_id=(
                        state.current_turn_id if state is not None else None
                    ),
                ),
            )
        )

    return summaries


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

    repo = context.repositories.sessions
    record = repo.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")

    state = repo.get_session_state(session_id)
    session_events = repo.read_session_events(session_id)
    transcript = repo.list_transcript_messages(session_id)
    active_tool_calls = repo.list_tool_calls(
        session_id, status=ToolExecutionStatus.RUNNING
    )
    pending_approvals = repo.list_approvals(session_id, status=ApprovalStatus.PENDING)
    turn_metrics = repo.list_turn_metrics(session_id, limit=10)
    runtime_notes = repo.list_runtime_notes(session_id)
    dashboard_url = _dashboard_url_from_events(session_events)
    latest_session_failure = _latest_session_failure(session_events)
    pending_question_text = _pending_question_text_from_events(
        session_events,
        state.pending_question_id if state is not None else None,
    )
    (
        can_fork,
        latest_fork_point_turn_id,
        latest_fork_point_sequence,
        fork_blocked_reason,
    ) = _fork_capability(repo, session_id)
    working_set = build_working_set_snapshot(repo, session_id)
    runtime_context = build_runtime_context_snapshot(
        record.cwd,
        runtime_notes,
        working_set=working_set,
        artifact_context=build_artifact_backed_context_snapshot(
            repo,
            context.repositories.artifacts,
            session_id,
        ),
    )

    return SessionSnapshotResponse(
        session_id=str(record.session_id),
        status=state.status if state is not None else record.status,
        current_turn_id=(
            str(state.current_turn_id) if state and state.current_turn_id else None
        ),
        model_name=record.model_name,
        cwd=str(record.cwd),
        approval_mode=record.approval_mode,
        parent_session_id=(
            str(record.parent_session_id)
            if record.parent_session_id is not None
            else None
        ),
        forked_from_turn_id=(
            str(record.forked_from_turn_id)
            if record.forked_from_turn_id is not None
            else None
        ),
        forked_from_sequence=record.forked_from_sequence,
        branch_label=record.branch_label,
        child_sessions=_child_session_summaries(repo, session_id),
        branchable_turns=(
            _branchable_turns_from_events(session_events) if can_fork else []
        ),
        can_fork=can_fork,
        latest_fork_point_turn_id=(
            str(latest_fork_point_turn_id)
            if latest_fork_point_turn_id is not None
            else None
        ),
        latest_fork_point_sequence=latest_fork_point_sequence,
        fork_blocked_reason=fork_blocked_reason,
        dashboard_url=dashboard_url,
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
        pending_question_text=pending_question_text,
        session_failure_message=(
            latest_session_failure.error_message
            if latest_session_failure is not None
            else None
        ),
        session_failure_retryable=(
            latest_session_failure.retryable
            if latest_session_failure is not None
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
        runtime_context=RuntimeContextSnapshot(
            repository_context=runtime_context.repository_context,
            runtime_notes=[
                RuntimeContextNoteSnapshot(
                    category=note.category,
                    message=note.message,
                    inherited=note.inherited,
                    source_session_id=note.source_session_id,
                )
                for note in runtime_context.runtime_notes
            ],
            additional_runtime_note_count=runtime_context.additional_runtime_note_count,
            working_set=WorkingSetSnapshot(
                items=[
                    WorkingSetItemSnapshot(
                        subject_kind=item.subject_kind,
                        subject=item.subject,
                        summary=item.summary,
                        reasons=list(item.reasons),
                        signal_types=list(item.signal_types),
                        inherited=item.inherited,
                    )
                    for item in runtime_context.working_set.items
                ],
                additional_item_count=runtime_context.working_set.additional_item_count,
            ),
            artifact_context=ArtifactBackedContextSnapshot(
                summaries=[
                    ArtifactBackedContextSummarySnapshot(
                        summary_kind=summary.summary_kind,
                        source_tool_name=summary.source_tool_name,
                        artifact_kind=summary.artifact_kind,
                        artifact_path=summary.artifact_path,
                        summary=summary.summary,
                        freshness=summary.freshness,
                        target_paths=list(summary.target_paths),
                        keyword_filter=summary.keyword_filter,
                        failing_tests=list(summary.failing_tests),
                        failure_count=summary.failure_count,
                        error_count=summary.error_count,
                        timed_out=summary.timed_out,
                        inherited=summary.inherited,
                        source_tool_call_id=summary.source_tool_call_id,
                    )
                    for summary in runtime_context.artifact_context.summaries
                ],
                additional_summary_count=(
                    runtime_context.artifact_context.additional_summary_count
                ),
            ),
        ),
    )


def _dashboard_url_from_events(events: list[EventEnvelope]) -> str | None:
    for event in events:
        if isinstance(event.payload, SessionStarted):
            return event.payload.dashboard_url
    return None


def _child_counts_by_parent(records) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        if record.parent_session_id is None:
            continue
        parent_session_id = str(record.parent_session_id)
        counts[parent_session_id] = counts.get(parent_session_id, 0) + 1
    return counts


def _child_session_summaries(
    repo,
    session_id: UUID,
) -> list[ChildSessionSummaryResponse]:
    child_records = [
        record
        for record in repo.list_sessions()
        if record.parent_session_id == session_id
    ]
    child_records.sort(key=lambda record: record.updated_at, reverse=True)

    return [
        ChildSessionSummaryResponse(
            session_id=str(record.session_id),
            status=record.status,
            branch_label=record.branch_label,
            updated_at=record.updated_at,
            latest_message_summary=_latest_message_summary(
                repo.list_transcript_messages(record.session_id)
            ),
        )
        for record in child_records
    ]


def _branchable_turns_from_events(
    events: list[EventEnvelope],
) -> list[BranchableTurnResponse]:
    user_messages_by_id: dict[str, str] = {}
    trigger_message_ids_by_turn: dict[str, str] = {}
    branchable_turns: list[BranchableTurnResponse] = []

    for event in events:
        if isinstance(event.payload, UserMessageReceived):
            user_messages_by_id[str(event.payload.message_id)] = event.payload.text
            continue

        if isinstance(event.payload, TurnStarted):
            trigger_message_ids_by_turn[str(event.payload.turn_id)] = str(
                event.payload.trigger_message_id
            )
            continue

        if not isinstance(event.payload, TurnCompleted):
            continue
        if event.payload.outcome != "completed":
            continue

        turn_id = str(event.payload.turn_id)
        trigger_message_id = trigger_message_ids_by_turn.get(turn_id)
        label = (
            user_messages_by_id.get(trigger_message_id or "") or f"Turn {turn_id[:8]}"
        )
        branchable_turns.append(
            BranchableTurnResponse(
                turn_id=turn_id,
                sequence=event.sequence,
                created_at=event.created_at,
                label=label,
            )
        )

    branchable_turns.sort(key=lambda turn: turn.sequence, reverse=True)
    return branchable_turns


def _fork_capability(
    repo,
    session_id: UUID,
) -> tuple[bool, UUID | None, int | None, str | None]:
    try:
        fork_point = repo.resolve_fork_point(session_id)
    except ValueError as exc:
        return False, None, None, str(exc)

    return True, fork_point.turn_id, fork_point.sequence, None


def _latest_session_failure(events: list[EventEnvelope]) -> SessionFailed | None:
    for event in reversed(events):
        if isinstance(event.payload, SessionFailed):
            return event.payload
    return None


def _pending_question_text_from_events(
    events: list[EventEnvelope],
    pending_question_id,
) -> str | None:
    if pending_question_id is None:
        return None

    pending_question_id_text = str(pending_question_id)
    for event in reversed(events):
        if not isinstance(event.payload, UserQuestionAsked):
            continue
        if str(event.payload.question_id) != pending_question_id_text:
            continue
        return event.payload.question
    return None


def _latest_message_summary(transcript: list[TranscriptMessage]) -> str | None:
    if not transcript:
        return None

    latest_message = transcript[-1]
    parts = getattr(latest_message, "parts", [])
    role = getattr(latest_message, "role", None)
    text = " ".join(
        part.text.strip().replace("\n", " ")
        for part in parts
        if getattr(part, "text", "").strip()
    ).strip()
    if not text:
        return role
    return f"{role}: {text}"


def _next_action_summary(
    status,
    *,
    pending_question_text: str | None,
    session_failure: SessionFailed | None,
    current_turn_id,
) -> str:
    status_text = str(status)

    if status_text == "awaiting_user_input":
        if pending_question_text is not None:
            return f"Answer pending question: {pending_question_text}"
        return "Answer pending question"

    if status_text == "awaiting_approval":
        return "Resolve pending approval"

    if status_text == "running":
        if current_turn_id is not None:
            return "Wait for the current turn to finish"
        return "Send the next prompt"

    if status_text == "failed":
        if session_failure is not None:
            return f"Review failure: {session_failure.error_message}"
        return "Review failed session"

    if status_text == "completed":
        return "Inspect completed session"

    if status_text == "cancelled":
        return "Inspect cancelled session"

    return "Inspect session"
