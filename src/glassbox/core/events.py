"""Event envelope and payload models for the Glassbox event log."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from glassbox.core.ids import (
    ApprovalId,
    ArtifactId,
    EventId,
    MessageId,
    SessionId,
    ToolCallId,
    TurnId,
    new_event_id,
)
from glassbox.core.models import MessagePart
from glassbox.core.types import ApprovalDecision, TurnStatus

ToolOutputStream = Literal["stdout", "stderr", "structured"]
TurnOutcome = Literal["completed", "awaiting_approval", "failed"]
ErrorScope = Literal["session", "turn", "tool", "web"]


class EventPayload(BaseModel):
    """Base class for all persisted event payloads."""

    model_config = ConfigDict(extra="forbid")


class SessionStarted(EventPayload):
    event_type: Literal["SessionStarted"] = "SessionStarted"
    cwd: str
    dashboard_url: str | None = None
    model_name: str
    approval_mode: str


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


class ToolExecutionStarted(EventPayload):
    event_type: Literal["ToolExecutionStarted"] = "ToolExecutionStarted"
    turn_id: TurnId
    tool_call_id: ToolCallId
    tool_name: str


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


class ApprovalResolved(EventPayload):
    event_type: Literal["ApprovalResolved"] = "ApprovalResolved"
    approval_id: ApprovalId
    decision: ApprovalDecision
    decided_by: str


class RuntimeNoteRecorded(EventPayload):
    event_type: Literal["RuntimeNoteRecorded"] = "RuntimeNoteRecorded"
    category: str
    message: str


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
    | AssistantMessageStarted
    | AssistantMessageDelta
    | AssistantMessageCompleted
    | TurnStarted
    | TurnStatusChanged
    | TurnCompleted
    | TurnFailed
    | ModelCallStarted
    | ModelCallCompleted
    | ModelToolCallRequested
    | ToolExecutionStarted
    | ToolOutputChunk
    | ToolArtifactRecorded
    | ToolExecutionCompleted
    | ApprovalRequested
    | ApprovalResolved
    | RuntimeNoteRecorded
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
