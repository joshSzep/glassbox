"""Local handoff enum contracts shared across Glassbox surfaces."""

from enum import StrEnum


class HandoffIntent(StrEnum):
    """Recipient intent for a local handoff package or readiness result."""

    REVIEW_ONLY = "review-only"
    CONTINUE_WORK = "continue-work"
    VERIFICATION_NEEDED = "verification-needed"
    FAILURE_TRIAGE = "failure-triage"
    RELEASE_SIGNOFF = "release-signoff"
    FUTURE_SELF = "future-self"
    FORK_RECOMMENDED = "fork-recommended"


class HandoffSourceKind(StrEnum):
    """Supported source contexts for local handoff."""

    SESSION = "session"
    TASK = "task"
    CHANGESET = "changeset"
    WORKSPACE = "workspace"
    RELEASE = "release"
    FUTURE_SELF = "future-self"
    IMPORTED_PACKAGE = "imported-package"


class HandoffPackageKind(StrEnum):
    """Portable handoff package families."""

    SESSION = "session-handoff"
    TASK = "task-handoff"
    CHANGESET = "changeset-handoff"
    WORKSPACE = "workspace-handoff"
    RELEASE = "release-handoff"
    FUTURE_SELF = "future-self-handoff"
    IMPORT_TRIAGE = "import-triage"


class HandoffLabelSource(StrEnum):
    """Where recipient, custodian, or exporter label metadata came from."""

    OPERATOR = "operator"
    PACKAGE = "package"
    IMPORT = "import"
    RUNTIME = "runtime"
    CONFIG = "config"
    UNKNOWN = "unknown"


class HandoffLabelMetadataPosture(StrEnum):
    """Portability posture for label metadata."""

    PORTABLE = "portable"
    LOCAL_ONLY = "local-only"
    REDACTED = "redacted"
    UNKNOWN = "unknown"


class HandoffReadinessState(StrEnum):
    """Shared readiness states for handoff sources."""

    READY = "ready"
    HISTORICAL_ONLY = "historical-only"
    AWAITING_APPROVAL = "awaiting-approval"
    AWAITING_ANSWER = "awaiting-answer"
    NEEDS_CONTEXT = "needs-context"
    NEEDS_VERIFICATION = "needs-verification"
    FAILED_NEEDS_TRIAGE = "failed-needs-triage"
    LOCAL_ONLY_EVIDENCE = "local-only-evidence"
    STALE_EVIDENCE = "stale-evidence"
    BLOCKED = "blocked"
    ACCEPTED_WITH_RISK = "accepted-with-risk"


class HandoffReadinessReasonKind(StrEnum):
    """Reason buckets explaining a handoff readiness state."""

    SUPPORTING_EVIDENCE = "supporting-evidence"
    MISSING_EVIDENCE = "missing-evidence"
    STALE_EVIDENCE = "stale-evidence"
    REDACTED_EVIDENCE = "redacted-evidence"
    LOCAL_ONLY_EVIDENCE = "local-only-evidence"
    MANUAL_ONLY_EVIDENCE = "manual-only-evidence"
    SKIPPED_EVIDENCE = "skipped-evidence"
    UNSUPPORTED_EVIDENCE = "unsupported-evidence"
    ACCEPTED_RISK = "accepted-risk"
    COMPATIBILITY_WARNING = "compatibility-warning"
    POLICY_BLOCKER = "policy-blocker"
    RUNTIME_OWNER_BLOCKER = "runtime-owner-blocker"
    PACKAGE_LIMITATION = "package-limitation"


class HandoffEvidenceFreshness(StrEnum):
    """Freshness posture for portable handoff evidence."""

    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class HandoffRedactionPosture(StrEnum):
    """Package redaction posture."""

    REVIEWER_SAFE = "reviewer-safe"
    REDACTED = "redacted"
    LOCAL_ONLY_OMITTED = "local-only-omitted"
    RAW_INCLUDED = "raw-included"
    UNKNOWN = "unknown"


class HandoffCompatibilityState(StrEnum):
    """Compatibility status for a handoff package."""

    SUPPORTED = "supported"
    SUPPORTED_WITH_WARNINGS = "supported-with-warnings"
    LEGACY_INSPECTION_ONLY = "legacy-inspection-only"
    UNSUPPORTED = "unsupported"
    FUTURE_VERSION = "future-version"
    INVALID = "invalid"


__all__ = [
    "HandoffCompatibilityState",
    "HandoffEvidenceFreshness",
    "HandoffIntent",
    "HandoffLabelMetadataPosture",
    "HandoffLabelSource",
    "HandoffPackageKind",
    "HandoffReadinessReasonKind",
    "HandoffReadinessState",
    "HandoffRedactionPosture",
    "HandoffSourceKind",
]
