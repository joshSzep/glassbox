"""Core Pydantic domain models for Glassbox."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from glassbox.core.ids import ApprovalId, MessageId, SessionId, ToolCallId, TurnId
from glassbox.core.types import SessionStatus, ToolExecutionStatus

MessagePartKind = Literal["text", "tool_result", "reasoning_summary"]
MessageRole = Literal["user", "assistant", "system"]


class SessionConfig(BaseModel):
    """Session-scoped configuration for a Glassbox runtime."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    cwd: Path
    approval_mode: str
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = Field(default=8765, ge=1, le=65535)
    persist_events: bool = True
    max_turns_per_input: int = Field(default=12, ge=1)


class SessionState(BaseModel):
    """Current runtime-facing state for a session."""

    model_config = ConfigDict(extra="forbid")

    session_id: SessionId
    status: SessionStatus
    current_turn_id: TurnId | None = None
    last_sequence: int = Field(default=0, ge=0)
    pending_approval_id: ApprovalId | None = None


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


class PolicyDecision(BaseModel):
    """The result of evaluating whether a tool action is allowed."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    requires_approval: bool
    reason: str
