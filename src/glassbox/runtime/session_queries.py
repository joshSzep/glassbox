"""Read-only session query models and service for CLI and web consumers."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from glassbox.core.events import (
    EventEnvelope,
    SessionFailed,
    SessionStarted,
    TurnCompleted,
    TurnStarted,
    UserMessageReceived,
    UserQuestionAsked,
)
from glassbox.core.ids import SessionId, TurnId
from glassbox.core.models import (
    ApprovalRecord,
    SessionRecord,
    SessionState,
    ToolCallRecord,
    TranscriptMessage,
    TurnMetricsRecord,
)
from glassbox.core.types import ApprovalStatus, ToolExecutionStatus
from glassbox.runtime.context_builder import (
    RuntimeContextSnapshot,
    build_artifact_backed_context_snapshot,
    build_runtime_context_snapshot,
    build_working_set_snapshot,
)
from glassbox.services import ArtifactRepository, SessionRepository


class ChildSessionSummaryView(BaseModel):
    """Read-model summary for child sessions in a snapshot."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    status: str
    branch_label: str | None = None
    updated_at: datetime
    latest_message_summary: str | None = None


class BranchableTurnView(BaseModel):
    """Read-model summary for completed turns that can be forked."""

    model_config = ConfigDict(extra="forbid")

    turn_id: TurnId
    sequence: int
    created_at: datetime
    label: str


class SessionSummaryView(BaseModel):
    """Query-friendly summary used by the session index."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    status: str
    model_name: str
    cwd: str
    approval_mode: str
    parent_session_id: SessionId | None = None
    forked_from_turn_id: TurnId | None = None
    forked_from_sequence: int | None = None
    branch_label: str | None = None
    child_session_count: int = 0
    can_fork: bool
    latest_fork_point_turn_id: TurnId | None = None
    latest_fork_point_sequence: int | None = None
    fork_blocked_reason: str | None = None
    dashboard_url: str | None = None
    created_at: datetime
    updated_at: datetime
    last_sequence: int
    pending_approval_id: str | None = None
    pending_question_id: str | None = None
    pending_question_text: str | None = None
    session_failure_message: str | None = None
    session_failure_retryable: bool | None = None
    latest_message_summary: str | None = None
    next_action_summary: str


class SessionSnapshotView(BaseModel):
    """Query-friendly session snapshot shared by CLI and web consumers."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    status: str
    current_turn_id: TurnId | None = None
    model_name: str
    cwd: str
    approval_mode: str
    parent_session_id: SessionId | None = None
    forked_from_turn_id: TurnId | None = None
    forked_from_sequence: int | None = None
    branch_label: str | None = None
    child_sessions: list[ChildSessionSummaryView] = Field(default_factory=list)
    branchable_turns: list[BranchableTurnView] = Field(default_factory=list)
    can_fork: bool
    latest_fork_point_turn_id: TurnId | None = None
    latest_fork_point_sequence: int | None = None
    fork_blocked_reason: str | None = None
    dashboard_url: str | None = None
    created_at: datetime
    updated_at: datetime
    last_sequence: int
    pending_approval_id: str | None = None
    pending_question_id: str | None = None
    pending_question_text: str | None = None
    session_failure_message: str | None = None
    session_failure_retryable: bool | None = None
    transcript: list[TranscriptMessage] = Field(default_factory=list)
    active_tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    pending_approvals: list[ApprovalRecord] = Field(default_factory=list)
    turn_metrics: list[TurnMetricsRecord] = Field(default_factory=list)
    runtime_context: RuntimeContextSnapshot


class SessionStatusView(BaseModel):
    """CLI-oriented status read model built from the shared snapshot path."""

    model_config = ConfigDict(extra="forbid")

    snapshot: SessionSnapshotView
    effective_current_turn_id: TurnId | None = None
    current_turn_metrics: TurnMetricsRecord | None = None
    latest_turn_metrics: TurnMetricsRecord | None = None
    recent_tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    latest_message_summary: str | None = None


