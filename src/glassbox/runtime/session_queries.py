"""Read-only session query models and service for CLI and web consumers."""

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionStarted
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import PolicyActivitySummary
from glassbox.core.models import ProjectionHealth
from glassbox.core.models import SessionRecord
from glassbox.core.models import SessionState
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.core.models import TurnMetricsRecord
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import ToolExecutionStatus
from glassbox.runtime.context_builder import RuntimeContextSnapshot
from glassbox.runtime.context_builder import build_repository_context_snapshot
from glassbox.runtime.runtime_context_derivation import derive_runtime_context_snapshot
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository

OperatorQueueName = (
    str  # kept broad at runtime; concrete values are constrained at the web boundary
)
OperatorSortName = str

OPERATOR_QUEUE_ALL = "all"
OPERATOR_QUEUE_APPROVALS = "approvals"
OPERATOR_QUEUE_QUESTIONS = "questions"
OPERATOR_QUEUE_FAILURES = "failures"
OPERATOR_QUEUE_DEGRADED = "degraded"
OPERATOR_QUEUE_ACTIVE = "active"
OPERATOR_QUEUE_ACTION_NEEDED = "action-needed"
OPERATOR_QUEUE_HISTORICAL = "historical"

OPERATOR_SORT_PRIORITY = "priority"
OPERATOR_SORT_UPDATED_AT = "updated_at"


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
    projection_health: ProjectionHealth
    next_action_summary: str


class OperatorSessionSummaryView(SessionSummaryView):
    """Operator-console summary row with queue and priority metadata."""

    queue_memberships: list[str] = Field(default_factory=list)
    priority_bucket: str
    priority_rank: int
    action_needed: bool
    live_actionable: bool
    historical_only: bool
    has_active_turn: bool


class SessionQueueCountsView(BaseModel):
    """Aggregate queue counts for the operator console."""

    model_config = ConfigDict(extra="forbid")

    total: int
    approvals: int
    questions: int
    failures: int
    degraded: int
    active: int
    action_needed: int
    historical: int


class ProjectionHealthCountsView(BaseModel):
    """Aggregate projection-health totals for the operator console."""

    model_config = ConfigDict(extra="forbid")

    ok: int = 0
    stale: int = 0
    unavailable: int = 0
    degraded: int = 0


