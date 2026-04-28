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
from glassbox.core.ids import EventId
from glassbox.core.ids import MessageId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.ids import new_event_id
from glassbox.core.models import MessagePart
from glassbox.core.models import PolicyDecisionOutcome
from glassbox.core.models import PolicyDecisionSourceKind
from glassbox.core.models import PolicyRiskLevel
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import TurnStatus

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
