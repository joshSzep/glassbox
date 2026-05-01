"""Decision-support derivation for bounded branch searches."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ArtifactId
from glassbox.core import BranchCandidateId
from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchCandidateStatus
from glassbox.core import BranchCandidateVerificationStatus
from glassbox.core import BranchSearchId
from glassbox.core import BranchSearchRecord
from glassbox.core import SessionId
from glassbox.core import TaskVerificationId
from glassbox.runtime.eval_recommendation_engine import recommend_eval_change_impact

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


def derive_branch_search_decision_support(
    *,
    search: BranchSearchRecord,
    candidates: list[BranchCandidateRecord],
    workspace_root: Path | None = None,
    changed_files_by_candidate: dict[BranchCandidateId, list[str]] | None = None,
) -> BranchSearchDecisionSupport:
    """Derive comparison posture without mutating parent history."""

    changed_files_by_candidate = changed_files_by_candidate or {}
    return BranchSearchDecisionSupport(
        search_id=search.search_id,
        objective=search.objective,
        selected_candidate_id=search.selected_candidate_id,
        non_goal=(
            "Branch search records candidate evidence and operator decisions; "
            "it does not automatically merge or mutate parent history."
        ),
        candidates=[
            _candidate_decision_support(
                search=search,
                candidate=candidate,
                workspace_root=workspace_root,
                changed_files=changed_files_by_candidate.get(
                    candidate.candidate_id,
                    [],
                ),
            )
            for candidate in candidates
        ],
    )


def _candidate_decision_support(
    *,
    search: BranchSearchRecord,
    candidate: BranchCandidateRecord,
    workspace_root: Path | None,
    changed_files: list[str],
) -> BranchCandidateDecisionSupport:
    verification_posture = _verification_posture(candidate.verification_status)
    risk_posture = _risk_posture(candidate)
    return BranchCandidateDecisionSupport(
        search_id=candidate.search_id,
        candidate_id=candidate.candidate_id,
        objective=search.objective,
        strategy_label=candidate.strategy_label,
        status=candidate.status,
        selection_state=candidate.selection_state,
        candidate_session_id=candidate.candidate_session_id,
        changed_files=changed_files,
        changed_files_summary=_changed_files_summary(changed_files),
        evidence=_candidate_evidence(candidate),
        verification_posture=verification_posture,
        cost_estimate=_cost_estimate(candidate),
        risk_posture=risk_posture,
        accepted_risks=_accepted_risks(candidate),
        verification_recommendations=_verification_recommendations(
            search=search,
            candidate=candidate,
            changed_files=changed_files,
            workspace_root=workspace_root,
        ),
        recommended_follow_up_action=_recommended_follow_up_action(
            candidate,
            verification_posture=verification_posture,
            risk_posture=risk_posture,
            has_changed_files=bool(changed_files),
        ),
    )


def _changed_files_summary(changed_files: list[str]) -> str:
    if changed_files:
        return ", ".join(changed_files)
    return (
        "Changed-file evidence is not captured in current branch-search "
        "projections; inspect the candidate session before merging work."
    )


def _verification_recommendations(
    *,
    search: BranchSearchRecord,
    candidate: BranchCandidateRecord,
    changed_files: list[str],
    workspace_root: Path | None,
) -> list[BranchCandidateVerificationRecommendation]:
    if changed_files and workspace_root is not None:
        report = recommend_eval_change_impact(
            workspace_root,
            touched_paths=changed_files,
        )
        commands = _dedupe(
            [
                *(
                    [report.cheapest_next_command]
                    if report.cheapest_next_command
                    else []
                ),
                *[command for recipe in report.recipes for command in recipe.commands],
                *report.suggested_commands,
            ]
        )
        return [
            BranchCandidateVerificationRecommendation(
                source="changed-files",
                rationale=(
                    "Candidate changed files matched repository verification "
                    "recommendations."
                ),
                commands=commands,
                recipe_ids=[recipe.recipe_id for recipe in report.recipes],
                case_ids=[case.case_id for case in report.cases],
                profile_ids=[profile.profile_id for profile in report.profiles],
                warnings=report.warnings,
            )
        ]
    if candidate.verification_status == BranchCandidateVerificationStatus.PASSED:
        return [
            BranchCandidateVerificationRecommendation(
                source="existing-evidence",
                rationale=(
                    "Candidate already has passed verification evidence; inspect "
                    "the retained summary before selection."
                ),
            )
        ]
    return [
        BranchCandidateVerificationRecommendation(
            source="missing-changed-files",
            rationale=(
                f"Branch search {search.search_id} does not retain changed-file "
                "evidence for this candidate yet; inspect the candidate session "
                "and run focused verification before selecting it."
            ),
        )
    ]


def _dedupe(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


def _candidate_evidence(
    candidate: BranchCandidateRecord,
) -> list[BranchDecisionEvidence]:
    evidence: list[BranchDecisionEvidence] = []
    if candidate.candidate_session_id is not None:
        evidence.append(
            BranchDecisionEvidence(
                kind="session",
                summary="Candidate session is retained for inspection.",
                session_id=candidate.candidate_session_id,
            )
        )
    if candidate.verification_summary:
        evidence.append(
            BranchDecisionEvidence(
                kind="verification",
                summary=candidate.verification_summary,
                verification_id=candidate.verification_id,
            )
        )
    if candidate.artifact_id is not None:
        evidence.append(
            BranchDecisionEvidence(
                kind="artifact",
                summary="Candidate has retained comparison or verification artifact.",
                artifact_id=candidate.artifact_id,
            )
        )
    if candidate.selection_state is not None:
        evidence.append(
            BranchDecisionEvidence(
                kind="selection",
                summary=(
                    f"Operator marked candidate as {candidate.selection_state.value}."
                ),
            )
        )
    return evidence


def _verification_posture(
    verification_status: BranchCandidateVerificationStatus,
) -> BranchPosture:
    if verification_status == BranchCandidateVerificationStatus.PASSED:
        return "strong"
    if verification_status in {
        BranchCandidateVerificationStatus.FAILED,
        BranchCandidateVerificationStatus.TIMED_OUT,
    }:
        return "risky"
    if verification_status == BranchCandidateVerificationStatus.BLOCKED:
        return "blocked"
    if verification_status == BranchCandidateVerificationStatus.INCONCLUSIVE:
        return "review"
    return "unknown"


def _risk_posture(candidate: BranchCandidateRecord) -> BranchPosture:
    if candidate.selection_state == BranchCandidateStatus.REJECTED:
        return "blocked"
    if candidate.selection_state == BranchCandidateStatus.NEEDS_REVIEW:
        return "review"
    if candidate.verification_status == BranchCandidateVerificationStatus.PASSED:
        return "strong"
    if candidate.verification_status in {
        BranchCandidateVerificationStatus.FAILED,
        BranchCandidateVerificationStatus.TIMED_OUT,
    }:
        return "risky"
    if candidate.verification_status == BranchCandidateVerificationStatus.BLOCKED:
        return "blocked"
    return "unknown"


def _cost_estimate(candidate: BranchCandidateRecord) -> BranchCostEstimate:
    if candidate.candidate_session_id is None:
        return "unknown"
    if candidate.verification_status == BranchCandidateVerificationStatus.NOT_RUN:
        return "medium"
    return "low"


def _accepted_risks(candidate: BranchCandidateRecord) -> list[str]:
    risks: list[str] = []
    if candidate.verification_status == BranchCandidateVerificationStatus.NOT_RUN:
        risks.append("candidate has no verification evidence yet")
    if candidate.verification_status == BranchCandidateVerificationStatus.INCONCLUSIVE:
        risks.append("candidate verification is inconclusive")
    if candidate.verification_status in {
        BranchCandidateVerificationStatus.FAILED,
        BranchCandidateVerificationStatus.TIMED_OUT,
    }:
        risks.append(f"candidate verification {candidate.verification_status.value}")
    if candidate.selection_state == BranchCandidateStatus.SELECTED and risks:
        return [f"selected with open risk: {risk}" for risk in risks]
    return risks


def _recommended_follow_up_action(
    candidate: BranchCandidateRecord,
    *,
    verification_posture: BranchPosture,
    risk_posture: BranchPosture,
    has_changed_files: bool,
) -> str:
    if candidate.selection_state == BranchCandidateStatus.SELECTED:
        return (
            "Inspect the selected candidate session before manually carrying "
            "work forward."
        )
    if candidate.selection_state == BranchCandidateStatus.REJECTED:
        return "No merge action recommended; keep retained evidence for audit."
    if candidate.selection_state == BranchCandidateStatus.NEEDS_REVIEW:
        return (
            "Review the candidate session and verification evidence before "
            "selecting or rejecting it."
        )
    if verification_posture == "strong" and risk_posture == "strong":
        return "Candidate is eligible for operator review and explicit selection."
    if verification_posture in {"risky", "blocked"}:
        return "Do not select yet; inspect failures and repair or reject the candidate."
    if not has_changed_files and verification_posture == "unknown":
        return (
            "Inspect the candidate session and attach changed-file evidence before "
            "choosing verification."
        )
    return "Run or attach verification evidence before comparing this candidate."


__all__ = [
    "BranchCandidateDecisionSupport",
    "BranchCandidateVerificationRecommendation",
    "BranchCostEstimate",
    "BranchDecisionEvidence",
    "BranchEvidenceKind",
    "BranchPosture",
    "BranchSearchDecisionSupport",
    "BranchVerificationRecommendationSource",
    "derive_branch_search_decision_support",
]
