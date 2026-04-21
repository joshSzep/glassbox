"""Shared domain state types for Glassbox."""

from enum import StrEnum


class SessionStatus(StrEnum):
    """Lifecycle states for a session."""

    IDLE = "idle"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_USER_INPUT = "awaiting_user_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TurnStatus(StrEnum):
    """Lifecycle states for a turn."""

    PENDING = "pending"
    BUILDING_CONTEXT = "building_context"
    CALLING_MODEL = "calling_model"
    STREAMING_MODEL = "streaming_model"
    EXECUTING_TOOL = "executing_tool"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_USER_INPUT = "awaiting_user_input"
    ASSEMBLING_RESPONSE = "assembling_response"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolExecutionStatus(StrEnum):
    """Lifecycle states for a tool execution."""

    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(StrEnum):
    """State of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class ApprovalDecision(StrEnum):
    """Explicit operator decision for an approval request."""

    APPROVED = "approved"
    DENIED = "denied"
