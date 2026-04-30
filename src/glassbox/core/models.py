"""Core Pydantic domain models for Glassbox."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.core.ids import ApprovalId
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import BackgroundJobId
from glassbox.core.ids import BranchCandidateId
from glassbox.core.ids import BranchSearchId
from glassbox.core.ids import ContextCompactionId
from glassbox.core.ids import MessageId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskCheckpointId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskStepId
from glassbox.core.ids import TaskVerificationId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.types import ApprovalMode
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import AutonomyMode
from glassbox.core.types import BackgroundJobFailureKind
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import BackgroundJobRecoveryReason
from glassbox.core.types import BackgroundJobState
from glassbox.core.types import BranchCandidateStatus
from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.core.types import BranchSearchStatus
from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope
from glassbox.core.types import LongRunPhase
from glassbox.core.types import RepositoryIndexEntityKind
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import SessionStatus
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import ToolAttemptStatus
from glassbox.core.types import ToolExecutionStatus
from glassbox.core.types import TurnRecoveryState
from glassbox.core.types import VerificationCheckKind
from glassbox.core.types import VerificationFailureCategory
from glassbox.core.types import VerificationPlanSource
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemorySourceType
from glassbox.core.types import WorkspaceMemoryState

MessagePartKind = Literal["text", "tool_result", "reasoning_summary"]
MessageRole = Literal["user", "assistant", "system"]
PolicyDecisionOutcome = Literal["allow", "approve", "deny", "blocked"]
PolicyRiskLevel = Literal["read_only", "workspace_write", "command"]
PolicyDecisionSourceKind = Literal["default", "rule", "invariant"]


class AutonomyBudget(BaseModel):
    """Explicit local limits for one autonomy mode selection."""

    model_config = ConfigDict(extra="forbid")

    max_steps: int = Field(ge=0)
    max_tool_calls: int = Field(ge=0)
    max_write_operations: int = Field(ge=0)
    max_command_operations: int = Field(ge=0)
    max_wall_clock_seconds: int = Field(ge=1)
    max_verification_attempts: int = Field(ge=0)
    max_branch_attempts: int = Field(ge=0)
    max_artifact_bytes: int = Field(ge=0)
    allowed_risk_buckets: list[PolicyRiskLevel] = Field(min_length=1)

    @field_validator("allowed_risk_buckets")
    @classmethod
    def normalize_allowed_risk_buckets(
        cls,
        value: list[PolicyRiskLevel],
    ) -> list[PolicyRiskLevel]:
        normalized = list(dict.fromkeys(value))
        if not normalized:
            raise ValueError("allowed_risk_buckets must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_budget_consistency(self) -> AutonomyBudget:
        allowed = set(self.allowed_risk_buckets)
        if self.max_write_operations > 0 and "workspace_write" not in allowed:
            raise ValueError(
                "max_write_operations requires workspace_write in allowed_risk_buckets"
            )
        if self.max_command_operations > 0 and "command" not in allowed:
            raise ValueError(
                "max_command_operations requires command in allowed_risk_buckets"
            )
        if "workspace_write" in allowed and self.max_write_operations == 0:
            raise ValueError(
                "workspace_write risk requires a positive max_write_operations budget"
            )
        if "command" in allowed and self.max_command_operations == 0:
            raise ValueError(
                "command risk requires a positive max_command_operations budget"
            )
        return self


class AutonomySelection(BaseModel):
    """Resolved autonomy mode and budget ready for policy/budget checks."""

    model_config = ConfigDict(extra="forbid")

    mode: AutonomyMode
    budget: AutonomyBudget
    escalation_reasons: list[AutonomyEscalationReason] = Field(
        default_factory=lambda: [
            AutonomyEscalationReason.APPROVAL_REQUIRED,
            AutonomyEscalationReason.BUDGET_EXHAUSTED,
            AutonomyEscalationReason.POLICY_BLOCKED,
            AutonomyEscalationReason.VERIFICATION_FAILED,
            AutonomyEscalationReason.PROVIDER_UNAVAILABLE,
            AutonomyEscalationReason.DAEMON_UNAVAILABLE,
            AutonomyEscalationReason.AMBIGUOUS_PLAN,
        ]
    )


class AutonomyBudgetUsage(BaseModel):
    """Current budget usage counters for a session or task."""

    model_config = ConfigDict(extra="forbid")

    steps: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    write_operations: int = Field(default=0, ge=0)
    command_operations: int = Field(default=0, ge=0)
    wall_clock_seconds: int = Field(default=0, ge=0)
    verification_attempts: int = Field(default=0, ge=0)
    branch_attempts: int = Field(default=0, ge=0)
    artifact_bytes: int = Field(default=0, ge=0)


class AutonomyBudgetRemaining(BaseModel):
    """Remaining budget counters after one decision."""

    model_config = ConfigDict(extra="forbid")

    steps: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    write_operations: int = Field(ge=0)
    command_operations: int = Field(ge=0)
    wall_clock_seconds: int = Field(ge=0)
    verification_attempts: int = Field(ge=0)
    branch_attempts: int = Field(ge=0)
    artifact_bytes: int = Field(ge=0)


class AutonomyBudgetPostureRecord(BaseModel):
    """Latest projected autonomy budget posture for a session or task."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    task_id: TaskId | None = None
    mode: AutonomyMode | None = None
    budget: AutonomyBudget | None = None
    usage: AutonomyBudgetUsage
    remaining: AutonomyBudgetRemaining | None = None
    last_decision: str
    last_reason: AutonomyEscalationReason | None = None
    last_limit_name: str | None = None
    last_detail: str | None = None
    last_sequence: int = Field(ge=0)
    updated_at: datetime


