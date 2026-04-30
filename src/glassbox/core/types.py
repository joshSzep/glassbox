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


class TurnRecoveryState(StrEnum):
    """Operator-facing recovery posture for an interrupted or in-flight turn."""

    ACTIVE = "active"
    INCOMPLETE = "incomplete"
    RECOVERABLE = "recoverable"
    ABANDONED = "abandoned"
    RESUMED = "resumed"
    NON_RESUMABLE = "non_resumable"


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
    RETRIED = "retried"
    ACCEPTED_WITH_RISK = "accepted_with_risk"


class VerificationCheckKind(StrEnum):
    """Supported verification check families."""

    COMMAND = "command"
    TEST = "test"
    EVAL = "eval"
    LINT = "lint"
    TYPECHECK = "typecheck"
    PACKAGE = "package"
    CUSTOM = "custom"


class VerificationPlanSource(StrEnum):
    """Signals used to select a verification plan entry."""

    EVAL_RECOMMENDATION = "eval_recommendation"
    WORKSPACE_PROFILE = "workspace_profile"
    CHANGED_PATHS = "changed_paths"
    TASK_TYPE = "task_type"
    POLICY_BUDGET = "policy_budget"
    OPERATOR = "operator"


class VerificationFailureCategory(StrEnum):
    """Evidence-based categories for verification failure output."""

    ASSERTION = "assertion"
    LINT = "lint"
    TYPECHECK = "typecheck"
    PACKAGE = "package"
    POLICY = "policy"
    BUDGET = "budget"
    TIMEOUT = "timeout"
    INFRASTRUCTURE = "infrastructure"
    FLAKY = "flaky"
    UNKNOWN = "unknown"


class BranchSearchStatus(StrEnum):
    """Lifecycle states for a bounded branch-search workflow."""

    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class BranchCandidateStatus(StrEnum):
    """Lifecycle states for one branch-search candidate."""

    PLANNED = "planned"
    FORKED = "forked"
    EXECUTED = "executed"
    VERIFIED = "verified"
    SELECTED = "selected"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class BranchCandidateVerificationStatus(StrEnum):
    """Verification outcome for one branch-search candidate."""

    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMED_OUT = "timed_out"
    INCONCLUSIVE = "inconclusive"


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
    CONTINUATION_WINDOW_EXPIRED = "continuation_window_expired"
    SCHEDULED_PAUSE = "scheduled_pause"
    UNKNOWN = "unknown"


class PauseWindowPolicy(StrEnum):
    """Local pause-window boundaries for long-running task work."""

    BEFORE_TIME = "before_time"
    AFTER_CHECKPOINT = "after_checkpoint"
    BEFORE_RISKY_ACTION = "before_risky_action"


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


class LongRunPhase(StrEnum):
    """Operator-visible phases for long-running local work."""

    PREPARING = "preparing"
    MODEL_CALL = "model_call"
    TOOL_EXECUTION = "tool_execution"
    CHECKPOINTING = "checkpointing"
    COMPACTING_CONTEXT = "compacting_context"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class LongRunPhaseState(StrEnum):
    """State of a long-running phase transition."""

    ENTERED = "entered"
    HEARTBEAT = "heartbeat"
    EXITED = "exited"
    BLOCKED = "blocked"


class ContextCompactionScope(StrEnum):
    """Scope of a durable context compaction artifact."""

    TRANSCRIPT = "transcript"
    TASK = "task"
    RUNTIME_CONTEXT = "runtime_context"
    VERIFICATION = "verification"
    TOOL_OUTPUT = "tool_output"


class ContextCompactionFreshness(StrEnum):
    """Freshness posture for compaction artifacts."""

    FRESH = "fresh"
    STALE = "stale"
    INVALIDATED = "invalidated"
    UNKNOWN = "unknown"


class ToolAttemptStatus(StrEnum):
    """Durable status values for a long-running tool attempt."""

    STARTED = "started"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"
    RETRIED = "retried"
    ABANDONED = "abandoned"


class ToolAttemptRetryClassification(StrEnum):
    """Operator-facing retry and resume posture for a tool attempt."""

    RETRYABLE = "retryable"
    UNSAFE_TO_RETRY = "unsafe_to_retry"
    IDEMPOTENT = "idempotent"
    UNKNOWN = "unknown"
    ALREADY_RUNNING = "already_running"
    ABANDONED = "abandoned"


class RecoveryDecision(StrEnum):
    """Operator-facing recovery decisions for interrupted long work."""

    RESUME = "resume"
    RETRY = "retry"
    FORK = "fork"
    ABANDON = "abandon"
    WAIT_FOR_OPERATOR = "wait_for_operator"
    NON_RESUMABLE = "non_resumable"


class ResumeOutcomeStatus(StrEnum):
    """Outcome of attempting to resume from durable recovery state."""

    RESUMED = "resumed"
    REJECTED_STALE = "rejected_stale"
    REJECTED_NON_RESUMABLE = "rejected_non_resumable"
    FAILED = "failed"


class ProviderRecoveryKind(StrEnum):
    """Operator-facing provider failure and degradation classes."""

    RETRYABLE_ERROR = "retryable_error"
    NON_RETRYABLE_ERROR = "non_retryable_error"
    LOST_STREAM = "lost_stream"
    MALFORMED_TOOL_CALL = "malformed_tool_call"
    RATE_LIMIT = "rate_limit"
    CREDENTIAL_CHANGE = "credential_change"
    DEGRADED_PROVIDER_POSTURE = "degraded_provider_posture"


class ProviderRecoveryAction(StrEnum):
    """Bounded recovery action recorded for provider failures."""

    RETRY_SCHEDULED = "retry_scheduled"
    RETRYING = "retrying"
    RETRY_EXHAUSTED = "retry_exhausted"
    STOPPED_CHECKPOINT_REQUIRED = "stopped_checkpoint_required"
    DEGRADED = "degraded"
    CONTINUE_WITH_CAUTION = "continue_with_caution"


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


class RepositoryIndexEntityKind(StrEnum):
    """Kinds of deterministic repository intelligence entries."""

    PROJECT_MARKER = "project_marker"
    FILE = "file"
    MODULE = "module"
    SYMBOL = "symbol"
    COMMAND = "command"
    TEST = "test"
    DOC = "doc"
    EVAL_CASE = "eval_case"
    OWNERSHIP_HINT = "ownership_hint"
    DEPENDENCY_HINT = "dependency_hint"
    RECENT_PATH = "recent_path"


class RepositoryIndexFreshness(StrEnum):
    """Freshness states for rebuildable repository index snapshots."""

    FRESH = "fresh"
    STALE = "stale"
    BUILDING = "building"
    FAILED = "failed"


class RepositoryIndexSourceType(StrEnum):
    """Inspectable source classes for repository index entries."""

    FILE_SYSTEM = "file_system"
    MANIFEST = "manifest"
    DOCUMENTATION = "documentation"
    TEST = "test"
    EVAL = "eval"
    STATIC_ANALYSIS = "static_analysis"
    GIT = "git"
    USER_HINT = "user_hint"
