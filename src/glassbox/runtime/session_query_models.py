"""Read-only session query view models shared by CLI and web consumers."""

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import PolicyActivitySummary
from glassbox.core.models import ProjectionHealth
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.core.models import TurnMetricsRecord
from glassbox.runtime.context_builder import RuntimeContextSnapshot

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