class SessionConfig(BaseModel):
    """Session-scoped configuration for a Glassbox runtime."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    cwd: Path
    approval_mode: str
    autonomy_mode: AutonomyMode = AutonomyMode.MANUAL
    autonomy_budget: AutonomyBudget | None = None
    autonomy_budget_preset: str | None = None
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


class TurnRecoveryPosture(BaseModel):
    """Derived recovery posture for the latest relevant turn in a session."""

    model_config = ConfigDict(extra="forbid")

    turn_id: TurnId
    state: TurnRecoveryState
    safe_to_resume: bool | None = None
    reason: str | None = Field(default=None, max_length=2000)
    next_action: str = Field(min_length=1, max_length=2000)
    source_event_type: str | None = None
    recovery_decision_id: str | None = None


class TaskCheckpointRecord(BaseModel):
    """Projected durable checkpoint for task or session handoff."""

    model_config = ConfigDict(extra="forbid")

    checkpoint_id: TaskCheckpointId
    session_id: SessionId
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    tool_attempt_id: ToolAttemptId | None = None
    compaction_id: ContextCompactionId | None = None
    artifact_id: ArtifactId | None = None
    objective: str = Field(min_length=1, max_length=4000)
    current_phase: LongRunPhase | None = None
    completed_step: str | None = Field(default=None, max_length=2000)
    next_action: str = Field(min_length=1, max_length=2000)
    blockers: list[str] = Field(default_factory=list)
    touched_files: list[str] = Field(default_factory=list)
    verification_status: str | None = Field(default=None, max_length=200)
    budget_status: str | None = Field(default=None, max_length=200)
    recovery_guidance: str = Field(min_length=1, max_length=4000)
    source_start_sequence: int = Field(ge=0)
    source_end_sequence: int = Field(ge=0)
    created_at: datetime
    last_sequence: int = Field(ge=0)


class ContextCompactionRecord(BaseModel):
    """Projected state for one artifact-backed context compaction."""

    model_config = ConfigDict(extra="forbid")

    compaction_id: ContextCompactionId
    session_id: SessionId
    scope: ContextCompactionScope
    source_start_sequence: int = Field(ge=0)
    source_end_sequence: int = Field(ge=0)
    summary: str = Field(min_length=1, max_length=4000)
    artifact_id: ArtifactId
    artifact_schema_version: int = Field(ge=1)
    freshness: ContextCompactionFreshness
    freshness_reason: str | None = Field(default=None, max_length=2000)
    superseded_by_compaction_id: ContextCompactionId | None = None
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    source_artifact_ids: list[ArtifactId] = Field(default_factory=list)
    decision_count: int = Field(default=0, ge=0)
    unresolved_question_count: int = Field(default=0, ge=0)
    accepted_risk_count: int = Field(default=0, ge=0)
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime
    last_sequence: int = Field(ge=0)


class BackgroundJobRecord(BaseModel):
    """Projected state for one daemon-owned background job."""

    model_config = ConfigDict(extra="forbid")

    job_id: BackgroundJobId
    session_id: SessionId
    state: BackgroundJobState
    kind: BackgroundJobKind
    job_type: str
    title: str
    requested_by: str
    payload: dict[str, object] = Field(default_factory=dict)
    priority: int = Field(ge=0)
    task_id: TaskId | None = None
    parent_job_id: BackgroundJobId | None = None
    worker_id: str | None = None
    claim_token: str | None = None
    attempt: int = Field(default=0, ge=0)
    lease_expires_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    progress_message: str | None = None
    completed_units: int | None = Field(default=None, ge=0)
    total_units: int | None = Field(default=None, ge=0)
    failure_kind: BackgroundJobFailureKind | None = None
    failure_message: str | None = None
    failure_artifact_id: ArtifactId | None = None
    failure_artifact_path: str | None = None
    retryable: bool = False
    next_retry_at: datetime | None = None
    cancellation_requested_by: str | None = None
    cancellation_reason: str | None = None
    cancelled_by: str | None = None
    recovery_reason: BackgroundJobRecoveryReason | None = None
    recovery_detail: str | None = None
    retry_requested_by: str | None = None
    retry_reason: str | None = None
    retry_exhausted_reason: str | None = None
    retry_budget: int | None = Field(default=None, ge=0)
    abandoned_by: str | None = None
    abandoned_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_sequence: int = Field(ge=0)


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


class WorkspaceMemoryProvenance(BaseModel):
    """Inspectable source evidence for one workspace memory entry."""

    model_config = ConfigDict(extra="forbid")

    source_type: WorkspaceMemorySourceType
    source_label: str | None = Field(default=None, max_length=500)
    session_id: SessionId | None = None
    source_sequence: int | None = Field(default=None, ge=0)
    task_id: TaskId | None = None
    artifact_id: ArtifactId | None = None
    tool_call_id: ToolCallId | None = None
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_source_links(self) -> WorkspaceMemoryProvenance:
        if self.source_type == WorkspaceMemorySourceType.SESSION_EVENT:
            if self.session_id is None or self.source_sequence is None:
                raise ValueError(
                    "session_event memory provenance requires session_id "
                    "and source_sequence"
                )
        if self.source_type == WorkspaceMemorySourceType.TASK and self.task_id is None:
            raise ValueError("task memory provenance requires task_id")
        if (
            self.source_type == WorkspaceMemorySourceType.ARTIFACT
            and self.artifact_id is None
        ):
            raise ValueError("artifact memory provenance requires artifact_id")
        if (
            self.source_type == WorkspaceMemorySourceType.TOOL_RESULT
            and self.tool_call_id is None
        ):
            raise ValueError("tool_result memory provenance requires tool_call_id")
        return self


class WorkspaceMemoryEntry(BaseModel):
    """Projected durable memory entry scoped to one local workspace."""

    model_config = ConfigDict(extra="forbid")

    memory_id: WorkspaceMemoryId
    session_id: SessionId
    kind: WorkspaceMemoryKind
    state: WorkspaceMemoryState
    content: str = Field(min_length=1, max_length=8000)
    summary: str | None = Field(default=None, max_length=500)
    provenance: WorkspaceMemoryProvenance
    created_by: str = Field(default="operator", min_length=1, max_length=200)
    created_at: datetime
    updated_at: datetime
    confirmed_by: str | None = Field(default=None, max_length=200)
    confirmed_at: datetime | None = None
    invalidated_by: str | None = Field(default=None, max_length=200)
    invalidated_at: datetime | None = None
    invalidation_reason: str | None = Field(default=None, max_length=2000)
    last_used_at: datetime | None = None
    use_count: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)
    redacted: bool = False
    import_source: str | None = Field(default=None, max_length=1000)
    pruned_by: str | None = Field(default=None, max_length=200)
    pruned_at: datetime | None = None
    prune_reason: str | None = Field(default=None, max_length=2000)
    last_sequence: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_memory_state(self) -> WorkspaceMemoryEntry:
        if self.state == WorkspaceMemoryState.INVALIDATED:
            if self.invalidated_by is None or self.invalidation_reason is None:
                raise ValueError(
                    "invalidated memory requires invalidated_by and invalidation_reason"
                )
        if self.confirmed_at is not None and self.confirmed_by is None:
            raise ValueError("confirmed_at requires confirmed_by")
        return self


class RepositoryIndexProvenance(BaseModel):
    """Inspectable source evidence for one repository index entry."""

    model_config = ConfigDict(extra="forbid")

    source_type: RepositoryIndexSourceType
    path: Path | None = None
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    source_label: str | None = Field(default=None, max_length=500)
    content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    tool_name: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_line_range(self) -> RepositoryIndexProvenance:
        if self.line_end is not None and self.line_start is None:
            raise ValueError("line_end requires line_start")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end must be greater than or equal to line_start")
        if (
            self.source_type != RepositoryIndexSourceType.USER_HINT
            and self.path is None
        ):
            raise ValueError("repository index provenance requires path")
        return self


class RepositoryIndexEntry(BaseModel):
    """One deterministic entry in a local repository intelligence index."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1, max_length=200)
    kind: RepositoryIndexEntityKind
    name: str = Field(min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=2000)
    path: Path | None = None
    symbol: str | None = Field(default=None, max_length=500)
    language: str | None = Field(default=None, max_length=100)
    provenance: list[RepositoryIndexProvenance] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime

    @model_validator(mode="after")
    def validate_entry_shape(self) -> RepositoryIndexEntry:
        if self.kind == RepositoryIndexEntityKind.SYMBOL and self.symbol is None:
            raise ValueError("symbol repository index entries require symbol")
        if self.kind != RepositoryIndexEntityKind.OWNERSHIP_HINT and self.path is None:
            raise ValueError("repository index entries require path")
        return self


