"""Event envelope and payload models for the Glassbox event log."""

from datetime import UTC
from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import TypeAdapter
from pydantic import model_validator

from glassbox.core.ids import ApprovalId
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import BackgroundJobId
from glassbox.core.ids import BranchCandidateId
from glassbox.core.ids import BranchSearchId
from glassbox.core.ids import BudgetOverrideId
from glassbox.core.ids import ContextCompactionId
from glassbox.core.ids import EventId
from glassbox.core.ids import MessageId
from glassbox.core.ids import PauseWindowId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import RecoveryDecisionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskCheckpointId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskStepId
from glassbox.core.ids import TaskVerificationId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.ids import new_event_id
from glassbox.core.models import AutonomyBudget
from glassbox.core.models import AutonomyBudgetRemaining
from glassbox.core.models import AutonomyBudgetUsage
from glassbox.core.models import MessagePart
from glassbox.core.models import PolicyDecisionOutcome
from glassbox.core.models import PolicyDecisionSourceKind
from glassbox.core.models import PolicyDecisionTrace
from glassbox.core.models import PolicyRiskLevel
from glassbox.core.models import TaskPlanSnapshot
from glassbox.core.models import TaskStepProposal
from glassbox.core.models import VerificationFailureDigest
from glassbox.core.models import VerificationPlanEntry
from glassbox.core.models import WorkspaceMemoryProvenance
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import AutonomyMode
from glassbox.core.types import BackgroundJobFailureKind
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import BackgroundJobRecoveryReason
from glassbox.core.types import BackgroundJobState
from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope
from glassbox.core.types import LongRunPhase
from glassbox.core.types import LongRunPhaseState
from glassbox.core.types import PauseWindowPolicy
from glassbox.core.types import RecoveryDecision
from glassbox.core.types import ResumeOutcomeStatus
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.core.types import TurnStatus
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemoryState

ToolOutputStream = Literal["stdout", "stderr", "structured"]
TurnOutcome = Literal[
    "completed",
    "awaiting_approval",
    "awaiting_user_input",
    "cancelled",
    "failed",
]
ErrorScope = Literal["session", "turn", "tool", "web"]
CancellationStage = Literal[
    "preparation",
    "model_call",
    "tool_execution",
    "awaiting_approval",
    "awaiting_user_input",
    "resumption",
    "reconnecting_stream",
    "unknown",
]


class EventPayload(BaseModel):
    """Base class for all persisted event payloads."""

    model_config = ConfigDict(extra="forbid")


class SessionStarted(EventPayload):
    event_type: Literal["SessionStarted"] = "SessionStarted"
    cwd: str
    dashboard_url: str | None = None
    model_name: str
    approval_mode: str
    autonomy_mode: AutonomyMode | None = None
    autonomy_budget: AutonomyBudget | None = None
    autonomy_budget_preset: str | None = None
    parent_session_id: SessionId | None = None
    forked_from_turn_id: TurnId | None = None
    forked_from_sequence: int | None = Field(default=None, ge=0)
    branch_label: str | None = None


class SessionResumed(EventPayload):
    event_type: Literal["SessionResumed"] = "SessionResumed"
    from_sequence: int


class SessionCompleted(EventPayload):
    event_type: Literal["SessionCompleted"] = "SessionCompleted"
    reason: str


class SessionFailed(EventPayload):
    event_type: Literal["SessionFailed"] = "SessionFailed"
    error_message: str
    retryable: bool = False


class UserMessageReceived(EventPayload):
    event_type: Literal["UserMessageReceived"] = "UserMessageReceived"
    message_id: MessageId
    text: str


class TranscriptMessageImported(EventPayload):
    event_type: Literal["TranscriptMessageImported"] = "TranscriptMessageImported"
    message_id: MessageId
    source_session_id: SessionId
    source_message_id: MessageId
    source_turn_id: TurnId | None = None
    role: Literal["user", "assistant", "system"]
    parts: list[MessagePart]
    source_created_at: datetime


class AssistantMessageStarted(EventPayload):
    event_type: Literal["AssistantMessageStarted"] = "AssistantMessageStarted"
    message_id: MessageId


class AssistantMessageDelta(EventPayload):
    event_type: Literal["AssistantMessageDelta"] = "AssistantMessageDelta"
    message_id: MessageId
    delta: str


class AssistantMessageCompleted(EventPayload):
    event_type: Literal["AssistantMessageCompleted"] = "AssistantMessageCompleted"
    message_id: MessageId
    parts: list[MessagePart]


class TurnStarted(EventPayload):
    event_type: Literal["TurnStarted"] = "TurnStarted"
    turn_id: TurnId
    trigger_message_id: MessageId


class TurnStatusChanged(EventPayload):
    event_type: Literal["TurnStatusChanged"] = "TurnStatusChanged"
    turn_id: TurnId
    status: TurnStatus


class TurnCompleted(EventPayload):
    event_type: Literal["TurnCompleted"] = "TurnCompleted"
    turn_id: TurnId
    outcome: TurnOutcome


class TurnFailed(EventPayload):
    event_type: Literal["TurnFailed"] = "TurnFailed"
    turn_id: TurnId
    error_message: str


