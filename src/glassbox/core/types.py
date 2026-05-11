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


class CheckpointAbsenceReason(StrEnum):
    """Why a session has no latest checkpoint projection."""

    IMPORTED_INSPECTION_ONLY = "imported_inspection_only"
    HISTORICAL_PRE_CHECKPOINT = "historical_pre_checkpoint"
    ACTIVE_CHECKPOINT_EXPECTED = "active_checkpoint_expected"
    PROJECTION_DEGRADED = "projection_degraded"
    NOT_EXPECTED_YET = "not_expected_yet"


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


class NextActionPriority(StrEnum):
    """Shared operator priority vocabulary for advisory next actions."""

    BLOCKED = "blocked"
    ACTION_NEEDED = "action-needed"
    DEGRADED = "degraded"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    HISTORICAL = "historical"
    MAINTENANCE_ONLY = "maintenance-only"


class NextActionSeverity(StrEnum):
    """Impact level for a next action within its priority bucket."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class NextActionKind(StrEnum):
    """Operator workflow family for a next action."""

    INSPECT = "inspect"
    ANSWER = "answer"
    APPROVE = "approve"
    RECOVER = "recover"
    REFRESH = "refresh"
    VERIFY = "verify"
    REVIEW = "review"
    HANDOFF = "handoff"
    MAINTAIN = "maintain"
    DOCUMENT = "document"


class NextActionSafetyClass(StrEnum):
    """Safety boundary for carrying out a next action."""

    READ_ONLY = "read_only"
    PLAN_ONLY = "plan_only"
    OPERATOR_DECISION = "operator_decision"
    COMMAND_RECIPE = "command_recipe"
    WORKSPACE_WRITE = "workspace_write"
    PUBLICATION_BLOCKED = "publication_blocked"


class NextActionTargetKind(StrEnum):
    """Supported local targets for next-action routing."""

    WORKSPACE = "workspace"
    SESSION = "session"
    TURN = "turn"
    TASK = "task"
    CHANGESET = "changeset"
    REVIEW_FEEDBACK = "review_feedback"
    VERIFICATION = "verification"
    REPOSITORY_INTELLIGENCE = "repository_intelligence"
    MEMORY = "memory"
    BACKGROUND_JOB = "background_job"
    ARTIFACT = "artifact"
    PROVIDER = "provider"
    PROJECTION = "projection"
    RELEASE = "release"
    UNKNOWN = "unknown"


class NextActionEvidenceKind(StrEnum):
    """Compact evidence reference classes for next-action support."""

    EVENT = "event"
    ARTIFACT = "artifact"
    COMMAND = "command"
    TOOL_ATTEMPT = "tool_attempt"
    VERIFICATION = "verification"
    REVIEW_FEEDBACK = "review_feedback"
    MANUAL_EVIDENCE = "manual_evidence"
    MEMORY = "memory"
    REPOSITORY_INTELLIGENCE = "repository_intelligence"
    EVAL = "eval"
    BACKGROUND_JOB = "background_job"
    RELEASE_GATE = "release_gate"
    PROJECTION = "projection"
    API_RESPONSE = "api_response"
    CLI_OUTPUT = "cli_output"


class NextActionSurface(StrEnum):
    """Consumer surface where a next action is useful."""

    CLI = "cli"
    TUI = "tui"
    DASHBOARD = "dashboard"
    API = "api"
    REVIEW_BRIEF = "review_brief"
    HANDOFF = "handoff"
    RELEASE_EVIDENCE = "release_evidence"


class OperatorQueueFamily(StrEnum):
    """Operator attention families for one unified queue."""

    WORK_BLOCKING = "work_blocking"
    REVIEW_BLOCKING = "review_blocking"
    VERIFICATION_BLOCKING = "verification_blocking"
    MAINTENANCE = "maintenance"
    ADVISORY = "advisory"
    INFORMATIONAL = "informational"


class OperatorQueueState(StrEnum):
    """Current posture of a derived operator queue item."""

    ACTION_NEEDED = "action_needed"
    BLOCKED = "blocked"
    ACTIVE = "active"
    STALE = "stale"
    DEGRADED = "degraded"
    READY = "ready"
    WATCHING = "watching"
    HISTORICAL = "historical"


class OperatorQueueDismissalPolicy(StrEnum):
    """How a derived queue item may leave the visible queue."""

    NOT_DISMISSIBLE = "not_dismissible"
    DISMISSIBLE_UNTIL_CHANGED = "dismissible_until_changed"
    DISMISSIBLE_FOR_SESSION = "dismissible_for_session"
    CANONICAL_DECISION_REQUIRED = "canonical_decision_required"


class OperatorQueueDedupeScope(StrEnum):
    """Scope used to merge queue items that point at the same problem."""

    TARGET = "target"
    FAMILY_TARGET = "family_target"
    EVIDENCE_FINGERPRINT = "evidence_fingerprint"
    WORKSPACE_SINGLETON = "workspace_singleton"


class EvidenceGraphNodeKind(StrEnum):
    """Local evidence node families used in derived evidence graphs."""

    EVENT = "event"
    ARTIFACT = "artifact"
    COMMAND = "command"
    TOOL_ATTEMPT = "tool_attempt"
    VERIFICATION_CHECK = "verification_check"
    REVIEW_FEEDBACK = "review_feedback"
    MANUAL_EVIDENCE = "manual_evidence"
    MEMORY_ENTRY = "memory_entry"
    REPOSITORY_INTELLIGENCE_SOURCE = "repository_intelligence_source"
    EVAL_CASE = "eval_case"
    BACKGROUND_JOB = "background_job"
    RELEASE_GATE_ROW = "release_gate_row"
    PROJECTION = "projection"
    NEXT_ACTION = "next_action"
    CLAIM = "claim"


class EvidenceGraphEdgeKind(StrEnum):
    """Relationship kinds between evidence graph nodes."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    MAKES_STALE = "makes-stale"
    VERIFIES = "verifies"
    SKIPPED_BY = "skipped-by"
    ACCEPTED_RISK_FOR = "accepted-risk-for"
    DERIVED_FROM = "derived-from"
    SAFE_NEXT_ACTION_FOR = "safe-next-action-for"