class SessionQueryService:
    """Build shared session summaries and snapshots from repository projections."""

    def __init__(
        self,
        session_repository: SessionRepository,
        artifact_repository: ArtifactRepository,
    ) -> None:
        self._session_repository = session_repository
        self._artifact_repository = artifact_repository

    def list_session_summaries(self) -> list[SessionSummaryView]:
        records = self._session_repository.list_sessions()
        child_counts_by_parent = _child_counts_by_parent(records)
        return [
            self._build_session_summary(
                record,
                child_count=child_counts_by_parent.get(str(record.session_id), 0),
            )
            for record in records
        ]

    def get_session_snapshot(
        self,
        session_id: SessionId,
        *,
        turn_metrics_limit: int = 10,
    ) -> SessionSnapshotView:
        record = self._session_repository.get_session(session_id)
        if record is None:
            raise ValueError(f"session {session_id} not found")

        state = self._session_repository.get_session_state(session_id)
        session_events = self._session_repository.read_session_events(session_id)
        transcript = self._session_repository.list_transcript_messages(session_id)
        active_tool_calls = self._session_repository.list_tool_calls(
            session_id,
            status=ToolExecutionStatus.RUNNING,
        )
        pending_approvals = self._session_repository.list_approvals(
            session_id,
            status=ApprovalStatus.PENDING,
        )
        turn_metrics = self._session_repository.list_turn_metrics(
            session_id,
            limit=turn_metrics_limit,
        )
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
        ) = _fork_capability(self._session_repository, session_id)
        runtime_context = self._build_runtime_context(record, session_id)

        return SessionSnapshotView(
            session_id=record.session_id,
            status=_session_status(record, state),
            current_turn_id=state.current_turn_id if state is not None else None,
            model_name=record.model_name,
            cwd=str(record.cwd),
            approval_mode=record.approval_mode,
            parent_session_id=record.parent_session_id,
            forked_from_turn_id=record.forked_from_turn_id,
            forked_from_sequence=record.forked_from_sequence,
            branch_label=record.branch_label,
            child_sessions=self._child_session_summaries(session_id),
            branchable_turns=(
                _branchable_turns_from_events(session_events) if can_fork else []
            ),
            can_fork=can_fork,
            latest_fork_point_turn_id=latest_fork_point_turn_id,
            latest_fork_point_sequence=latest_fork_point_sequence,
            fork_blocked_reason=fork_blocked_reason,
            dashboard_url=dashboard_url,
            created_at=record.created_at,
            updated_at=record.updated_at,
            last_sequence=_last_sequence(record, state),
            pending_approval_id=(
                str(state.pending_approval_id)
                if state is not None and state.pending_approval_id is not None
                else None
            ),
            pending_question_id=(
                str(state.pending_question_id)
                if state is not None and state.pending_question_id is not None
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
            transcript=transcript,
            active_tool_calls=active_tool_calls,
            pending_approvals=pending_approvals,
            turn_metrics=turn_metrics,
            runtime_context=runtime_context,
        )

    def get_session_status_view(
        self,
        session_id: SessionId,
        *,
        turn_metrics_limit: int = 5,
        recent_tool_call_limit: int = 3,
    ) -> SessionStatusView:
        snapshot = self.get_session_snapshot(
            session_id,
            turn_metrics_limit=turn_metrics_limit,
        )
        all_tool_calls = self._session_repository.list_tool_calls(session_id)
        effective_current_turn_id = _effective_current_turn_id(
            snapshot.current_turn_id,
            snapshot.status,
            snapshot.pending_approvals,
        )
        current_turn_metrics = _find_turn_metrics(
            snapshot.turn_metrics,
            effective_current_turn_id,
        )
        latest_turn_metrics = current_turn_metrics or (
            snapshot.turn_metrics[0] if snapshot.turn_metrics else None
        )

        return SessionStatusView(
            snapshot=snapshot,
            effective_current_turn_id=effective_current_turn_id,
            current_turn_metrics=current_turn_metrics,
            latest_turn_metrics=latest_turn_metrics,
            recent_tool_calls=_recent_tool_calls(
                all_tool_calls,
                limit=recent_tool_call_limit,
            ),
            latest_message_summary=_latest_message_summary(snapshot.transcript),
        )

    def _build_session_summary(
        self,
        record: SessionRecord,
        *,
        child_count: int,
    ) -> SessionSummaryView:
        state = self._session_repository.get_session_state(record.session_id)
        session_events = self._session_repository.read_session_events(record.session_id)
        transcript = self._session_repository.list_transcript_messages(
            record.session_id
        )
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
        ) = _fork_capability(self._session_repository, record.session_id)
        status = _session_status(record, state)

        return SessionSummaryView(
            session_id=record.session_id,
            status=status,
            model_name=record.model_name,
            cwd=str(record.cwd),
            approval_mode=record.approval_mode,
            parent_session_id=record.parent_session_id,
            forked_from_turn_id=record.forked_from_turn_id,
            forked_from_sequence=record.forked_from_sequence,
            branch_label=record.branch_label,
            child_session_count=child_count,
            can_fork=can_fork,
            latest_fork_point_turn_id=latest_fork_point_turn_id,
            latest_fork_point_sequence=latest_fork_point_sequence,
            fork_blocked_reason=fork_blocked_reason,
            dashboard_url=dashboard_url,
            created_at=record.created_at,
            updated_at=record.updated_at,
            last_sequence=_last_sequence(record, state),
            pending_approval_id=(
                str(state.pending_approval_id)
                if state is not None and state.pending_approval_id is not None
                else None
            ),
            pending_question_id=(
                str(state.pending_question_id)
                if state is not None and state.pending_question_id is not None
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
                status,
                pending_question_text=pending_question_text,
                session_failure=latest_session_failure,
                current_turn_id=state.current_turn_id if state is not None else None,
            ),
        )

    def _build_runtime_context(
        self,
        record: SessionRecord,
        session_id: SessionId,
    ) -> RuntimeContextSnapshot:
        return build_runtime_context_snapshot(
            record.cwd,
            self._session_repository.list_runtime_notes(session_id),
            working_set=build_working_set_snapshot(
                self._session_repository,
                session_id,
            ),
            artifact_context=build_artifact_backed_context_snapshot(
                self._session_repository,
                self._artifact_repository,
                session_id,
            ),
        )

    def _child_session_summaries(
        self,
        session_id: SessionId,
    ) -> list[ChildSessionSummaryView]:
        child_records = [
            record
            for record in self._session_repository.list_sessions()
            if record.parent_session_id == session_id
        ]
        child_records.sort(key=lambda record: record.updated_at, reverse=True)

        return [
            ChildSessionSummaryView(
                session_id=record.session_id,
                status=record.status,
                branch_label=record.branch_label,
                updated_at=record.updated_at,
                latest_message_summary=_latest_message_summary(
                    self._session_repository.list_transcript_messages(record.session_id)
                ),
            )
            for record in child_records
        ]