class CancellationRequested(EventPayload):
    event_type: Literal["CancellationRequested"] = "CancellationRequested"
    turn_id: TurnId
    requested_by: str = "operator"
    reason: str | None = None


class CancellationAcknowledged(EventPayload):
    event_type: Literal["CancellationAcknowledged"] = "CancellationAcknowledged"
    turn_id: TurnId
    requested_by: str = "runtime"
    repeated: bool = False


class TurnCancelled(EventPayload):
    event_type: Literal["TurnCancelled"] = "TurnCancelled"
    turn_id: TurnId
    reason: str
    stage: CancellationStage = "unknown"


class ToolExecutionCancelled(EventPayload):
    event_type: Literal["ToolExecutionCancelled"] = "ToolExecutionCancelled"
    turn_id: TurnId
    tool_call_id: ToolCallId
    summary: str
    exit_code: int | None = None


class CancellationFailed(EventPayload):
    event_type: Literal["CancellationFailed"] = "CancellationFailed"
    turn_id: TurnId | None = None
    reason: str
    retryable: bool = False


class ModelCallStarted(EventPayload):
    event_type: Literal["ModelCallStarted"] = "ModelCallStarted"
    turn_id: TurnId
    provider: str
    model_name: str


class ModelCallCompleted(EventPayload):
    event_type: Literal["ModelCallCompleted"] = "ModelCallCompleted"
    turn_id: TurnId
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int


class ModelToolCallRequested(EventPayload):
    event_type: Literal["ModelToolCallRequested"] = "ModelToolCallRequested"
    turn_id: TurnId
    tool_call_id: ToolCallId
    tool_name: str
    arguments_json: str
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None
    policy_reason: str | None = None
    policy_trace: PolicyDecisionTrace | None = None


class ToolExecutionStarted(EventPayload):
    event_type: Literal["ToolExecutionStarted"] = "ToolExecutionStarted"
    turn_id: TurnId
    tool_call_id: ToolCallId
    tool_name: str
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None
    policy_reason: str | None = None
    policy_trace: PolicyDecisionTrace | None = None


class ToolOutputChunk(EventPayload):
    event_type: Literal["ToolOutputChunk"] = "ToolOutputChunk"
    turn_id: TurnId
    tool_call_id: ToolCallId
    stream: ToolOutputStream
    chunk: str


class ToolArtifactRecorded(EventPayload):
    event_type: Literal["ToolArtifactRecorded"] = "ToolArtifactRecorded"
    turn_id: TurnId
    tool_call_id: ToolCallId
    artifact_id: ArtifactId
    artifact_kind: str
    path: str | None = None
    content_sha256: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)


class ReplayArtifactRecorded(EventPayload):
    event_type: Literal["ReplayArtifactRecorded"] = "ReplayArtifactRecorded"
    turn_id: TurnId
    artifact_id: ArtifactId
    artifact_kind: str
    path: str | None = None
    tool_call_id: ToolCallId | None = None
    content_sha256: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)


class ToolExecutionCompleted(EventPayload):
    event_type: Literal["ToolExecutionCompleted"] = "ToolExecutionCompleted"
    turn_id: TurnId
    tool_call_id: ToolCallId
    success: bool
    exit_code: int | None = None
    summary: str


class ApprovalRequested(EventPayload):
    event_type: Literal["ApprovalRequested"] = "ApprovalRequested"
    approval_id: ApprovalId
    turn_id: TurnId
    reason: str
    subject: str
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None
    policy_trace: PolicyDecisionTrace | None = None
    # Optional fields — set when the approval is linked to a specific tool call so
    # the turn can be correctly resumed after a decision is made.
    tool_call_id: ToolCallId | None = None
    provider_tool_call_id: str | None = None


class ApprovalResolved(EventPayload):
    event_type: Literal["ApprovalResolved"] = "ApprovalResolved"
    approval_id: ApprovalId
    decision: ApprovalDecision
    decided_by: str


class UserQuestionAsked(EventPayload):
    event_type: Literal["UserQuestionAsked"] = "UserQuestionAsked"
    question_id: QuestionId
    turn_id: TurnId
    tool_call_id: ToolCallId
    provider_tool_call_id: str
    question: str


class UserAnswerProvided(EventPayload):
    event_type: Literal["UserAnswerProvided"] = "UserAnswerProvided"
    question_id: QuestionId
    answer: str


class RuntimeNoteRecorded(EventPayload):
    event_type: Literal["RuntimeNoteRecorded"] = "RuntimeNoteRecorded"
    category: str
    message: str


class RuntimeNoteImported(EventPayload):
    event_type: Literal["RuntimeNoteImported"] = "RuntimeNoteImported"
    source_session_id: SessionId
    source_sequence: int = Field(ge=0)
    category: str
    message: str
    source_created_at: datetime


class BudgetDecisionRecorded(EventPayload):
    event_type: Literal["BudgetDecisionRecorded"] = "BudgetDecisionRecorded"
    scope: Literal["session", "task"]
    mode: AutonomyMode
    budget: AutonomyBudget
    usage: AutonomyBudgetUsage
    remaining: AutonomyBudgetRemaining
    decision: Literal["allowed", "exhausted", "override_required"]
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    reason: AutonomyEscalationReason | None = None
    limit_name: str | None = Field(default=None, max_length=120)
    detail: str | None = Field(default=None, max_length=2000)