class EvidenceGraphConfidence(StrEnum):
    """Confidence posture for evidence graph nodes, edges, and claims."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class EvidenceGraphFreshness(StrEnum):
    """Freshness posture for evidence referenced by a graph."""

    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    SUPERSEDED = "superseded"
    MANUAL_ONLY = "manual-only"
    UNKNOWN = "unknown"


class EvidenceGraphRedactionStatus(StrEnum):
    """Whether graph evidence can be shown in reviewer-safe contexts."""

    SAFE_SUMMARY = "safe_summary"
    LOCAL_ONLY = "local_only"
    REDACTED = "redacted"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class EvidenceGraphVisibility(StrEnum):
    """Visibility class for evidence graph material."""

    OPERATOR_ONLY = "operator_only"
    REVIEWER_SAFE = "reviewer_safe"
    RELEASE_SAFE = "release_safe"


class ClaimSupportState(StrEnum):
    """How well local evidence supports a graph claim."""

    SUPPORTED = "supported"
    MISSING = "missing"
    STALE = "stale"
    CONTRADICTED = "contradicted"
    MANUAL_ONLY = "manual-only"
    ACCEPTED_WITH_RISK = "accepted_with_risk"
    UNSUPPORTED = "unsupported"


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

    CHANGESET_INVENTORY = "changeset_inventory"
    COMMAND_RECIPE = "command_recipe"
    EVAL_RECOMMENDATION = "eval_recommendation"
    MANUAL_EVIDENCE = "manual_evidence"
    RELEASE_GATE = "release_gate"
    REPOSITORY_INTELLIGENCE = "repository_intelligence"
    WORKSPACE_PROFILE = "workspace_profile"
    CHANGED_PATHS = "changed_paths"
    TASK_TYPE = "task_type"
    POLICY_BUDGET = "policy_budget"
    OPERATOR = "operator"


class VerificationPlanLifecycleState(StrEnum):
    """Reviewable lifecycle states for planned verification checks."""

    PROPOSED = "proposed"
    SELECTED = "selected"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    STALE = "stale"
    SUPERSEDED = "superseded"
    ACCEPTED_RISK = "accepted-risk"
    MANUAL_ONLY = "manual-only"
    BLOCKED = "blocked"


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


class ChangesetSourceKind(StrEnum):
    """Source classes that can explain where a changeset came from."""

    SESSION = "session"
    TASK = "task"
    BRANCH_SEARCH_CANDIDATE = "branch_search_candidate"
    WORKSPACE_DIFF = "workspace_diff"
    ARTIFACT = "artifact"
    OPERATOR = "operator"
    IMPORT = "import"


class ChangesetInventoryFreshness(StrEnum):
    """Freshness states for changeset inventory artifacts."""

    FRESH = "fresh"
    STALE = "stale"
    SUPERSEDED = "superseded"
    UNKNOWN = "unknown"


class ChangesetRiskLevel(StrEnum):
    """Advisory review risk levels for a changeset or changed path."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ChangesetVerificationState(StrEnum):
    """Review-time verification posture for a changeset."""

    PLANNED = "planned"
    MISSING = "missing"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    STALE = "stale"
    SKIPPED = "skipped"
    ACCEPTED_WITH_RISK = "accepted_with_risk"
    NOT_APPLICABLE = "not_applicable"


