"""Shared provider recommendation models and enums."""

from enum import StrEnum

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.types import AutonomyMode


class ProviderTaskKind(StrEnum):
    """Workflow categories used for provider recommendations."""

    INSPECTION = "inspection"
    CODING = "coding"
    VERIFICATION = "verification"
    BRANCH_SEARCH = "branch-search"
    BACKGROUND = "background"
    RELEASE = "release"


class ProviderRecommendationConfidence(StrEnum):
    """Confidence levels for advisory provider recommendations."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProviderRecommendationPosture(StrEnum):
    """Recommendation posture for the selected provider/model."""

    RECOMMENDED = "recommended"
    USABLE = "usable"
    RISKY = "risky"
    LOCAL_FALLBACK = "local_fallback"


class ProviderCapabilityFit(StrEnum):
    """How well retained evidence covers the workflow capabilities."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class ProviderRiskPosture(StrEnum):
    """Risk posture for using the selected provider in the workflow."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ProviderCredentialReadiness(StrEnum):
    """Credential readiness for provider-backed work."""

    READY = "ready"
    MISSING = "missing"
    NOT_REQUIRED = "not_required"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class ProviderRecommendedAction(StrEnum):
    """Concrete advisory action for continuing after provider posture changes."""

    CONTINUE = "continue"
    RETRY = "retry"
    PAUSE = "pause"
    SWITCH_PROVIDER = "switch_provider"
    LOCAL_FALLBACK = "local_fallback"
    FIX_CREDENTIALS = "fix_credentials"
    REFRESH_EVIDENCE = "refresh_evidence"


class ProviderFailurePosture(BaseModel):
    """Latest provider recovery evidence folded into recommendations."""

    model_config = ConfigDict(extra="forbid")

    state: str
    provider: str | None = None
    model_name: str | None = None
    failure_kind: str | None = None
    recovery_action: str | None = None
    retryable: bool = False
    safe_to_continue: bool | None = None
    degraded: bool = False
    repeated_failure_count: int = 0
    latest_reason: str | None = None
    operator_next_action: str | None = None


class ProviderBudgetImpact(BaseModel):
    """Budget-relevant retry and pause impact for advisory recommendations."""

    model_config = ConfigDict(extra="forbid")

    retry_delay_seconds: int | None = None
    retry_attempt: int | None = None
    max_attempts: int | None = None
    next_retry_at: str | None = None
    budget_warning: str | None = None


class ProviderRecommendationEvidence(BaseModel):
    """Evidence inputs used for one recommendation."""

    model_config = ConfigDict(extra="forbid")

    diagnostics_state: str
    runtime_mode: str
    canary_status: str
    freshness_status: str
    canary_stale: bool = False
    model_identity_matches_config: bool | None = None
    scenario_count: int = 0
    matrix_entry_count: int = 0
    relevant_scenarios: list[str] = Field(default_factory=list)
    relevant_passed: list[str] = Field(default_factory=list)
    relevant_preflight: list[str] = Field(default_factory=list)
    relevant_skipped_or_missing: list[str] = Field(default_factory=list)


class ProviderRecommendation(BaseModel):
    """Non-authoritative provider/model recommendation for a workflow."""

    model_config = ConfigDict(extra="forbid")

    advisory: bool = True
    auto_applied: bool = False
    task_kind: ProviderTaskKind
    autonomy_mode: AutonomyMode
    recommended_model_name: str
    provider: str
    posture: ProviderRecommendationPosture
    confidence: ProviderRecommendationConfidence
    capability_fit: ProviderCapabilityFit
    risk_posture: ProviderRiskPosture
    evidence_freshness: str
    credential_readiness: ProviderCredentialReadiness
    recommended_action: ProviderRecommendedAction
    failure_posture: ProviderFailurePosture
    budget_impact: ProviderBudgetImpact
    required_capabilities: list[str]
    reasons: list[str]
    warnings: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    evidence: ProviderRecommendationEvidence
    next_actions: list[str] = Field(default_factory=list)