class BudgetExhausted(EventPayload):
    event_type: Literal["BudgetExhausted"] = "BudgetExhausted"
    scope: Literal["session", "task"]
    limit_name: str = Field(min_length=1, max_length=120)
    used: int = Field(ge=0)
    limit: int = Field(ge=0)
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    reason: AutonomyEscalationReason = AutonomyEscalationReason.BUDGET_EXHAUSTED
    detail: str | None = Field(default=None, max_length=2000)


class BudgetOverrideRequested(EventPayload):
    event_type: Literal["BudgetOverrideRequested"] = "BudgetOverrideRequested"
    override_id: BudgetOverrideId
    scope: Literal["session", "task"]
    reason: AutonomyEscalationReason
    requested_by: str = Field(default="operator", min_length=1, max_length=200)
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    detail: str | None = Field(default=None, max_length=2000)


class BudgetOverrideResolved(EventPayload):
    event_type: Literal["BudgetOverrideResolved"] = "BudgetOverrideResolved"
    override_id: BudgetOverrideId
    decision: ApprovalDecision
    decided_by: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=2000)


class ContinuationWindowRequested(EventPayload):
    event_type: Literal["ContinuationWindowRequested"] = "ContinuationWindowRequested"
    approval_id: ApprovalId
    scope: Literal["session", "task"]
    requested_minutes: int = Field(ge=1, le=1440)
    requested_by: str = Field(default="operator", min_length=1, max_length=200)
    task_id: TaskId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    reason: str | None = Field(default=None, max_length=2000)


class ContinuationWindowResolved(EventPayload):
    event_type: Literal["ContinuationWindowResolved"] = "ContinuationWindowResolved"
    approval_id: ApprovalId
    decision: ApprovalDecision
    decided_by: str = Field(min_length=1, max_length=200)
    approved_minutes: int | None = Field(default=None, ge=1, le=1440)
    approved_until: datetime | None = None
    task_id: TaskId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    reason: str | None = Field(default=None, max_length=2000)


class ContinuationWindowExpired(EventPayload):
    event_type: Literal["ContinuationWindowExpired"] = "ContinuationWindowExpired"
    approval_id: ApprovalId
    scope: Literal["session", "task"]
    expired_at: datetime
    stop_reason: str = Field(min_length=1, max_length=2000)
    task_id: TaskId | None = None
    job_id: BackgroundJobId | None = None
    checkpoint_id: TaskCheckpointId | None = None


class PauseWindowScheduled(EventPayload):
    event_type: Literal["PauseWindowScheduled"] = "PauseWindowScheduled"
    pause_window_id: PauseWindowId
    scope: Literal["session", "task"]
    policy: PauseWindowPolicy
    scheduled_by: str = Field(default="operator", min_length=1, max_length=200)
    task_id: TaskId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    pause_before: datetime | None = None
    reason: str = Field(min_length=1, max_length=2000)


class PauseWindowTriggered(EventPayload):
    event_type: Literal["PauseWindowTriggered"] = "PauseWindowTriggered"
    pause_window_id: PauseWindowId
    scope: Literal["session", "task"]
    policy: PauseWindowPolicy
    triggered_at: datetime
    stop_reason: str = Field(min_length=1, max_length=2000)
    task_id: TaskId | None = None
    job_id: BackgroundJobId | None = None
    checkpoint_id: TaskCheckpointId | None = None


class PauseWindowCancelled(EventPayload):
    event_type: Literal["PauseWindowCancelled"] = "PauseWindowCancelled"
    pause_window_id: PauseWindowId
    cancelled_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    task_id: TaskId | None = None


class TaskCreated(EventPayload):
    event_type: Literal["TaskCreated"] = "TaskCreated"
    task_id: TaskId
    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=4000)
    source_turn_id: TurnId | None = None


class TaskPlanProposed(EventPayload):
    event_type: Literal["TaskPlanProposed"] = "TaskPlanProposed"
    task_id: TaskId
    plan: TaskPlanSnapshot

    @model_validator(mode="after")
    def ensure_plan_matches_task(self) -> TaskPlanProposed:
        if self.plan.task_id != self.task_id:
            raise ValueError("plan.task_id must match task_id")
        return self


class TaskPlanRevised(EventPayload):
    event_type: Literal["TaskPlanRevised"] = "TaskPlanRevised"
    task_id: TaskId
    revision_reason: str = Field(min_length=1, max_length=1000)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    goal: str | None = Field(default=None, min_length=1, max_length=4000)
    steps: list[TaskStepProposal] | None = Field(default=None, max_length=50)


class TaskStepStarted(EventPayload):
    event_type: Literal["TaskStepStarted"] = "TaskStepStarted"
    task_id: TaskId
    step_id: TaskStepId
    turn_id: TurnId | None = None


class TaskStepCompleted(EventPayload):
    event_type: Literal["TaskStepCompleted"] = "TaskStepCompleted"
    task_id: TaskId
    step_id: TaskStepId
    summary: str | None = Field(default=None, max_length=4000)


