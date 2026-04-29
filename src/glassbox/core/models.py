"""Core Pydantic domain models for Glassbox."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from glassbox.core.ids import ApprovalId
from glassbox.core.ids import MessageId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskStepId
from glassbox.core.ids import TaskVerificationId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.types import ApprovalMode
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import SessionStatus
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import ToolExecutionStatus

MessagePartKind = Literal["text", "tool_result", "reasoning_summary"]
MessageRole = Literal["user", "assistant", "system"]
PolicyDecisionOutcome = Literal["allow", "approve", "deny", "blocked"]
PolicyRiskLevel = Literal["read_only", "workspace_write", "command"]
PolicyDecisionSourceKind = Literal["default", "rule", "invariant"]


class SessionConfig(BaseModel):
    """Session-scoped configuration for a Glassbox runtime."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    cwd: Path
    approval_mode: str
    dashboard_url: str | None = None
    parent_session_id: SessionId | None = None
    forked_from_turn_id: TurnId | None = None
    forked_from_sequence: int | None = Field(default=None, ge=0)
    branch_label: str | None = None

    @field_validator("approval_mode")
    @classmethod
    def validate_approval_mode(cls, value: str) -> str:
        return ApprovalMode(value).value


class SessionState(BaseModel):
    """Current runtime-facing state for a session."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    status: SessionStatus
    current_turn_id: TurnId | None = None
    last_sequence: int = Field(default=0, ge=0)
    pending_approval_id: ApprovalId | None = None
    pending_question_id: QuestionId | None = None


class SessionRecord(BaseModel):
    """Coarse persisted metadata for listing and resuming sessions."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    cwd: Path
    model_name: str
    approval_mode: str
    last_sequence: int = Field(default=0, ge=0)
    parent_session_id: SessionId | None = None
    forked_from_turn_id: TurnId | None = None
    forked_from_sequence: int | None = Field(default=None, ge=0)
    branch_label: str | None = None


class ProjectionHealth(BaseModel):
    """Health summary for derived session projection state."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["ok", "stale", "unavailable"]
    canonical_last_sequence: int = Field(ge=0)
    projected_last_sequence: int | None = Field(default=None, ge=0)
    lag: int = Field(default=0, ge=0)
    estimated_rebuild_event_count: int = Field(default=0, ge=0)
    projected_progress_ratio: float | None = Field(default=None, ge=0, le=1)
    degraded: bool = False
    detail: str | None = None


class MessagePart(BaseModel):
    """A typed part of a transcript message."""

    model_config = ConfigDict(extra="forbid")

    kind: MessagePartKind
    text: str


class TranscriptMessage(BaseModel):
    """A normalized message stored in or projected from a session transcript."""

    model_config = ConfigDict(extra="forbid")

    message_id: MessageId
    role: MessageRole
    parts: list[MessagePart]
    created_at: datetime


class RuntimeNoteRecord(BaseModel):
    """A query-friendly view of an active runtime note."""

    model_config = ConfigDict(extra="forbid")

    source_session_id: SessionId
    source_sequence: int = Field(ge=0)
    category: str
    message: str
    created_at: datetime
    inherited: bool = False


class InheritedTranscriptMessage(BaseModel):
    """Normalized transcript content inherited from a parent session."""

    model_config = ConfigDict(extra="forbid")

    source_message_id: MessageId
    source_turn_id: TurnId | None = None
    role: MessageRole
    parts: list[MessagePart]
    created_at: datetime


class ResolvedForkPoint(BaseModel):
    """A validated historical fork boundary resolved from persisted session data."""

    model_config = ConfigDict(extra="forbid")

    parent_session_id: SessionId
    turn_id: TurnId
    sequence: int = Field(ge=0)
    inherited_messages: list[InheritedTranscriptMessage]


class ForkedSession(BaseModel):
    """Summary of a newly created child session fork."""

    model_config = ConfigDict(extra="forbid")

    child_session_id: SessionId
    parent_session_id: SessionId
    forked_from_turn_id: TurnId
    forked_from_sequence: int = Field(ge=0)
    branch_label: str | None = None
    inherited_message_count: int = Field(default=0, ge=0)
    last_sequence: int = Field(default=0, ge=0)


class ToolCallRecord(BaseModel):
    """A query-friendly view of a tool call in a turn."""

    model_config = ConfigDict(extra="forbid")

    tool_call_id: ToolCallId
    turn_id: TurnId
    tool_name: str
    status: ToolExecutionStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: str | None = None
    exit_code: int | None = None
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None
    policy_reason: str | None = None


class ApprovalRecord(BaseModel):
    """A query-friendly view of an approval request."""

    model_config = ConfigDict(extra="forbid")

    approval_id: ApprovalId
    turn_id: TurnId
    subject: str
    reason: str
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None
    status: ApprovalStatus
    requested_at: datetime
    resolved_at: datetime | None = None
    decided_by: str | None = None


class TurnMetricsRecord(BaseModel):
    """Aggregated per-turn runtime metrics derived from persisted events."""

    model_config = ConfigDict(extra="forbid")

    turn_id: TurnId
    started_at: datetime | None = None
    completed_at: datetime | None = None
    turn_duration_ms: int | None = None
    model_call_count: int = Field(default=0, ge=0)
    model_duration_ms_total: int = Field(default=0, ge=0)
    model_input_tokens_total: int = Field(default=0, ge=0)
    model_output_tokens_total: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    tool_duration_ms_total: int = Field(default=0, ge=0)
    succeeded_tool_call_count: int = Field(default=0, ge=0)
    failed_tool_call_count: int = Field(default=0, ge=0)


class PolicyDecision(BaseModel):
    """The result of evaluating whether a tool action is allowed."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    requires_approval: bool
    reason: str
    outcome: PolicyDecisionOutcome
    risk_level: PolicyRiskLevel
    source_kind: PolicyDecisionSourceKind
    source_label: str


