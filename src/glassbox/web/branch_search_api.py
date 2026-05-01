"""HTTP transport models for branch-search dashboard APIs."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from glassbox.core.models import BranchCandidateRecord
from glassbox.core.models import BranchSearchRecord
from glassbox.runtime.branch_decision_support import BranchCandidateDecisionSupport
from glassbox.runtime.branch_decision_support import (
    BranchCandidateVerificationRecommendation,
)
from glassbox.runtime.branch_decision_support import BranchDecisionEvidence
from glassbox.runtime.branch_decision_support import BranchSearchDecisionSupport


class BranchSearchSummaryResponse(BaseModel):
    search_id: str
    session_id: str
    parent_session_id: str
    status: str
    objective: str
    task_id: str | None = None
    selected_candidate_id: str | None = None
    abandoned_reason: str | None = None
    candidate_count: int
    created_at: datetime
    updated_at: datetime
    last_sequence: int


class BranchCandidateResponse(BaseModel):
    search_id: str
    candidate_id: str
    parent_session_id: str
    candidate_session_id: str | None = None
    strategy_label: str
    status: str
    verification_status: str
    selection_state: str | None = None
    verification_summary: str | None = None
    verification_id: str | None = None
    artifact_id: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    patch_summary: str | None = None
    policy_budget_summary: str | None = None
    residual_risks: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_sequence: int


class BranchDecisionEvidenceResponse(BaseModel):
    kind: str
    summary: str
    session_id: str | None = None
    verification_id: str | None = None
    artifact_id: str | None = None


class BranchCandidateVerificationRecommendationResponse(BaseModel):
    source: str
    rationale: str
    commands: list[str] = Field(default_factory=list)
    recipe_ids: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    profile_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BranchCandidateDecisionSupportResponse(BaseModel):
    search_id: str
    candidate_id: str
    objective: str
    strategy_label: str
    status: str
    selection_state: str | None = None
    candidate_session_id: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    changed_files_summary: str
    evidence: list[BranchDecisionEvidenceResponse] = Field(default_factory=list)
    verification_posture: str
    cost_estimate: str
    risk_posture: str
    accepted_risks: list[str] = Field(default_factory=list)
    verification_recommendations: list[
        BranchCandidateVerificationRecommendationResponse
    ] = Field(default_factory=list)
    recommended_follow_up_action: str


class BranchSearchDecisionSupportResponse(BaseModel):
    search_id: str
    objective: str
    selected_candidate_id: str | None = None
    automatic_merge: bool
    non_goal: str
    candidates: list[BranchCandidateDecisionSupportResponse]


class BranchSearchListPageResponse(BaseModel):
    items: list[BranchSearchSummaryResponse]


class BranchSearchDetailResponse(BaseModel):
    search: BranchSearchSummaryResponse
    candidates: list[BranchCandidateResponse]
    decision_support: BranchSearchDecisionSupportResponse


class BranchCandidateActionRequest(BaseModel):
    actor: str = "operator"
    reason: str = Field(min_length=1, max_length=2000)


class BranchCandidateActionResponse(BaseModel):
    status: str
    candidate: BranchCandidateResponse


def build_branch_search_summary_response(
    search: BranchSearchRecord,
) -> BranchSearchSummaryResponse:
    return BranchSearchSummaryResponse(
        search_id=str(search.search_id),
        session_id=str(search.session_id),
        parent_session_id=str(search.parent_session_id),
        status=search.status.value,
        objective=search.objective,
        task_id=str(search.task_id) if search.task_id is not None else None,
        selected_candidate_id=(
            str(search.selected_candidate_id)
            if search.selected_candidate_id is not None
            else None
        ),
        abandoned_reason=search.abandoned_reason,
        candidate_count=search.candidate_count,
        created_at=search.created_at,
        updated_at=search.updated_at,
        last_sequence=search.last_sequence,
    )


def build_branch_search_summary_responses(
    searches: Sequence[BranchSearchRecord],
) -> list[BranchSearchSummaryResponse]:
    return [build_branch_search_summary_response(search) for search in searches]


def build_branch_candidate_response(
    candidate: BranchCandidateRecord,
) -> BranchCandidateResponse:
    return BranchCandidateResponse(
        search_id=str(candidate.search_id),
        candidate_id=str(candidate.candidate_id),
        parent_session_id=str(candidate.parent_session_id),
        candidate_session_id=(
            str(candidate.candidate_session_id)
            if candidate.candidate_session_id is not None
            else None
        ),
        strategy_label=candidate.strategy_label,
        status=candidate.status.value,
        verification_status=candidate.verification_status.value,
        selection_state=(
            candidate.selection_state.value
            if candidate.selection_state is not None
            else None
        ),
        verification_summary=candidate.verification_summary,
        verification_id=(
            str(candidate.verification_id)
            if candidate.verification_id is not None
            else None
        ),
        artifact_id=str(candidate.artifact_id)
        if candidate.artifact_id is not None
        else None,
        changed_files=[],
        patch_summary=None,
        policy_budget_summary=(
            "No candidate-specific policy or budget evidence is retained."
        ),
        residual_risks=_candidate_residual_risks(candidate),
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        last_sequence=candidate.last_sequence,
    )


def build_branch_candidate_responses(
    candidates: Sequence[BranchCandidateRecord],
) -> list[BranchCandidateResponse]:
    return [build_branch_candidate_response(candidate) for candidate in candidates]


def build_branch_search_decision_support_response(
    support: BranchSearchDecisionSupport,
) -> BranchSearchDecisionSupportResponse:
    return BranchSearchDecisionSupportResponse(
        search_id=str(support.search_id),
        objective=support.objective,
        selected_candidate_id=(
            str(support.selected_candidate_id)
            if support.selected_candidate_id is not None
            else None
        ),
        automatic_merge=support.automatic_merge,
        non_goal=support.non_goal,
        candidates=[
            build_branch_candidate_decision_support_response(candidate)
            for candidate in support.candidates
        ],
    )


def build_branch_candidate_decision_support_response(
    candidate: BranchCandidateDecisionSupport,
) -> BranchCandidateDecisionSupportResponse:
    return BranchCandidateDecisionSupportResponse(
        search_id=str(candidate.search_id),
        candidate_id=str(candidate.candidate_id),
        objective=candidate.objective,
        strategy_label=candidate.strategy_label,
        status=candidate.status.value,
        selection_state=(
            candidate.selection_state.value
            if candidate.selection_state is not None
            else None
        ),
        candidate_session_id=(
            str(candidate.candidate_session_id)
            if candidate.candidate_session_id is not None
            else None
        ),
        changed_files=candidate.changed_files,
        changed_files_summary=candidate.changed_files_summary,
        evidence=[
            build_branch_decision_evidence_response(item) for item in candidate.evidence
        ],
        verification_posture=candidate.verification_posture,
        cost_estimate=candidate.cost_estimate,
        risk_posture=candidate.risk_posture,
        accepted_risks=candidate.accepted_risks,
        verification_recommendations=[
            build_branch_candidate_verification_recommendation_response(item)
            for item in candidate.verification_recommendations
        ],
        recommended_follow_up_action=candidate.recommended_follow_up_action,
    )


def build_branch_candidate_verification_recommendation_response(
    recommendation: BranchCandidateVerificationRecommendation,
) -> BranchCandidateVerificationRecommendationResponse:
    return BranchCandidateVerificationRecommendationResponse(
        source=recommendation.source,
        rationale=recommendation.rationale,
        commands=recommendation.commands,
        recipe_ids=recommendation.recipe_ids,
        case_ids=recommendation.case_ids,
        profile_ids=recommendation.profile_ids,
        warnings=recommendation.warnings,
    )


def build_branch_decision_evidence_response(
    evidence: BranchDecisionEvidence,
) -> BranchDecisionEvidenceResponse:
    return BranchDecisionEvidenceResponse(
        kind=evidence.kind,
        summary=evidence.summary,
        session_id=str(evidence.session_id)
        if evidence.session_id is not None
        else None,
        verification_id=str(evidence.verification_id)
        if evidence.verification_id is not None
        else None,
        artifact_id=str(evidence.artifact_id)
        if evidence.artifact_id is not None
        else None,
    )


def _candidate_residual_risks(candidate: BranchCandidateRecord) -> list[str]:
    if candidate.verification_status.value == "passed":
        return ["Selection is metadata only; review candidate session before merging."]
    if candidate.verification_status.value == "not_run":
        return ["Verification has not run for this candidate."]
    return [f"Verification ended {candidate.verification_status.value}."]