class TaskStepFailed(EventPayload):
    event_type: Literal["TaskStepFailed"] = "TaskStepFailed"
    task_id: TaskId
    step_id: TaskStepId
    reason: str = Field(min_length=1, max_length=4000)
    blocked_reason: TaskBlockedReason | None = None


class TaskStepSkipped(EventPayload):
    event_type: Literal["TaskStepSkipped"] = "TaskStepSkipped"
    task_id: TaskId
    step_id: TaskStepId
    reason: str = Field(min_length=1, max_length=2000)


class TaskVerificationPlanned(EventPayload):
    event_type: Literal["TaskVerificationPlanned"] = "TaskVerificationPlanned"
    task_id: TaskId
    verification: VerificationPlanEntry
    step_id: TaskStepId | None = None
    attempt: int = Field(default=1, ge=1)


class TaskVerificationStarted(EventPayload):
    event_type: Literal["TaskVerificationStarted"] = "TaskVerificationStarted"
    task_id: TaskId
    verification_id: TaskVerificationId
    step_id: TaskStepId | None = None
    check_name: str = Field(min_length=1, max_length=200)
    attempt: int = Field(default=1, ge=1)


class TaskVerificationStreamed(EventPayload):
    event_type: Literal["TaskVerificationStreamed"] = "TaskVerificationStreamed"
    task_id: TaskId
    verification_id: TaskVerificationId
    stream: ToolOutputStream
    chunk_summary: str = Field(min_length=1, max_length=2000)
    artifact_id: ArtifactId | None = None


class TaskVerificationFailed(EventPayload):
    event_type: Literal["TaskVerificationFailed"] = "TaskVerificationFailed"
    task_id: TaskId
    verification_id: TaskVerificationId
    failure: VerificationFailureDigest
    step_id: TaskStepId | None = None


class TaskVerificationSkipped(EventPayload):
    event_type: Literal["TaskVerificationSkipped"] = "TaskVerificationSkipped"
    task_id: TaskId
    verification_id: TaskVerificationId
    reason: str = Field(min_length=1, max_length=2000)
    step_id: TaskStepId | None = None


class TaskVerificationRetried(EventPayload):
    event_type: Literal["TaskVerificationRetried"] = "TaskVerificationRetried"
    task_id: TaskId
    verification_id: TaskVerificationId
    next_verification_id: TaskVerificationId
    attempt: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)
    step_id: TaskStepId | None = None


class TaskVerificationCompleted(EventPayload):
    event_type: Literal["TaskVerificationCompleted"] = "TaskVerificationCompleted"
    task_id: TaskId
    verification_id: TaskVerificationId
    status: TaskVerificationStatus
    summary: str | None = Field(default=None, max_length=4000)
    artifact_id: ArtifactId | None = None


class TaskVerificationResidualRiskAccepted(EventPayload):
    event_type: Literal["TaskVerificationResidualRiskAccepted"] = (
        "TaskVerificationResidualRiskAccepted"
    )
    task_id: TaskId
    verification_id: TaskVerificationId
    accepted_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    residual_risks: list[str] = Field(default_factory=list, max_length=20)


class TaskPaused(EventPayload):
    event_type: Literal["TaskPaused"] = "TaskPaused"
    task_id: TaskId
    reason: TaskBlockedReason
    detail: str | None = Field(default=None, max_length=2000)


class TaskResumed(EventPayload):
    event_type: Literal["TaskResumed"] = "TaskResumed"
    task_id: TaskId
    resumed_by: str = Field(default="operator", min_length=1, max_length=200)


class TaskCancelled(EventPayload):
    event_type: Literal["TaskCancelled"] = "TaskCancelled"
    task_id: TaskId
    requested_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=2000)


class TaskAbandoned(EventPayload):
    event_type: Literal["TaskAbandoned"] = "TaskAbandoned"
    task_id: TaskId
    reason: str = Field(min_length=1, max_length=2000)


class TaskStatusChanged(EventPayload):
    event_type: Literal["TaskStatusChanged"] = "TaskStatusChanged"
    task_id: TaskId
    status: TaskPlanStatus
    reason: str | None = Field(default=None, max_length=2000)


class BranchSearchStarted(EventPayload):
    event_type: Literal["BranchSearchStarted"] = "BranchSearchStarted"
    search_id: BranchSearchId
    parent_session_id: SessionId
    objective: str = Field(min_length=1, max_length=4000)
    task_id: TaskId | None = None
    max_candidates: int = Field(default=2, ge=1, le=20)


class BranchCandidatePlanned(EventPayload):
    event_type: Literal["BranchCandidatePlanned"] = "BranchCandidatePlanned"
    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    strategy_label: str = Field(min_length=1, max_length=200)
    verification_plan: list[VerificationPlanEntry] = Field(
        default_factory=list,
        max_length=20,
    )


class BranchCandidateForked(EventPayload):
    event_type: Literal["BranchCandidateForked"] = "BranchCandidateForked"
    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    candidate_session_id: SessionId
    forked_from_turn_id: TurnId | None = None
    forked_from_sequence: int | None = Field(default=None, ge=0)


