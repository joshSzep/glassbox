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
    CANCELLING = "cancelling"
    ASSEMBLING_RESPONSE = "assembling_response"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
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


class ApprovalMode(StrEnum):
    """Supported approval modes for session and tool policy configuration."""

    CONFIRM = "confirm"
    REVIEW = "review"
    ON_REQUEST = "on-request"
    NEVER = "never"


class TaskPlanStatus(StrEnum):
    """Lifecycle states for a durable task plan."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"


class TaskStepStatus(StrEnum):
    """Lifecycle states for a task-plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskVerificationStatus(StrEnum):
    """Lifecycle states for a task verification run."""

    PLANNED = "planned"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskBlockedReason(StrEnum):
    """Operator-facing reasons a task cannot continue."""

    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_USER_INPUT = "awaiting_user_input"
    POLICY_BLOCKED = "policy_blocked"
    BUDGET_EXHAUSTED = "budget_exhausted"
    VERIFICATION_FAILED = "verification_failed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    DAEMON_UNAVAILABLE = "daemon_unavailable"
    AMBIGUOUS_PLAN = "ambiguous_plan"
    CANCELLED = "cancelled"
    MANUAL_PAUSE = "manual_pause"
    UNKNOWN = "unknown"
