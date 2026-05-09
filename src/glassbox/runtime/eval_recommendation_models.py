"""Structured models for replay/eval change-impact recommendations."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from glassbox.runtime.evals import EvalProfileTrack
from glassbox.runtime.evals import EvalVerificationStage

type EvalRecommendationConfidence = Literal[
    "direct",
    "owner-derived",
    "capability-derived",
    "stage-derived",
    "fallback",
]
type EvalRecommendationReasonGroupKind = Literal[
    "direct-path",
    "owner-derived-rule",
    "capability-derived-rule",
    "stage-derived-profile",
    "release-gate-recommendation",
    "fallback-policy",
]
type EvalVerificationRecipeConfidence = Literal["direct", "topology", "degraded"]
type EvalVerificationRecipeSource = Literal["recipe", "topology"]
type EvalTestTargetConfidence = Literal[
    "direct",
    "topology-derived",
    "naming-derived",
    "package-derived",
    "recipe-derived",
    "fallback",
]
type EvalTestTargetSource = Literal[
    "repository-intelligence",
    "topology",
    "naming",
    "package",
    "recipe",
    "fallback",
]
type PathVerificationConfidence = Literal[
    "direct",
    "topology-derived",
    "naming-derived",
    "package-derived",
    "recipe-derived",
    "owner-derived",
    "capability-derived",
    "stage-derived",
    "fallback",
]
type PathVerificationEvidenceClass = Literal[
    "deterministic-executable",
    "advisory-command",
    "live-provider-canary",
    "browser-evidence",
    "accessibility-evidence",
    "manual-evidence",
]
type PathVerificationFreshness = Literal[
    "fresh",
    "stale",
    "missing",
    "degraded",
    "unknown",
]
type PathVerificationProvenanceSource = Literal[
    "repository-intelligence-snapshot",
    "workspace-topology",
    "eval-impact",
    "eval-coverage",
    "eval-profile",
    "eval-case",
    "eval-recipe",
    "command-evidence",
    "confirmed-memory",
    "changeset-inventory",
    "release-gate",
    "fallback-policy",
]
type PathVerificationTargetKind = Literal[
    "test-target",
    "eval-case",
    "eval-profile",
    "command-recipe",
    "release-gate",
    "lint",
    "format",
    "typecheck",
    "live-provider-canary",
    "browser-evidence",
    "accessibility-evidence",
    "manual-evidence",
]
type PathVerificationSkippedReason = Literal[
    "fallback-confidence",
    "live-provider-canary",
    "advisory-only",
    "stale-intelligence",
    "missing-intelligence",
    "operator-selection-required",
]
type PathVerificationStaleEvidenceKind = Literal[
    "verification",
    "repository-intelligence",
    "topology",
    "command-recipe",
    "workspace-memory",
    "eval-metadata",
    "release-surface",
]

_CONFIDENCE_PRIORITY: dict[EvalRecommendationConfidence, int] = {
    "direct": 5,
    "owner-derived": 4,
    "capability-derived": 3,
    "stage-derived": 2,
    "fallback": 1,
}
_DAILY_RELEASE_STAGES: tuple[EvalVerificationStage, ...] = (
    "commit-time",
    "push-time",
    "release-candidate",
    "advisory",
)
type LongRunVerificationSurface = Literal[
    "immediate",
    "checkpoint",
    "pre-resume",
    "pre-merge",
    "release-candidate",
]


_LONG_RUN_SURFACES: tuple[LongRunVerificationSurface, ...] = (
    "immediate",
    "checkpoint",
    "pre-resume",
    "pre-merge",
    "release-candidate",
)


class EvalRecommendationReason(BaseModel):
    """One explanation for why a case or profile was recommended."""

    model_config = ConfigDict(extra="forbid")

    confidence: EvalRecommendationConfidence
    group: EvalRecommendationReasonGroupKind
    summary: str
    matched_path: str | None = None
    rule_id: str | None = None
    owner: str | None = None
    capability_id: str | None = None
    verification_stage: str | None = None


class EvalRecommendationReasonGroup(BaseModel):
    """Grouped explanation rows for recommendation output."""

    model_config = ConfigDict(extra="forbid")

    group: EvalRecommendationReasonGroupKind
    title: str
    summaries: list[str] = Field(default_factory=list)
    matched_paths: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    recommended_case_ids: list[str] = Field(default_factory=list)
    recommended_profile_ids: list[str] = Field(default_factory=list)
    release_gate_commands: list[str] = Field(default_factory=list)


class EvalCaseRecommendation(BaseModel):
    """Recommended replay/eval case for one change set."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    confidence: EvalRecommendationConfidence
    owner: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    verification_stages: list[str] = Field(default_factory=list)
    reasons: list[EvalRecommendationReason] = Field(default_factory=list)