class BranchCandidateExecuted(EventPayload):
    event_type: Literal["BranchCandidateExecuted"] = "BranchCandidateExecuted"
    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    summary: str = Field(min_length=1, max_length=4000)


class BranchCandidateVerified(EventPayload):
    event_type: Literal["BranchCandidateVerified"] = "BranchCandidateVerified"
    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    verification_status: BranchCandidateVerificationStatus
    summary: str = Field(min_length=1, max_length=4000)
    verification_id: TaskVerificationId | None = None
    artifact_id: ArtifactId | None = None


class BranchCandidatesCompared(EventPayload):
    event_type: Literal["BranchCandidatesCompared"] = "BranchCandidatesCompared"
    search_id: BranchSearchId
    summary: str = Field(min_length=1, max_length=4000)
    artifact_id: ArtifactId | None = None


class BranchCandidateSelected(EventPayload):
    event_type: Literal["BranchCandidateSelected"] = "BranchCandidateSelected"
    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    selected_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class BranchCandidateRejected(EventPayload):
    event_type: Literal["BranchCandidateRejected"] = "BranchCandidateRejected"
    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    rejected_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class BranchCandidateNeedsReview(EventPayload):
    event_type: Literal["BranchCandidateNeedsReview"] = "BranchCandidateNeedsReview"
    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    marked_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class BranchSearchAbandoned(EventPayload):
    event_type: Literal["BranchSearchAbandoned"] = "BranchSearchAbandoned"
    search_id: BranchSearchId
    reason: str = Field(min_length=1, max_length=2000)


class BackgroundJobCreated(EventPayload):
    event_type: Literal["BackgroundJobCreated"] = "BackgroundJobCreated"
    job_id: BackgroundJobId
    kind: BackgroundJobKind
    job_type: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    requested_by: str = Field(default="operator", min_length=1, max_length=200)
    payload: dict[str, object] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0)
    task_id: TaskId | None = None
    parent_job_id: BackgroundJobId | None = None


class BackgroundJobClaimed(EventPayload):
    event_type: Literal["BackgroundJobClaimed"] = "BackgroundJobClaimed"
    job_id: BackgroundJobId
    worker_id: str = Field(min_length=1, max_length=200)
    claim_token: str = Field(min_length=1, max_length=200)
    attempt: int = Field(ge=1)
    lease_expires_at: datetime


class BackgroundJobStarted(EventPayload):
    event_type: Literal["BackgroundJobStarted"] = "BackgroundJobStarted"
    job_id: BackgroundJobId
    worker_id: str = Field(min_length=1, max_length=200)
    claim_token: str = Field(min_length=1, max_length=200)
    attempt: int = Field(ge=1)


class BackgroundJobHeartbeat(EventPayload):
    event_type: Literal["BackgroundJobHeartbeat"] = "BackgroundJobHeartbeat"
    job_id: BackgroundJobId
    worker_id: str = Field(min_length=1, max_length=200)
    claim_token: str = Field(min_length=1, max_length=200)
    lease_expires_at: datetime
    state: BackgroundJobState = BackgroundJobState.RUNNING
    message: str | None = Field(default=None, max_length=1000)


class BackgroundJobProgressRecorded(EventPayload):
    event_type: Literal["BackgroundJobProgressRecorded"] = (
        "BackgroundJobProgressRecorded"
    )
    job_id: BackgroundJobId
    message: str = Field(min_length=1, max_length=1000)
    completed_units: int | None = Field(default=None, ge=0)
    total_units: int | None = Field(default=None, ge=0)


class BackgroundJobPaused(EventPayload):
    event_type: Literal["BackgroundJobPaused"] = "BackgroundJobPaused"
    job_id: BackgroundJobId
    reason: AutonomyEscalationReason
    detail: str | None = Field(default=None, max_length=2000)


class BackgroundJobCompleted(EventPayload):
    event_type: Literal["BackgroundJobCompleted"] = "BackgroundJobCompleted"
    job_id: BackgroundJobId
    summary: str = Field(min_length=1, max_length=4000)
    artifact_id: ArtifactId | None = None


class BackgroundJobFailed(EventPayload):
    event_type: Literal["BackgroundJobFailed"] = "BackgroundJobFailed"
    job_id: BackgroundJobId
    failure_kind: BackgroundJobFailureKind
    message: str = Field(min_length=1, max_length=4000)
    retryable: bool = False
    attempt: int = Field(ge=1)
    next_retry_at: datetime | None = None
    artifact_id: ArtifactId | None = None
    artifact_path: str | None = Field(default=None, max_length=4000)


class BackgroundJobCancellationRequested(EventPayload):
    event_type: Literal["BackgroundJobCancellationRequested"] = (
        "BackgroundJobCancellationRequested"
    )
    job_id: BackgroundJobId
    requested_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=2000)


