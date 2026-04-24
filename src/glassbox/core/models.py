"""Core Pydantic domain models for Glassbox."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from glassbox.core.ids import (
    ApprovalId,
    MessageId,
    QuestionId,
    SessionId,
    ToolCallId,
    TurnId,
)
from glassbox.core.types import (
    ApprovalMode,
    ApprovalStatus,
    SessionStatus,
    ToolExecutionStatus,
)

MessagePartKind = Literal["text", "tool_result", "reasoning_summary"]
MessageRole = Literal["user", "assistant", "system"]


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


class ApprovalRecord(BaseModel):
    """A query-friendly view of an approval request."""

    model_config = ConfigDict(extra="forbid")

    approval_id: ApprovalId
    turn_id: TurnId
    subject: str
    reason: str
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