class EvalProfileRecommendation(BaseModel):
    """Recommended eval profile for one change set."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    title: str
    confidence: EvalRecommendationConfidence
    verification_stage: str
    track: EvalProfileTrack
    blocking: bool
    reasons: list[EvalRecommendationReason] = Field(default_factory=list)


class EvalVerificationRecipeRecommendation(BaseModel):
    """Recommended verification recipe for one change set."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    title: str
    confidence: EvalVerificationRecipeConfidence = "direct"
    source: EvalVerificationRecipeSource = "recipe"
    matched_paths: list[str] = Field(default_factory=list)
    component_ids: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    profile_ids: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    notes: str | None = None
    limitations: list[str] = Field(default_factory=list)


class EvalTestTargetRecommendation(BaseModel):
    """Likely test target for one changed path set."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    title: str
    confidence: EvalTestTargetConfidence
    source: EvalTestTargetSource
    freshness: PathVerificationFreshness = "unknown"
    matched_paths: list[str] = Field(default_factory=list)
    target_paths: list[str] = Field(default_factory=list)
    component_ids: list[str] = Field(default_factory=list)
    package_ids: list[str] = Field(default_factory=list)
    command: str | None = None
    reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class PathVerificationProvenance(BaseModel):
    """Source evidence for one path-to-verification claim."""

    model_config = ConfigDict(extra="forbid")

    source: PathVerificationProvenanceSource
    confidence: PathVerificationConfidence
    freshness: PathVerificationFreshness = "unknown"
    source_path: str | None = None
    source_id: str | None = None
    explanation: str
    limitations: list[str] = Field(default_factory=list)


class PathVerificationImpact(BaseModel):
    """Repository intelligence summary for one changed path."""

    model_config = ConfigDict(extra="forbid")

    path: str
    confidence: PathVerificationConfidence
    subsystems: list[str] = Field(default_factory=list)
    package_ids: list[str] = Field(default_factory=list)
    owner_hints: list[str] = Field(default_factory=list)
    release_surfaces: list[EvalVerificationStage] = Field(default_factory=list)
    generated: bool = False
    policy_sensitive: bool = False
    why_this: list[str] = Field(default_factory=list)
    provenance: list[PathVerificationProvenance] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class PathVerificationTarget(BaseModel):
    """One recommended verification target for changed paths."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    target_kind: PathVerificationTargetKind
    title: str
    evidence_class: PathVerificationEvidenceClass
    confidence: PathVerificationConfidence
    matched_paths: list[str] = Field(default_factory=list)
    command: str | None = None
    verification_stage: EvalVerificationStage | None = None
    profile_track: EvalProfileTrack | None = None
    blocking: bool = False
    why_this: str
    provenance: list[PathVerificationProvenance] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence_class(self) -> PathVerificationTarget:
        expected_class_by_kind: dict[
            PathVerificationTargetKind,
            PathVerificationEvidenceClass,
        ] = {
            "command-recipe": "advisory-command",
            "live-provider-canary": "live-provider-canary",
            "browser-evidence": "browser-evidence",
            "accessibility-evidence": "accessibility-evidence",
            "manual-evidence": "manual-evidence",
        }
        expected = expected_class_by_kind.get(self.target_kind)
        if expected is not None and self.evidence_class != expected:
            raise ValueError(f"{self.target_kind} targets must use {expected} evidence")
        if self.evidence_class == "deterministic-executable" and self.target_kind in {
            "command-recipe",
            "live-provider-canary",
            "browser-evidence",
            "accessibility-evidence",
            "manual-evidence",
        }:
            raise ValueError(
                f"{self.target_kind} is advisory and cannot be deterministic"
            )
        return self


class PathVerificationCommandRecipeTarget(PathVerificationTarget):
    """Advisory command recipe recommendation for changed paths."""

    target_kind: Literal["command-recipe"] = "command-recipe"
    evidence_class: Literal["advisory-command"] = "advisory-command"
    recipe_id: str
    purpose: str
    risk: str
    review_relevance: str | None = None
    timeout_hint_seconds: int | None = Field(default=None, gt=0)