class BackgroundJobCancelled(EventPayload):
    event_type: Literal["BackgroundJobCancelled"] = "BackgroundJobCancelled"
    job_id: BackgroundJobId
    cancelled_by: str = Field(default="runtime", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class BackgroundJobRecoveryRecorded(EventPayload):
    event_type: Literal["BackgroundJobRecoveryRecorded"] = (
        "BackgroundJobRecoveryRecorded"
    )
    job_id: BackgroundJobId
    reason: BackgroundJobRecoveryReason
    previous_state: BackgroundJobState
    recovered_by: str = Field(default="runtime", min_length=1, max_length=200)
    detail: str | None = Field(default=None, max_length=2000)


class BackgroundJobRetryRequested(EventPayload):
    event_type: Literal["BackgroundJobRetryRequested"] = "BackgroundJobRetryRequested"
    job_id: BackgroundJobId
    requested_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=2000)


class BackgroundJobRetryExhausted(EventPayload):
    event_type: Literal["BackgroundJobRetryExhausted"] = "BackgroundJobRetryExhausted"
    job_id: BackgroundJobId
    retry_budget: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=2000)


class BackgroundJobAbandoned(EventPayload):
    event_type: Literal["BackgroundJobAbandoned"] = "BackgroundJobAbandoned"
    job_id: BackgroundJobId
    abandoned_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class LongRunPhaseChanged(EventPayload):
    event_type: Literal["LongRunPhaseChanged"] = "LongRunPhaseChanged"
    phase: LongRunPhase
    state: LongRunPhaseState
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    tool_attempt_id: ToolAttemptId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    compaction_id: ContextCompactionId | None = None
    reason: str | None = Field(default=None, max_length=2000)
    detail: str | None = Field(default=None, max_length=4000)


class TaskCheckpointCreated(EventPayload):
    event_type: Literal["TaskCheckpointCreated"] = "TaskCheckpointCreated"
    checkpoint_id: TaskCheckpointId
    objective: str = Field(min_length=1, max_length=4000)
    current_phase: LongRunPhase | None = None
    completed_step: str | None = Field(default=None, max_length=2000)
    next_action: str = Field(min_length=1, max_length=2000)
    recovery_guidance: str = Field(min_length=1, max_length=4000)
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    tool_attempt_id: ToolAttemptId | None = None
    compaction_id: ContextCompactionId | None = None
    blockers: list[str] = Field(default_factory=list, max_length=20)
    touched_files: list[str] = Field(default_factory=list, max_length=100)
    verification_status: str | None = Field(default=None, max_length=200)
    budget_status: str | None = Field(default=None, max_length=200)
    source_start_sequence: int = Field(default=0, ge=0)
    source_end_sequence: int = Field(default=0, ge=0)
    artifact_id: ArtifactId | None = None

    @model_validator(mode="after")
    def ensure_source_range_is_ordered(self) -> TaskCheckpointCreated:
        if self.source_end_sequence < self.source_start_sequence:
            raise ValueError(
                "source_end_sequence must be greater than or equal to "
                "source_start_sequence"
            )
        return self


class ContextCompactionCreated(EventPayload):
    event_type: Literal["ContextCompactionCreated"] = "ContextCompactionCreated"
    compaction_id: ContextCompactionId
    scope: ContextCompactionScope
    source_start_sequence: int = Field(ge=0)
    source_end_sequence: int = Field(ge=0)
    summary: str = Field(min_length=1, max_length=4000)
    artifact_id: ArtifactId
    artifact_schema_version: int = Field(default=1, ge=1)
    freshness: ContextCompactionFreshness = ContextCompactionFreshness.FRESH
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    source_artifact_ids: list[ArtifactId] = Field(default_factory=list, max_length=50)
    decision_count: int = Field(default=0, ge=0)
    unresolved_question_count: int = Field(default=0, ge=0)
    accepted_risk_count: int = Field(default=0, ge=0)
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def ensure_source_range_is_ordered(self) -> ContextCompactionCreated:
        if self.source_end_sequence < self.source_start_sequence:
            raise ValueError(
                "source_end_sequence must be greater than or equal to "
                "source_start_sequence"
            )
        return self


class ContextCompactionFreshnessChanged(EventPayload):
    event_type: Literal["ContextCompactionFreshnessChanged"] = (
        "ContextCompactionFreshnessChanged"
    )
    compaction_id: ContextCompactionId
    freshness: ContextCompactionFreshness
    reason: str = Field(min_length=1, max_length=2000)
    changed_by: str = Field(default="runtime", min_length=1, max_length=200)
    superseded_by_compaction_id: ContextCompactionId | None = None


class ToolAttemptHeartbeat(EventPayload):
    event_type: Literal["ToolAttemptHeartbeat"] = "ToolAttemptHeartbeat"
    tool_attempt_id: ToolAttemptId
    status: ToolAttemptStatus
    turn_id: TurnId
    tool_name: str = Field(min_length=1, max_length=200)
    tool_call_id: ToolCallId | None = None
    task_id: TaskId | None = None
    message: str | None = Field(default=None, max_length=1000)
    completed_units: int | None = Field(default=None, ge=0)
    total_units: int | None = Field(default=None, ge=0)
    heartbeat_expires_at: datetime | None = None
    output_artifact_id: ArtifactId | None = None
    safe_to_retry: bool | None = None
    retry_classification: ToolAttemptRetryClassification | None = None
    retry_requires_approval: bool | None = None
    retry_reason: str | None = Field(default=None, max_length=2000)
    retry_policy_reason: str | None = Field(default=None, max_length=2000)


