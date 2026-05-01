"""Structured models for replay/eval change-impact recommendations."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.evals import EvalProfileTrack
from glassbox.runtime.evals import EvalVerificationStage

type EvalRecommendationConfidence = Literal[
    "direct",
    "owner-derived",
    "capability-derived",
    "stage-derived",
    "fallback",
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
    summary: str
    matched_path: str | None = None
    rule_id: str | None = None
    owner: str | None = None
    capability_id: str | None = None
    verification_stage: str | None = None


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
    suggested_commands: list[str] = Field(default_factory=list)
