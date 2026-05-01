"""Typed models for branch-search decision support."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ArtifactId
from glassbox.core import BranchCandidateId
from glassbox.core import BranchCandidateStatus
from glassbox.core import BranchSearchId
from glassbox.core import SessionId
from glassbox.core import TaskVerificationId

BranchEvidenceKind = Literal["session", "verification", "artifact", "selection"]
BranchPosture = Literal["strong", "review", "risky", "blocked", "unknown"]
BranchCostEstimate = Literal["low", "medium", "unknown"]
BranchVerificationRecommendationSource = Literal[
    "changed-files",
    "existing-evidence",
    "missing-changed-files",
]


class BranchDecisionEvidence(BaseModel):
    """One retained evidence pointer for a branch-search candidate."""

    model_config = ConfigDict(extra="forbid")

    kind: BranchEvidenceKind
    summary: str = Field(min_length=1, max_length=4000)
    session_id: SessionId | None = None
    verification_id: TaskVerificationId | None = None
    artifact_id: ArtifactId | None = None


class BranchCandidateVerificationRecommendation(BaseModel):
    """One candidate-level verification recommendation."""

    model_config = ConfigDict(extra="forbid")

    source: BranchVerificationRecommendationSource
    rationale: str = Field(min_length=1, max_length=1000)
    commands: list[str] = Field(default_factory=list)
    recipe_ids: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    profile_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BranchCandidateDecisionSupport(BaseModel):
    """Operator-facing decision-support target for one candidate."""

    model_config = ConfigDict(extra="forbid")

    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    objective: str = Field(min_length=1, max_length=4000)
    strategy_label: str = Field(min_length=1, max_length=200)
    status: BranchCandidateStatus
    selection_state: BranchCandidateStatus | None = None
    candidate_session_id: SessionId | None = None
    changed_files: list[str] = Field(default_factory=list, max_length=500)
    changed_files_summary: str = Field(min_length=1, max_length=1000)
    evidence: list[BranchDecisionEvidence] = Field(default_factory=list)
    verification_posture: BranchPosture
    cost_estimate: BranchCostEstimate
    risk_posture: BranchPosture
    accepted_risks: list[str] = Field(default_factory=list, max_length=20)
    verification_recommendations: list[BranchCandidateVerificationRecommendation] = (
        Field(default_factory=list)
    )
    recommended_follow_up_action: str = Field(min_length=1, max_length=1000)


class BranchSearchDecisionSupport(BaseModel):
    """Decision-support target for comparing bounded branch-search candidates."""

    model_config = ConfigDict(extra="forbid")

    search_id: BranchSearchId
    objective: str = Field(min_length=1, max_length=4000)
    selected_candidate_id: BranchCandidateId | None = None
    automatic_merge: Literal[False] = False
    non_goal: str = Field(min_length=1, max_length=1000)
    candidates: list[BranchCandidateDecisionSupport]


__all__ = [
    "BranchCandidateDecisionSupport",
    "BranchCandidateVerificationRecommendation",
    "BranchCostEstimate",
    "BranchDecisionEvidence",
    "BranchEvidenceKind",
    "BranchPosture",
    "BranchSearchDecisionSupport",
    "BranchVerificationRecommendationSource",
]