class RecoveryDecisionRecorded(EventPayload):
    event_type: Literal["RecoveryDecisionRecorded"] = "RecoveryDecisionRecorded"
    recovery_decision_id: RecoveryDecisionId
    decision: RecoveryDecision
    reason: str = Field(min_length=1, max_length=2000)
    safe_to_resume: bool
    next_action: str = Field(min_length=1, max_length=2000)
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    tool_attempt_id: ToolAttemptId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    compaction_id: ContextCompactionId | None = None
    decided_by: str = Field(default="runtime", min_length=1, max_length=200)


class ResumeOutcomeRecorded(EventPayload):
    event_type: Literal["ResumeOutcomeRecorded"] = "ResumeOutcomeRecorded"
    outcome: ResumeOutcomeStatus
    summary: str = Field(min_length=1, max_length=4000)
    task_id: TaskId | None = None
    turn_id: TurnId | None = None
    tool_attempt_id: ToolAttemptId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    compaction_id: ContextCompactionId | None = None
    recovery_decision_id: RecoveryDecisionId | None = None
    resumed_by: str = Field(default="runtime", min_length=1, max_length=200)


class WorkspaceMemoryCreated(EventPayload):
    event_type: Literal["WorkspaceMemoryCreated"] = "WorkspaceMemoryCreated"
    memory_id: WorkspaceMemoryId
    kind: WorkspaceMemoryKind
    content: str = Field(min_length=1, max_length=8000)
    summary: str | None = Field(default=None, max_length=500)
    provenance: WorkspaceMemoryProvenance
    created_by: str = Field(default="operator", min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list)
    redacted: bool = False


class WorkspaceMemoryConfirmed(EventPayload):
    event_type: Literal["WorkspaceMemoryConfirmed"] = "WorkspaceMemoryConfirmed"
    memory_id: WorkspaceMemoryId
    confirmed_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=2000)


class WorkspaceMemoryUpdated(EventPayload):
    event_type: Literal["WorkspaceMemoryUpdated"] = "WorkspaceMemoryUpdated"
    memory_id: WorkspaceMemoryId
    updated_by: str = Field(default="operator", min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=8000)
    summary: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = None
    reason: str | None = Field(default=None, max_length=2000)


class WorkspaceMemoryInvalidated(EventPayload):
    event_type: Literal["WorkspaceMemoryInvalidated"] = "WorkspaceMemoryInvalidated"
    memory_id: WorkspaceMemoryId
    invalidated_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class WorkspaceMemoryImported(EventPayload):
    event_type: Literal["WorkspaceMemoryImported"] = "WorkspaceMemoryImported"
    memory_id: WorkspaceMemoryId
    kind: WorkspaceMemoryKind
    content: str = Field(min_length=1, max_length=8000)
    provenance: WorkspaceMemoryProvenance
    import_source: str = Field(min_length=1, max_length=1000)
    imported_by: str = Field(default="operator", min_length=1, max_length=200)
    redacted: bool = True


class WorkspaceMemoryUsedInContext(EventPayload):
    event_type: Literal["WorkspaceMemoryUsedInContext"] = "WorkspaceMemoryUsedInContext"
    memory_id: WorkspaceMemoryId
    turn_id: TurnId
    prompt_section: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    state_at_use: WorkspaceMemoryState = WorkspaceMemoryState.ACTIVE


class WorkspaceMemoryPruned(EventPayload):
    event_type: Literal["WorkspaceMemoryPruned"] = "WorkspaceMemoryPruned"
    memory_id: WorkspaceMemoryId
    pruned_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