class PathVerificationEvalCaseTarget(PathVerificationTarget):
    """Eval case recommendation in the path-to-verification contract."""

    target_kind: Literal["eval-case"] = "eval-case"
    case_id: str
    owner: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class PathVerificationEvalProfileTarget(PathVerificationTarget):
    """Eval profile recommendation in the path-to-verification contract."""

    target_kind: Literal["eval-profile"] = "eval-profile"
    profile_id: str
    profile_track: EvalProfileTrack


class PathVerificationSkippedCheck(BaseModel):
    """Recommendation that stays out of an executable plan."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    target_kind: PathVerificationTargetKind
    reason: PathVerificationSkippedReason
    explanation: str
    safe_next_actions: list[str] = Field(default_factory=list)


class PathVerificationStaleEvidence(BaseModel):
    """Stale or missing evidence that should lower recommendation confidence."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    evidence_kind: PathVerificationStaleEvidenceKind
    freshness: PathVerificationFreshness
    affected_paths: list[str] = Field(default_factory=list)
    reason: str
    provenance: list[PathVerificationProvenance] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)


class PathVerificationRecommendationReport(BaseModel):
    """Unified v15 path-to-verification recommendation contract."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    changed_paths: list[str] = Field(default_factory=list)
    impacts: list[PathVerificationImpact] = Field(default_factory=list)
    targets: list[PathVerificationTarget] = Field(default_factory=list)
    command_recipes: list[PathVerificationCommandRecipeTarget] = Field(
        default_factory=list
    )
    eval_cases: list[PathVerificationEvalCaseTarget] = Field(default_factory=list)
    eval_profiles: list[PathVerificationEvalProfileTarget] = Field(default_factory=list)
    skipped_checks: list[PathVerificationSkippedCheck] = Field(default_factory=list)
    stale_evidence: list[PathVerificationStaleEvidence] = Field(default_factory=list)
    cheapest_next_command: str | None = None
    limitations: list[str] = Field(default_factory=list)


class EvalReleaseSurfaceRecommendation(BaseModel):
    """Daily-development view of one release verification surface."""

    model_config = ConfigDict(extra="forbid")

    verification_stage: EvalVerificationStage
    impacted: bool = False
    recommended_case_ids: list[str] = Field(default_factory=list)
    recommended_profile_ids: list[str] = Field(default_factory=list)
    blocking_profile_ids: list[str] = Field(default_factory=list)
    impacted_capability_ids: list[str] = Field(default_factory=list)
    owner_ids: list[str] = Field(default_factory=list)
    profile_budget_notes: list[str] = Field(default_factory=list)
    release_gate_commands: list[str] = Field(default_factory=list)
    release_gate_notes: list[str] = Field(default_factory=list)


class EvalLongRunSurfaceRecommendation(BaseModel):
    """Long-running-task view of when recommended verification should run."""

    model_config = ConfigDict(extra="forbid")

    surface: LongRunVerificationSurface
    impacted: bool = False
    recommended_case_ids: list[str] = Field(default_factory=list)
    recommended_profile_ids: list[str] = Field(default_factory=list)
    suggested_commands: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class EvalRecommendationReport(BaseModel):
    """Structured replay/eval recommendation report for one change set."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    touched_paths: list[str] = Field(default_factory=list)
    matched_rule_ids: list[str] = Field(default_factory=list)
    unmatched_paths: list[str] = Field(default_factory=list)
    coverage_audit_recommended: bool = False
    warnings: list[str] = Field(default_factory=list)
    release_surfaces: list[EvalReleaseSurfaceRecommendation] = Field(
        default_factory=list
    )
    long_run_surfaces: list[EvalLongRunSurfaceRecommendation] = Field(
        default_factory=list
    )
    cases: list[EvalCaseRecommendation] = Field(default_factory=list)
    profiles: list[EvalProfileRecommendation] = Field(default_factory=list)
    recipes: list[EvalVerificationRecipeRecommendation] = Field(default_factory=list)
    test_targets: list[EvalTestTargetRecommendation] = Field(default_factory=list)
    suggested_commands: list[str] = Field(default_factory=list)
    cheapest_next_command: str | None = None
    fallback_policy_commands: list[str] = Field(default_factory=list)
    reason_groups: list[EvalRecommendationReasonGroup] = Field(default_factory=list)