class WorkspaceRuntimeSummaryView(BaseModel):
    """Workspace-level runtime owner summary for operator triage."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: str
    state: str
    health: str | None = None
    pid: int | None = None
    dashboard_url: str | None = None
    health_url: str | None = None
    session_index_url: str | None = None
    started_at: datetime | None = None


class SessionAggregateView(BaseModel):
    """Aggregate operator-console response built from session summaries."""

    model_config = ConfigDict(extra="forbid")

    queue: str | None = None
    status: str | None = None
    sort: str
    limit: int | None = None
    queue_counts: SessionQueueCountsView
    projection_health_counts: ProjectionHealthCountsView
    runtime: WorkspaceRuntimeSummaryView
    sessions: list[OperatorSessionSummaryView] = Field(default_factory=list)


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
    session_policy_summary: PolicyActivitySummary = Field(
        default_factory=PolicyActivitySummary
    )
    current_turn_policy_summary: PolicyActivitySummary | None = None
    turn_metrics: list[TurnMetricsRecord] = Field(default_factory=list)
    runtime_context: RuntimeContextSnapshot
    projection_health: ProjectionHealth


class SessionStatusView(BaseModel):
    """CLI-oriented status read model built from the shared snapshot path."""

    model_config = ConfigDict(extra="forbid")

    snapshot: SessionSnapshotView
    effective_current_turn_id: TurnId | None = None
    current_turn_metrics: TurnMetricsRecord | None = None
    latest_turn_metrics: TurnMetricsRecord | None = None
    latest_turn_policy_summary: PolicyActivitySummary | None = None
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

        projection_health = self._session_repository.inspect_session_projection_health(
            session_id
        )
        projections_available = projection_health.state != "unavailable"
        state = (
            self._session_repository.get_session_state(session_id)
            if projections_available
            else None
        )
        session_events = self._session_repository.read_session_events(session_id)
        transcript = (
            self._session_repository.list_transcript_messages(session_id)
            if projections_available
            else []
        )
        all_tool_calls = (
            self._session_repository.list_tool_calls(session_id)
            if projections_available
            else []
        )
        active_tool_calls = [
            tool_call
            for tool_call in all_tool_calls
            if tool_call.status == ToolExecutionStatus.RUNNING
        ]
        pending_approvals = (
            self._session_repository.list_approvals(
                session_id,
                status=ApprovalStatus.PENDING,
            )
            if projections_available
            else []
        )
        turn_metrics = (
            self._session_repository.list_turn_metrics(
                session_id,
                limit=turn_metrics_limit,
            )
            if projections_available
            else []
        )
        dashboard_url = _dashboard_url_from_events(session_events)
        latest_session_failure = _latest_session_failure(session_events)
        pending_question_id = state.pending_question_id if state is not None else None
        pending_question_text = _pending_question_text_from_events(
            session_events,
            pending_question_id,
        )
        if projections_available:
            (
                can_fork,
                latest_fork_point_turn_id,
                latest_fork_point_sequence,
                fork_blocked_reason,
            ) = _fork_capability(self._session_repository, session_id)
            runtime_context = self._build_runtime_context(record, session_id)
            child_sessions = self._child_session_summaries(session_id)
        else:
            can_fork = False
            latest_fork_point_turn_id = None
            latest_fork_point_sequence = None
            fork_blocked_reason = projection_health.detail
            runtime_context = self._build_degraded_runtime_context(record)
            child_sessions = []

        snapshot_status = _session_status(record, state)
        effective_current_turn_id = _effective_current_turn_id(
            state.current_turn_id if state is not None else None,
            snapshot_status,
            pending_approvals,
        )

        return SessionSnapshotView(
            session_id=record.session_id,
            status=snapshot_status,
            current_turn_id=state.current_turn_id if state is not None else None,
            model_name=record.model_name,
            cwd=str(record.cwd),
            approval_mode=record.approval_mode,
            parent_session_id=record.parent_session_id,
            forked_from_turn_id=record.forked_from_turn_id,
            forked_from_sequence=record.forked_from_sequence,
            branch_label=record.branch_label,
            child_sessions=child_sessions,
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
            session_policy_summary=_summarize_policy_activity(all_tool_calls),
            current_turn_policy_summary=(
                _summarize_policy_activity(
                    all_tool_calls,
                    turn_id=effective_current_turn_id,
                )
                if effective_current_turn_id is not None
                else None
            ),
            turn_metrics=turn_metrics,
            runtime_context=runtime_context,
            projection_health=projection_health,
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
        all_tool_calls = (
            self._session_repository.list_tool_calls(session_id)
            if snapshot.projection_health.state != "unavailable"
            else []
        )
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
        latest_turn_policy_summary = snapshot.current_turn_policy_summary
        if latest_turn_policy_summary is None:
            latest_policy_turn_id = _latest_policy_turn_id(all_tool_calls)
            if latest_policy_turn_id is not None:
                latest_turn_policy_summary = _summarize_policy_activity(
                    all_tool_calls,
                    turn_id=latest_policy_turn_id,
                )

        return SessionStatusView(
            snapshot=snapshot,
            effective_current_turn_id=effective_current_turn_id,
            current_turn_metrics=current_turn_metrics,
            latest_turn_metrics=latest_turn_metrics,
            latest_turn_policy_summary=latest_turn_policy_summary,
            recent_tool_calls=_recent_tool_calls(
                all_tool_calls,
                limit=recent_tool_call_limit,
            ),
            latest_message_summary=_latest_message_summary(snapshot.transcript),
        )

    def get_session_aggregate(
        self,
        *,
        runtime: WorkspaceRuntimeSummaryView,
        queue: OperatorQueueName | None = None,
        status: str | None = None,
        sort: OperatorSortName = OPERATOR_SORT_PRIORITY,
        limit: int | None = None,
    ) -> SessionAggregateView:
        rows = [
            _build_operator_session_summary(summary)
            for summary in self.list_session_summaries()
        ]
        filtered_rows = [
            row
            for row in rows
            if _matches_operator_queue(row, queue)
            and _matches_operator_status(row, status)
        ]
        sorted_rows = _sort_operator_rows(filtered_rows, sort=sort)
        if limit is not None:
            sorted_rows = sorted_rows[:limit]

        return SessionAggregateView(
            queue=queue,
            status=status,
            sort=sort,
            limit=limit,
            queue_counts=_session_queue_counts(rows),
            projection_health_counts=_projection_health_counts(rows),
            runtime=runtime,
            sessions=sorted_rows,
        )

    def _build_session_summary(
        self,
        record: SessionRecord,
        *,
        child_count: int,
    ) -> SessionSummaryView:
        projection_health = self._session_repository.inspect_session_projection_health(
            record.session_id
        )
        projections_available = projection_health.state != "unavailable"
        state = (
            self._session_repository.get_session_state(record.session_id)
            if projections_available
            else None
        )
        session_events = self._session_repository.read_session_events(record.session_id)
        transcript = (
            self._session_repository.list_transcript_messages(record.session_id)
            if projections_available
            else []
        )
        dashboard_url = _dashboard_url_from_events(session_events)
        latest_session_failure = _latest_session_failure(session_events)
        pending_question_id = state.pending_question_id if state is not None else None
        pending_question_text = _pending_question_text_from_events(
            session_events,
            pending_question_id,
        )
        if projections_available:
            (
                can_fork,
                latest_fork_point_turn_id,
                latest_fork_point_sequence,
                fork_blocked_reason,
            ) = _fork_capability(self._session_repository, record.session_id)
        else:
            can_fork = False
            latest_fork_point_turn_id = None
            latest_fork_point_sequence = None
            fork_blocked_reason = projection_health.detail
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
            projection_health=projection_health,
            next_action_summary=_next_action_summary(
                status,
                projection_health=projection_health,
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
        return derive_runtime_context_snapshot(
            self._session_repository,
            session_id,
            record.cwd,
            artifact_repository=self._artifact_repository,
        )

    def _build_degraded_runtime_context(
        self,
        record: SessionRecord,
    ) -> RuntimeContextSnapshot:
        return RuntimeContextSnapshot(
            repository_context=build_repository_context_snapshot(record.cwd),
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
    projection_health: ProjectionHealth,
    pending_question_text: str | None,
    session_failure: SessionFailed | None,
    current_turn_id,
) -> str:
    if projection_health.degraded:
        return "Rebuild derived projections from canonical events"

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


def _latest_policy_turn_id(tool_calls: Sequence[ToolCallRecord]) -> TurnId | None:
    recent_tool_calls = _recent_tool_calls(tool_calls, limit=1)
    if not recent_tool_calls:
        return None
    return recent_tool_calls[0].turn_id


def _summarize_policy_activity(
    tool_calls: Sequence[ToolCallRecord],
    *,
    turn_id: TurnId | None = None,
) -> PolicyActivitySummary:
    summary = PolicyActivitySummary()
    highest_rank = -1
    highest_risk_level = None
    risk_ranks = {
        "read_only": 0,
        "workspace_write": 1,
        "command": 2,
    }

    for tool_call in tool_calls:
        if turn_id is not None and tool_call.turn_id != turn_id:
            continue
        if tool_call.policy_outcome is None or tool_call.policy_risk_level is None:
            continue

        summary.total_decisions += 1
        if tool_call.policy_outcome == "allow":
            summary.allow_count += 1
        elif tool_call.policy_outcome == "approve":
            summary.approve_count += 1
        elif tool_call.policy_outcome == "deny":
            summary.deny_count += 1
        elif tool_call.policy_outcome == "blocked":
            summary.blocked_count += 1

        if tool_call.policy_risk_level == "read_only":
            summary.read_only_count += 1
        elif tool_call.policy_risk_level == "workspace_write":
            summary.workspace_write_count += 1
        elif tool_call.policy_risk_level == "command":
            summary.command_count += 1

        current_rank = risk_ranks.get(tool_call.policy_risk_level, -1)
        if current_rank > highest_rank:
            highest_rank = current_rank
            highest_risk_level = tool_call.policy_risk_level

    summary.highest_risk_level = highest_risk_level
    return summary


def _build_operator_session_summary(
    summary: SessionSummaryView,
) -> OperatorSessionSummaryView:
    has_active_turn = (
        summary.status == "running"
        and summary.next_action_summary == "Wait for the current turn to finish"
    )
    live_actionable = summary.status in {
        "running",
        "awaiting_approval",
        "awaiting_user_input",
    }
    historical_only = not live_actionable
    priority_bucket, priority_rank = _operator_priority(summary, has_active_turn)
    action_needed = bool(
        summary.pending_approval_id is not None
        or summary.pending_question_id is not None
        or summary.status == "failed"
        or summary.projection_health.degraded
    )
    queue_memberships = _operator_queue_memberships(
        summary,
        live_actionable=live_actionable,
        historical_only=historical_only,
        action_needed=action_needed,
    )

    payload = summary.model_dump()
    payload.update(
        {
            "queue_memberships": queue_memberships,
            "priority_bucket": priority_bucket,
            "priority_rank": priority_rank,
            "action_needed": action_needed,
            "live_actionable": live_actionable,
            "historical_only": historical_only,
            "has_active_turn": has_active_turn,
        }
    )
    return OperatorSessionSummaryView.model_validate(payload)


def _operator_priority(
    summary: SessionSummaryView,
    has_active_turn: bool,
) -> tuple[str, int]:
    if summary.pending_approval_id is not None:
        return "approvals", 0
    if summary.pending_question_id is not None:
        return "questions", 1
    if summary.status == "failed":
        return "failures", 2
    if summary.projection_health.degraded:
        return "degraded", 3
    if has_active_turn:
        return "running", 4
    if summary.status == "running":
        return "idle_running", 5
    return "historical", 6


def _matches_operator_queue(
    row: OperatorSessionSummaryView,
    queue: OperatorQueueName | None,
) -> bool:
    if queue is None or queue == OPERATOR_QUEUE_ALL:
        return True
    return queue in row.queue_memberships


def _matches_operator_status(
    row: OperatorSessionSummaryView,
    status: str | None,
) -> bool:
    return status is None or row.status == status


def _sort_operator_rows(
    rows: Sequence[OperatorSessionSummaryView],
    *,
    sort: OperatorSortName,
) -> list[OperatorSessionSummaryView]:
    if sort == OPERATOR_SORT_UPDATED_AT:
        return sorted(
            rows,
            key=lambda row: (
                -row.updated_at.replace(tzinfo=UTC).timestamp(),
                row.priority_rank,
                str(row.session_id),
            ),
        )

    return sorted(
        rows,
        key=lambda row: (
            row.priority_rank,
            -row.updated_at.replace(tzinfo=UTC).timestamp(),
            str(row.session_id),
        ),
    )


def _operator_queue_memberships(
    summary: SessionSummaryView,
    *,
    live_actionable: bool,
    historical_only: bool,
    action_needed: bool,
) -> list[str]:
    queue_memberships: list[str] = []
    if summary.pending_approval_id is not None:
        queue_memberships.append(OPERATOR_QUEUE_APPROVALS)
    if summary.pending_question_id is not None:
        queue_memberships.append(OPERATOR_QUEUE_QUESTIONS)
    if summary.status == "failed":
        queue_memberships.append(OPERATOR_QUEUE_FAILURES)
    if summary.projection_health.degraded:
        queue_memberships.append(OPERATOR_QUEUE_DEGRADED)
    if live_actionable:
        queue_memberships.append(OPERATOR_QUEUE_ACTIVE)
    if action_needed:
        queue_memberships.append(OPERATOR_QUEUE_ACTION_NEEDED)
    if historical_only:
        queue_memberships.append(OPERATOR_QUEUE_HISTORICAL)
    return queue_memberships


def _queue_count(
    rows: Sequence[OperatorSessionSummaryView],
    queue_name: str,
) -> int:
    return sum(queue_name in row.queue_memberships for row in rows)


def _session_queue_counts(
    rows: Sequence[OperatorSessionSummaryView],
) -> SessionQueueCountsView:
    return SessionQueueCountsView(
        total=len(rows),
        approvals=_queue_count(rows, OPERATOR_QUEUE_APPROVALS),
        questions=_queue_count(rows, OPERATOR_QUEUE_QUESTIONS),
        failures=_queue_count(rows, OPERATOR_QUEUE_FAILURES),
        degraded=_queue_count(rows, OPERATOR_QUEUE_DEGRADED),
        active=_queue_count(rows, OPERATOR_QUEUE_ACTIVE),
        action_needed=_queue_count(rows, OPERATOR_QUEUE_ACTION_NEEDED),
        historical=_queue_count(rows, OPERATOR_QUEUE_HISTORICAL),
    )


def _projection_health_counts(
    rows: Sequence[OperatorSessionSummaryView],
) -> ProjectionHealthCountsView:
    counts = ProjectionHealthCountsView()
    for row in rows:
        state = row.projection_health.state
        if state == "ok":
            counts.ok += 1
        elif state == "stale":
            counts.stale += 1
        elif state == "unavailable":
            counts.unavailable += 1
        if row.projection_health.degraded:
            counts.degraded += 1
    return counts