class PolicyDecisionTrace(BaseModel):
    """Persistable explanation of one tool-policy decision."""

    model_config = ConfigDict(extra="forbid")

    outcome: PolicyDecisionOutcome
    risk_level: PolicyRiskLevel
    source_kind: PolicyDecisionSourceKind
    source_label: str
    reason: str

    @classmethod
    def from_decision(cls, decision: PolicyDecision) -> PolicyDecisionTrace:
        return cls(
            outcome=decision.outcome,
            risk_level=decision.risk_level,
            source_kind=decision.source_kind,
            source_label=decision.source_label,
            reason=decision.reason,
        )


class TaskStepProposal(BaseModel):
    """A proposed task-plan step before it is executed."""

    model_config = ConfigDict(extra="forbid")

    step_id: TaskStepId
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    order: int = Field(ge=0)


class TaskPlanSnapshot(BaseModel):
    """A structured plan proposal owned by the runtime."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=4000)
    status: TaskPlanStatus = TaskPlanStatus.PROPOSED
    steps: list[TaskStepProposal] = Field(default_factory=list, max_length=50)


class TaskStepRecord(BaseModel):
    """A query-friendly view of a durable task step."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    step_id: TaskStepId
    title: str
    order: int = Field(ge=0)
    status: TaskStepStatus
    description: str | None = None
    blocked_reason: TaskBlockedReason | None = None


class TaskVerificationRecord(BaseModel):
    """A query-friendly view of a task verification run."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    verification_id: TaskVerificationId
    step_id: TaskStepId | None = None
    status: TaskVerificationStatus
    check_name: str
    summary: str | None = None


class PolicyActivitySummary(BaseModel):
    """Concise session or turn summary of policy decisions."""

    model_config = ConfigDict(extra="forbid")

    total_decisions: int = Field(default=0, ge=0)
    allow_count: int = Field(default=0, ge=0)
    approve_count: int = Field(default=0, ge=0)
    deny_count: int = Field(default=0, ge=0)
    blocked_count: int = Field(default=0, ge=0)
    read_only_count: int = Field(default=0, ge=0)
    workspace_write_count: int = Field(default=0, ge=0)
    command_count: int = Field(default=0, ge=0)
    highest_risk_level: PolicyRiskLevel | None = None