class ReviewFeedbackKind(StrEnum):
    """Local review feedback classes captured as changeset evidence."""

    REQUESTED_CHANGE = "requested_change"
    REVIEWER_QUESTION = "reviewer_question"
    OPERATOR_NOTE = "operator_note"
    OBSERVATION = "observation"
    RISK = "risk"


class ReviewFeedbackProvenance(StrEnum):
    """Where a local review feedback record came from."""

    REVIEWER = "reviewer"
    OPERATOR = "operator"
    MANUAL = "manual"
    IMPORTED = "imported"
    UNKNOWN = "unknown"


class ReviewFeedbackScopeKind(StrEnum):
    """Supported local scope targets for review feedback."""

    CHANGESET = "changeset"
    FILE = "file"
    TASK = "task"
    TURN = "turn"
    ARTIFACT = "artifact"
    VERIFICATION = "verification"
    BRANCH_CANDIDATE = "branch_candidate"


class ReviewFeedbackDisposition(StrEnum):
    """Local lifecycle state for review feedback."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESPONDED = "responded"
    RESOLVED_LOCALLY = "resolved_locally"
    ACCEPTED_WITH_RISK = "accepted_with_risk"
    ARCHIVED = "archived"


class ReviewFixupSourceKind(StrEnum):
    """Source categories for response-linked fixup inventory evidence."""

    SESSION_TURN = "session_turn"
    TASK_STEP = "task_step"
    MANUAL_WORKSPACE_EDIT = "manual_workspace_edit"
    BRANCH_CANDIDATE = "branch_candidate"
    WORKTREE = "worktree"
    OPERATOR_NOTE = "operator_note"
    VERIFICATION = "verification"
    MANUAL_EVIDENCE = "manual_evidence"


class ManualEvidenceKind(StrEnum):
    """Manual evidence classes accepted into the local review loop."""

    MANUAL_COMMAND = "manual_command"
    EXTERNAL_CHECK = "external_check"
    REVIEWER_NOTE = "reviewer_note"
    SCREENSHOT = "screenshot"
    BROWSER_OBSERVATION = "browser_observation"
    ACCESSIBILITY_NOTE = "accessibility_note"
    LOCAL_FILE_REFERENCE = "local_file_reference"
    SANITIZED_LOG = "sanitized_log"
    OPERATOR_ASSERTION = "operator_assertion"


class ManualEvidenceTargetKind(StrEnum):
    """Local review-loop targets that manual evidence may cite."""

    CHANGESET = "changeset"
    FEEDBACK = "feedback"
    RESPONSE = "response"
    VERIFICATION_REQUIREMENT = "verification_requirement"
    REVIEW_BRIEF = "review_brief"
    PUBLICATION_BOUNDARY = "publication_boundary"
    UNKNOWN = "unknown"


class ManualEvidenceState(StrEnum):
    """Lifecycle state for one manual evidence record."""

    ATTACHED = "attached"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ManualEvidenceRedactionStatus(StrEnum):
    """Outcome of manual evidence redaction checks."""

    PASSED = "passed"
    REDACTED = "redacted"
    LOCAL_ONLY = "local_only"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class ManualEvidenceFreshness(StrEnum):
    """Freshness posture for manual review-loop evidence."""

    CURRENT = "current"
    NEEDS_INSPECTION = "needs_inspection"
    STALE = "stale"
    UNKNOWN = "unknown"


class ReviewResponseState(StrEnum):
    """Derived local response posture for review feedback."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    RESPONDED = "responded"
    RESOLVED = "resolved"
    READY_FOR_HANDOFF = "ready_for_handoff"
    REOPENED = "reopened"
    BLOCKED = "blocked"
    ACCEPTED_WITH_RISK = "accepted_with_risk"
    NOT_APPLICABLE = "not_applicable"