class RepositoryIndexSnapshot(BaseModel):
    """Versioned rebuildable repository intelligence snapshot."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1)
    workspace_root: Path
    status: RepositoryIndexFreshness
    built_at: datetime | None = None
    builder_version: str = Field(default="v1", min_length=1, max_length=100)
    source_digest: str | None = Field(default=None, min_length=64, max_length=64)
    source_inputs: list[str] = Field(default_factory=list)
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    entries: list[RepositoryIndexEntry] = Field(default_factory=list)
    failure_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_snapshot(self) -> RepositoryIndexSnapshot:
        if (
            self.status == RepositoryIndexFreshness.FAILED
            and self.failure_reason is None
        ):
            raise ValueError("failed repository index snapshots require failure_reason")
        if self.status == RepositoryIndexFreshness.FRESH and self.built_at is None:
            raise ValueError("fresh repository index snapshots require built_at")
        entry_ids = [entry.entry_id for entry in self.entries]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("repository index entries require unique entry_id values")
        return self


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


class ToolAttemptRecord(BaseModel):
    """Projected long-running tool-attempt state for recovery surfaces."""

    model_config = ConfigDict(extra="forbid")

    tool_attempt_id: ToolAttemptId
    session_id: SessionId
    turn_id: TurnId
    tool_name: str
    status: ToolAttemptStatus
    tool_call_id: ToolCallId | None = None
    task_id: TaskId | None = None
    message: str | None = None
    started_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    heartbeat_expires_at: datetime | None = None
    completed_at: datetime | None = None
    completed_units: int | None = Field(default=None, ge=0)
    total_units: int | None = Field(default=None, ge=0)
    output_artifact_id: ArtifactId | None = None
    safe_to_retry: bool | None = None
    retry_reason: str | None = None
    last_sequence: int = Field(ge=0)


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


class TaskRecord(BaseModel):
    """A query-friendly view of a durable task plan."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    session_id: SessionId
    title: str
    goal: str
    status: TaskPlanStatus
    created_at: datetime
    updated_at: datetime
    source_turn_id: TurnId | None = None
    current_step_id: TaskStepId | None = None
    blocked_reason: TaskBlockedReason | None = None
    blocked_detail: str | None = None
    last_sequence: int = Field(ge=0)
    step_count: int = Field(default=0, ge=0)


