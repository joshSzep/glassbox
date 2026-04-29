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


class AutonomyMode(StrEnum):
    """Operator-selected posture for bounded autonomous local work."""

    MANUAL = "manual"
    GUIDED = "guided"
    INSPECT = "inspect"
    EDIT_SAFE = "edit-safe"
    TEST_DRIVEN = "test-driven"
    AUTONOMOUS_LOCAL = "autonomous-local"
    RELEASE_CANDIDATE = "release-candidate"


class AutonomyEscalationReason(StrEnum):
    """Reasons autonomy must pause or escalate to the operator."""

    APPROVAL_REQUIRED = "approval_required"
    BUDGET_EXHAUSTED = "budget_exhausted"
    POLICY_BLOCKED = "policy_blocked"
    VERIFICATION_FAILED = "verification_failed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    DAEMON_UNAVAILABLE = "daemon_unavailable"
    AMBIGUOUS_PLAN = "ambiguous_plan"


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


class BackgroundJobKind(StrEnum):
    """Coarse authority class for daemon-owned background jobs."""

    READ_ONLY_MAINTENANCE = "read_only_maintenance"
    DERIVED_INDEX = "derived_index"
    MUTATING_CONTINUATION = "mutating_continuation"


class BackgroundJobState(StrEnum):
    """Lifecycle states for daemon-owned background jobs."""

    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLATION_REQUESTED = "cancellation_requested"
    CANCELLED = "cancelled"
    STALE = "stale"
    ABANDONED = "abandoned"


class BackgroundJobRecoveryReason(StrEnum):
    """Reasons a background job needs durable recovery evidence."""

    DAEMON_RESTART = "daemon_restart"
    STALE_CLAIM = "stale_claim"
    DUPLICATE_CLAIM = "duplicate_claim"
    PROJECTION_REBUILD = "projection_rebuild"
    OPERATOR_REQUEST = "operator_request"


class BackgroundJobFailureKind(StrEnum):
    """Operator-facing failure classes for background jobs."""

    POLICY_BLOCKED = "policy_blocked"
    BUDGET_EXHAUSTED = "budget_exhausted"
    VERIFICATION_FAILED = "verification_failed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    DAEMON_UNAVAILABLE = "daemon_unavailable"
    STORAGE_ERROR = "storage_error"
    TOOL_ERROR = "tool_error"
    UNKNOWN = "unknown"


class WorkspaceMemoryKind(StrEnum):
    """Operator-facing categories for durable workspace memory."""

    FACT = "fact"
    CONVENTION = "convention"
    COMMAND = "command"
    FAILURE_PATTERN = "failure_pattern"
    ARCHITECTURE_NOTE = "architecture_note"
    USER_PREFERENCE = "user_preference"
    TASK_OUTCOME = "task_outcome"


class WorkspaceMemoryState(StrEnum):
    """Lifecycle states for workspace-scoped memory entries."""

    ACTIVE = "active"
    STALE = "stale"
    INVALIDATED = "invalidated"
    IMPORTED = "imported"
    PRUNED = "pruned"


class WorkspaceMemorySourceType(StrEnum):
    """Inspectable source classes for workspace memory provenance."""

    OPERATOR = "operator"
    SESSION_EVENT = "session_event"
    TASK = "task"
    ARTIFACT = "artifact"
    TOOL_RESULT = "tool_result"
    RUNTIME_NOTE = "runtime_note"
    IMPORT = "import"