class WorkspaceMemoryCandidateRejected(EventPayload):
    event_type: Literal["WorkspaceMemoryCandidateRejected"] = (
        "WorkspaceMemoryCandidateRejected"
    )
    candidate_id: str = Field(min_length=1, max_length=128)
    kind: WorkspaceMemoryKind
    content_summary: str = Field(min_length=1, max_length=500)
    provenance: WorkspaceMemoryProvenance
    rejected_by: str = Field(default="operator", min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    redacted: bool = False


class ErrorRecorded(EventPayload):
    event_type: Literal["ErrorRecorded"] = "ErrorRecorded"
    scope: ErrorScope
    message: str


EventPayloadType = Annotated[
    SessionStarted
    | SessionResumed
    | SessionCompleted
    | SessionFailed
    | UserMessageReceived
    | TranscriptMessageImported
    | AssistantMessageStarted
    | AssistantMessageDelta
    | AssistantMessageCompleted
    | TurnStarted
    | TurnStatusChanged
    | TurnCompleted
    | TurnFailed
    | CancellationRequested
    | CancellationAcknowledged
    | TurnCancelled
    | ToolExecutionCancelled
    | CancellationFailed
    | ModelCallStarted
    | ModelCallCompleted
    | ModelToolCallRequested
    | ToolExecutionStarted
    | ToolOutputChunk
    | ToolArtifactRecorded
    | ReplayArtifactRecorded
    | ToolExecutionCompleted
    | ApprovalRequested
    | ApprovalResolved
    | UserQuestionAsked
    | UserAnswerProvided
    | RuntimeNoteRecorded
    | RuntimeNoteImported
    | BudgetDecisionRecorded
    | BudgetExhausted
    | BudgetOverrideRequested
    | BudgetOverrideResolved
    | ContinuationWindowRequested
    | ContinuationWindowResolved
    | ContinuationWindowExpired
    | PauseWindowScheduled
    | PauseWindowTriggered
    | PauseWindowCancelled
    | TaskCreated
    | TaskPlanProposed
    | TaskPlanRevised
    | TaskStepStarted
    | TaskStepCompleted
    | TaskStepFailed
    | TaskStepSkipped
    | TaskVerificationPlanned
    | TaskVerificationStarted
    | TaskVerificationStreamed
    | TaskVerificationFailed
    | TaskVerificationSkipped
    | TaskVerificationRetried
    | TaskVerificationCompleted
    | TaskVerificationResidualRiskAccepted
    | TaskPaused
    | TaskResumed
    | TaskCancelled
    | TaskAbandoned
    | TaskStatusChanged
    | BranchSearchStarted
    | BranchCandidatePlanned
    | BranchCandidateForked
    | BranchCandidateExecuted
    | BranchCandidateVerified
    | BranchCandidatesCompared
    | BranchCandidateSelected
    | BranchCandidateRejected
    | BranchCandidateNeedsReview
    | BranchSearchAbandoned
    | BackgroundJobCreated
    | BackgroundJobClaimed
    | BackgroundJobStarted
    | BackgroundJobHeartbeat
    | BackgroundJobProgressRecorded
    | BackgroundJobPaused
    | BackgroundJobCompleted
    | BackgroundJobFailed
    | BackgroundJobCancellationRequested
    | BackgroundJobCancelled
    | BackgroundJobRecoveryRecorded
    | BackgroundJobRetryRequested
    | BackgroundJobRetryExhausted
    | BackgroundJobAbandoned
    | LongRunPhaseChanged
    | TaskCheckpointCreated
    | ContextCompactionCreated
    | ContextCompactionFreshnessChanged
    | ToolAttemptHeartbeat
    | RecoveryDecisionRecorded
    | ResumeOutcomeRecorded
    | WorkspaceMemoryCreated
    | WorkspaceMemoryConfirmed
    | WorkspaceMemoryUpdated
    | WorkspaceMemoryInvalidated
    | WorkspaceMemoryImported
    | WorkspaceMemoryUsedInContext
    | WorkspaceMemoryPruned
    | WorkspaceMemoryCandidateRejected
    | ErrorRecorded,
    Field(discriminator="event_type"),
]

event_payload_adapter = TypeAdapter(EventPayloadType)


class EventEnvelope(BaseModel):
    """Envelope for a persisted session event."""

    model_config = ConfigDict(extra="forbid")

    event_id: EventId = Field(default_factory=new_event_id)
    session_id: SessionId
    sequence: int = Field(ge=0)
    event_type: str = ""
    event_version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: EventPayloadType

    @model_validator(mode="before")
    @classmethod
    def ensure_event_type_matches_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = data.get("payload")
        payload_event_type: str | None = None

        if isinstance(payload, BaseModel):
            payload_event_type = getattr(payload, "event_type", None)
        elif isinstance(payload, dict):
            payload_event_type = payload.get("event_type")

        if payload_event_type is None:
            return data

        event_type = data.get("event_type")
        if event_type is None:
            data["event_type"] = payload_event_type
            return data

        if event_type != payload_event_type:
            raise ValueError(
                "event_type must match payload.event_type in EventEnvelope"
            )

        return data

    @property
    def turn_id(self) -> TurnId | None:
        return getattr(self.payload, "turn_id", None)

    @property
    def message_id(self) -> MessageId | None:
        return getattr(self.payload, "message_id", None)

    @property
    def tool_call_id(self) -> ToolCallId | None:
        return getattr(self.payload, "tool_call_id", None)

    @property
    def approval_id(self) -> ApprovalId | None:
        return getattr(self.payload, "approval_id", None)

    @property
    def task_id(self) -> TaskId | None:
        return getattr(self.payload, "task_id", None)

    @property
    def job_id(self) -> BackgroundJobId | None:
        return getattr(self.payload, "job_id", None)

    @property
    def memory_id(self) -> WorkspaceMemoryId | None:
        return getattr(self.payload, "memory_id", None)

    @property
    def search_id(self) -> BranchSearchId | None:
        return getattr(self.payload, "search_id", None)

    @property
    def candidate_id(self) -> BranchCandidateId | None:
        return getattr(self.payload, "candidate_id", None)

    @property
    def checkpoint_id(self) -> TaskCheckpointId | None:
        return getattr(self.payload, "checkpoint_id", None)

    @property
    def compaction_id(self) -> ContextCompactionId | None:
        return getattr(self.payload, "compaction_id", None)

    @property
    def tool_attempt_id(self) -> ToolAttemptId | None:
        return getattr(self.payload, "tool_attempt_id", None)

    @property
    def recovery_decision_id(self) -> RecoveryDecisionId | None:
        return getattr(self.payload, "recovery_decision_id", None)

    @property
    def pause_window_id(self) -> PauseWindowId | None:
        return getattr(self.payload, "pause_window_id", None)
