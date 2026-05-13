"""Operator-flow enum contracts shared by core models and queue helpers."""

from enum import StrEnum


class MaintenanceCueKind(StrEnum):
    """Workspace maintenance and recovery cue families."""

    PROJECTION_DRIFT = "projection_drift"
    STALE_DAEMON_OWNER = "stale_daemon_owner"
    FAILED_BACKGROUND_JOBS = "failed_background_jobs"
    ARTIFACT_PRESSURE = "artifact_pressure"
    BACKUP_POSTURE = "backup_posture"
    STALE_REPOSITORY_INTELLIGENCE = "stale_repository_intelligence"
    PROVIDER_CONFIG_ISSUES = "provider_config_issues"
    PACKAGE_ASSET_STALENESS = "package_asset_staleness"
    EVAL_BASELINE_DRIFT = "eval_baseline_drift"


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


__all__ = [
    "MaintenanceCueKind",
    "NextActionEvidenceKind",
    "NextActionKind",
    "NextActionPriority",
    "NextActionSafetyClass",
    "NextActionSeverity",
    "NextActionSurface",
    "NextActionTargetKind",
    "OperatorQueueDedupeScope",
    "OperatorQueueDismissalPolicy",
    "OperatorQueueFamily",
    "OperatorQueueState",
]