def _child_counts_by_parent(records: Sequence[SessionRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        if record.parent_session_id is None:
            continue
        parent_session_id = str(record.parent_session_id)
        counts[parent_session_id] = counts.get(parent_session_id, 0) + 1
    return counts


def _branchable_turns_from_events(
    events: Sequence[EventEnvelope],
) -> list[BranchableTurnView]:
    user_messages_by_id: dict[str, str] = {}
    trigger_message_ids_by_turn: dict[str, str] = {}
    branchable_turns: list[BranchableTurnView] = []

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
            BranchableTurnView(
                turn_id=event.payload.turn_id,
                sequence=event.sequence,
                created_at=event.created_at,
                label=label,
            )
        )

    branchable_turns.sort(key=lambda turn: turn.sequence, reverse=True)
    return branchable_turns


def _dashboard_url_from_events(events: Sequence[EventEnvelope]) -> str | None:
    for event in events:
        if isinstance(event.payload, SessionStarted):
            return event.payload.dashboard_url
    return None


def _fork_capability(
    session_repository: SessionRepository,
    session_id: SessionId,
) -> tuple[bool, TurnId | None, int | None, str | None]:
    try:
        fork_point = session_repository.resolve_fork_point(session_id)
    except ValueError as exc:
        return False, None, None, str(exc)

    return True, fork_point.turn_id, fork_point.sequence, None


def _latest_message_summary(transcript: Sequence[TranscriptMessage]) -> str | None:
    if not transcript:
        return None

    latest_message = transcript[-1]
    text = " ".join(
        part.text.strip().replace("\n", " ")
        for part in latest_message.parts
        if part.text.strip()
    ).strip()
    if not text:
        return latest_message.role
    return f"{latest_message.role}: {text}"


def _latest_session_failure(events: Sequence[EventEnvelope]) -> SessionFailed | None:
    for event in reversed(events):
        if isinstance(event.payload, SessionFailed):
            return event.payload
    return None


def _pending_question_text_from_events(
    events: Sequence[EventEnvelope],
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


def _next_action_summary(
    status: str,
    *,
    pending_question_text: str | None,
    session_failure: SessionFailed | None,
    current_turn_id,
) -> str:
    if status == "awaiting_user_input":
        if pending_question_text is not None:
            return f"Answer pending question: {pending_question_text}"
        return "Answer pending question"

    if status == "awaiting_approval":
        return "Resolve pending approval"

    if status == "running":
        if current_turn_id is not None:
            return "Wait for the current turn to finish"
        return "Send the next prompt"

    if status == "failed":
        if session_failure is not None:
            return f"Review failure: {session_failure.error_message}"
        return "Review failed session"

    if status == "completed":
        return "Inspect completed session"

    if status == "cancelled":
        return "Inspect cancelled session"

    return "Inspect session"


def _session_status(record: SessionRecord, state: SessionState | None) -> str:
    return state.status if state is not None else record.status


def _last_sequence(record: SessionRecord, state: SessionState | None) -> int:
    return state.last_sequence if state is not None else record.last_sequence


def _effective_current_turn_id(
    current_turn_id: TurnId | None,
    status: str,
    approvals: Sequence[ApprovalRecord],
) -> TurnId | None:
    if current_turn_id is not None:
        return current_turn_id
    if status == "awaiting_approval" and approvals:
        return approvals[-1].turn_id
    return None


def _find_turn_metrics(
    turn_metrics: Sequence[TurnMetricsRecord],
    turn_id: TurnId | None,
) -> TurnMetricsRecord | None:
    if turn_id is None:
        return None
    for metrics in turn_metrics:
        if metrics.turn_id == turn_id:
            return metrics
    return None


def _recent_tool_calls(
    tool_calls: Sequence[ToolCallRecord],
    *,
    limit: int,
) -> list[ToolCallRecord]:
    def sort_key(tool_call: ToolCallRecord) -> datetime:
        return tool_call.completed_at or tool_call.started_at or datetime.min

    return sorted(tool_calls, key=sort_key, reverse=True)[:limit]
