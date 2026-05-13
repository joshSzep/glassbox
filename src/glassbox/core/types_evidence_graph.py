"""Evidence graph enum contracts shared across Glassbox surfaces."""

from enum import StrEnum


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


__all__ = [
    "ClaimSupportState",
    "EvidenceGraphConfidence",
    "EvidenceGraphEdgeKind",
    "EvidenceGraphFreshness",
    "EvidenceGraphNodeKind",
    "EvidenceGraphRedactionStatus",
    "EvidenceGraphVisibility",
]