class TaskVerificationRecord(BaseModel):
    """A query-friendly view of a task verification run."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    verification_id: TaskVerificationId
    step_id: TaskStepId | None = None
    status: TaskVerificationStatus
    check_name: str
    summary: str | None = None


class BranchCandidateRecord(BaseModel):
    """Projected state for one branch-search candidate."""

    model_config = ConfigDict(extra="forbid")

    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    parent_session_id: SessionId
    candidate_session_id: SessionId | None = None
    strategy_label: str = Field(min_length=1, max_length=200)
    status: BranchCandidateStatus
    verification_status: BranchCandidateVerificationStatus = (
        BranchCandidateVerificationStatus.NOT_RUN
    )
    selection_state: BranchCandidateStatus | None = None
    verification_summary: str | None = Field(default=None, max_length=4000)
    verification_id: TaskVerificationId | None = None
    artifact_id: ArtifactId | None = None
    created_at: datetime
    updated_at: datetime
    last_sequence: int = Field(ge=0)


class BranchSearchRecord(BaseModel):
    """Projected state for a branch-search workflow."""

    model_config = ConfigDict(extra="forbid")

    search_id: BranchSearchId
    session_id: SessionId
    parent_session_id: SessionId
    status: BranchSearchStatus
    objective: str = Field(min_length=1, max_length=4000)
    task_id: TaskId | None = None
    selected_candidate_id: BranchCandidateId | None = None
    abandoned_reason: str | None = Field(default=None, max_length=2000)
    candidate_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime
    last_sequence: int = Field(ge=0)


class VerificationPlanEntry(BaseModel):
    """One explicit local verification check selected for a task."""

    model_config = ConfigDict(extra="forbid")

    verification_id: TaskVerificationId
    check_name: str = Field(min_length=1, max_length=200)
    kind: VerificationCheckKind
    command: list[str] = Field(min_length=1, max_length=64)
    source: VerificationPlanSource
    rationale: str = Field(min_length=1, max_length=2000)
    blocking: bool = True
    timeout_seconds: int = Field(default=300, ge=1, le=7200)
    expected_exit_codes: list[int] = Field(default_factory=lambda: [0], min_length=1)
    changed_paths: list[Path] = Field(default_factory=list, max_length=100)
    eval_case_id: str | None = Field(default=None, min_length=1, max_length=200)
    eval_profile_id: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("expected_exit_codes")
    @classmethod
    def normalize_expected_exit_codes(cls, value: list[int]) -> list[int]:
        normalized = list(dict.fromkeys(value))
        if not normalized:
            raise ValueError("expected_exit_codes must not be empty")
        for exit_code in normalized:
            if exit_code < 0 or exit_code > 255:
                raise ValueError("expected_exit_codes must be between 0 and 255")
        return normalized

    @model_validator(mode="after")
    def validate_eval_links(self) -> VerificationPlanEntry:
        if self.kind == VerificationCheckKind.EVAL and (
            self.eval_case_id is None and self.eval_profile_id is None
        ):
            raise ValueError(
                "eval verification requires eval_case_id or eval_profile_id"
            )
        return self


class VerificationPlan(BaseModel):
    """A bounded collection of verification checks for one task."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    entries: list[VerificationPlanEntry] = Field(min_length=1, max_length=20)
    max_repair_attempts: int = Field(default=0, ge=0, le=10)
    selection_sources: list[VerificationPlanSource] = Field(
        default_factory=list,
        max_length=20,
    )
    residual_risk_policy: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_unique_verification_ids(self) -> VerificationPlan:
        verification_ids = [entry.verification_id for entry in self.entries]
        if len(verification_ids) != len(set(verification_ids)):
            raise ValueError("verification plan entries require unique verification_id")
        return self


class VerificationFailureDigest(BaseModel):
    """Compact failure evidence suitable for event payloads and artifacts."""

    model_config = ConfigDict(extra="forbid")

    category: VerificationFailureCategory
    summary: str = Field(min_length=1, max_length=4000)
    exit_code: int | None = Field(default=None, ge=0)
    timed_out: bool = False
    artifact_id: ArtifactId | None = None
    first_relevant_line: str | None = Field(default=None, max_length=1000)


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