class ChangesetReadinessKind(StrEnum):
    """Kinds of readiness decisions a changeset can carry."""

    REVIEW = "review"
    COMMIT = "commit"


class ChangesetReadinessState(StrEnum):
    """Advisory readiness states for review and commit preparation."""

    READY = "ready"
    BLOCKED = "blocked"
    NEEDS_VERIFICATION = "needs_verification"
    NEEDS_REVIEW = "needs_review"
    STALE_INVENTORY = "stale_inventory"
    DIRTY_UNTRACKED_RISK = "dirty_untracked_risk"
    FAILED_CHECKS = "failed_checks"
    MISSING_PROVENANCE = "missing_provenance"
    ACCEPTED_WITH_RISK = "accepted_with_risk"
    NOT_READY = "not_ready"


class WorktreeState(StrEnum):
    """Lifecycle and inspection states for a local temporary worktree."""

    ACTIVE = "active"
    MISSING = "missing"
    DIRTY = "dirty"
    CLEANUP_READY = "cleanup_ready"
    CLEANUP_BLOCKED = "cleanup_blocked"
    CLEANED = "cleaned"
    UNSUPPORTED = "unsupported"


class WorktreeSourceKind(StrEnum):
    """Sources that can explain why a temporary worktree exists."""

    BRANCH_SEARCH_CANDIDATE = "branch_search_candidate"
    CHANGESET = "changeset"
    TASK = "task"
    SESSION = "session"
    MANUAL = "manual"


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


class CommandPurpose(StrEnum):
    """Review-oriented purpose classes for retained command evidence."""

    INSPECT = "inspect"
    TEST = "test"
    LINT = "lint"
    TYPECHECK = "typecheck"
    BUILD = "build"
    PACKAGE = "package"
    EVAL = "eval"
    RELEASE_GATE = "release_gate"
    PUBLISH = "publish"
    DEPLOY = "deploy"
    CLEANUP = "cleanup"
    UNKNOWN = "unknown"
    DANGEROUS = "dangerous"


class CommandReviewRelevance(StrEnum):
    """How a classified command should be interpreted during review."""

    INSPECTION = "inspection"
    VERIFICATION = "verification"
    LOCAL_ARTIFACT = "local_artifact"
    RELEASE_OR_REMOTE_MUTATION = "release_or_remote_mutation"
    CLEANUP_OR_DESTRUCTIVE = "cleanup_or_destructive"
    UNKNOWN = "unknown"


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
    REPOSITORY_INTELLIGENCE = "repository_intelligence"
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


class RepositoryIntelligenceConfidence(StrEnum):
    """Confidence classes for advisory repository intelligence records."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class RepositoryIntelligencePathKind(StrEnum):
    """Repository path roles carried by v2 intelligence snapshots."""

    SOURCE_ROOT = "source_root"
    TEST_ROOT = "test_root"
    DOC_ROOT = "doc_root"
    GENERATED_PATH = "generated_path"
    CACHE_PATH = "cache_path"
    BUILD_OUTPUT = "build_output"
    POLICY_SENSITIVE_PATH = "policy_sensitive_path"


class RepositoryIntelligencePackageKind(StrEnum):
    """Package and workspace boundary kinds."""

    PYTHON = "python"
    FRONTEND = "frontend"
    NODE_WORKSPACE = "node_workspace"
    EVAL = "eval"
    DOCS = "docs"
    RELEASE = "release"
    GENERIC = "generic"


class RepositoryIntelligenceCommandRisk(StrEnum):
    """Advisory command recipe risk classes."""

    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"
    NETWORK = "network"
    RELEASE = "release"
    DESTRUCTIVE = "destructive"
    UNKNOWN = "unknown"


class RepositoryIntelligenceReleaseSurfaceKind(StrEnum):
    """Release-sensitive surface classes for repository intelligence."""

    COMMIT_TIME = "commit_time"
    PUSH_TIME = "push_time"
    RELEASE_CANDIDATE = "release_candidate"
    ADVISORY = "advisory"
