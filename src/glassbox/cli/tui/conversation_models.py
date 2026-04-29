"""Terminal conversation state models for the TUI."""

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from enum import StrEnum
from typing import Self

from glassbox.core.ids import ApprovalId
from glassbox.core.ids import MessageId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.models import PolicyDecisionOutcome
from glassbox.core.models import PolicyDecisionSourceKind
from glassbox.core.models import PolicyRiskLevel
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus
from glassbox.core.types import TurnStatus

TOOL_OUTPUT_PREVIEW_CHARS = 160


class TerminalStreamStatus(StrEnum):
    LIVE = "live"
    RECONNECTING = "reconnecting"
    UNAVAILABLE = "unavailable"
    HISTORICAL_ONLY = "historical_only"


class TerminalMode(StrEnum):
    STARTING = "starting"
    READY = "ready"
    THINKING = "thinking"
    RUNNING_TOOL = "running_tool"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_ANSWER = "awaiting_answer"
    FAILED = "failed"
    HISTORICAL_ONLY = "historical_only"


class ConversationMessageKind(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    RUNTIME = "runtime"


class AssistantMessageStatus(StrEnum):
    STREAMING = "streaming"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


class ToolActivityStatus(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TerminalActionKind(StrEnum):
    PROMPT = "prompt"
    PENDING_APPROVAL = "pending_approval"
    PENDING_QUESTION = "pending_question"
    ACTIVE_TURN_WAIT = "active_turn_wait"
    FAILED = "failed"
    HISTORICAL_ONLY = "historical_only"
    UNAVAILABLE_PROMPT = "unavailable_prompt"


@dataclass(frozen=True, slots=True)
class TerminalHeaderState:
    session_id: SessionId
    status: SessionStatus
    mode: TerminalMode
    stream_status: TerminalStreamStatus = TerminalStreamStatus.LIVE
    model_name: str | None = None
    cwd: str | None = None
    approval_mode: str | None = None
    branch_label: str | None = None
    runtime_owner: str | None = None
    dashboard_url: str | None = None
    current_turn_id: TurnId | None = None
    last_sequence: int = 0
    stream_detail: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalHeaderDisplayState:
    session_label: str
    mode_label: str
    stream_label: str
    model_label: str
    cwd_label: str
    branch_label: str | None
    runtime_label: str
    dashboard_label: str
    last_update_label: str
    dashboard_url: str | None


@dataclass(frozen=True, slots=True)
class ComposerDraftState:
    text: str = ""
    question_id: QuestionId | None = None


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    kind: ConversationMessageKind
    text: str
    sequence: int
    message_id: MessageId | None = None
    turn_id: TurnId | None = None
    status: AssistantMessageStatus | None = None
    imported: bool = False


@dataclass(frozen=True, slots=True)
class ToolActivity:
    tool_call_id: ToolCallId
    turn_id: TurnId
    tool_name: str
    status: ToolActivityStatus
    sequence: int
    arguments_json: str | None = None
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None
    policy_reason: str | None = None
    output: tuple[str, ...] = ()
    summary: str | None = None
    exit_code: int | None = None
    artifact_paths: tuple[str, ...] = ()

    @property
    def output_text(self) -> str:
        return "".join(self.output)

    @property
    def output_preview(self) -> str:
        output_text = self.output_text
        if len(output_text) <= TOOL_OUTPUT_PREVIEW_CHARS:
            return output_text
        return f"{output_text[:TOOL_OUTPUT_PREVIEW_CHARS]}..."

    @property
    def output_truncated(self) -> bool:
        return len(self.output_text) > TOOL_OUTPUT_PREVIEW_CHARS


@dataclass(frozen=True, slots=True)
class PendingApprovalState:
    approval_id: ApprovalId
    turn_id: TurnId
    subject: str
    reason: str
    sequence: int
    tool_call_id: ToolCallId | None = None
    decision: ApprovalDecision | None = None
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalActionState:
    kind: TerminalActionKind
    title: str
    description: str
    turn_id: TurnId | None = None
    approval_id: ApprovalId | None = None
    question_id: QuestionId | None = None
    tool_call_id: ToolCallId | None = None
    related_tool_name: str | None = None
    subject: str | None = None
    reason: str | None = None
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None
    allowed_decisions: tuple[ApprovalDecision, ...] = ()
    answer_draft: str | None = None
    debug_id: str | None = None


@dataclass(frozen=True, slots=True)
class PendingQuestionState:
    question_id: QuestionId
    turn_id: TurnId
    tool_call_id: ToolCallId
    question: str
    sequence: int
    answer: str | None = None


@dataclass(frozen=True, slots=True)
class FailureState:
    message: str
    sequence: int
    turn_id: TurnId | None = None
    retryable: bool | None = None


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    turn_id: TurnId
    trigger_message_id: MessageId | None
    status: TurnStatus | str
    sequence: int
    messages: tuple[ConversationMessage, ...] = ()
    tools: tuple[ToolActivity, ...] = ()
    completed_outcome: str | None = None
    model_duration_ms: int | None = None
    model_input_tokens: int | None = None
    model_output_tokens: int | None = None
    failure_message: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalConversationState:
    header: TerminalHeaderState
    composer: ComposerDraftState = field(default_factory=ComposerDraftState)
    messages: tuple[ConversationMessage, ...] = ()
    turns: tuple[ConversationTurn, ...] = ()
    pending_approval: PendingApprovalState | None = None
    pending_question: PendingQuestionState | None = None
    failure: FailureState | None = None
    expanded_tool_ids: frozenset[ToolCallId] = frozenset()

    def with_dashboard_url(
        self,
        dashboard_url: str | None,
    ) -> Self:
        return replace(
            self,
            header=replace(self.header, dashboard_url=dashboard_url),
        )
