"""Decision-support derivation for bounded branch searches."""

from pathlib import Path

from glassbox.core import BranchCandidateId
from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchSearchRecord
from glassbox.runtime.branch_decision_cost import cost_estimate
from glassbox.runtime.branch_decision_evidence import candidate_evidence
from glassbox.runtime.branch_decision_files import changed_files_summary
from glassbox.runtime.branch_decision_followup import recommended_follow_up_action
from glassbox.runtime.branch_decision_models import BranchCandidateDecisionSupport
from glassbox.runtime.branch_decision_models import (
    BranchCandidateVerificationRecommendation,
)
from glassbox.runtime.branch_decision_models import BranchCostEstimate
from glassbox.runtime.branch_decision_models import BranchDecisionEvidence
from glassbox.runtime.branch_decision_models import BranchEvidenceKind
from glassbox.runtime.branch_decision_models import BranchPosture
from glassbox.runtime.branch_decision_models import BranchSearchDecisionSupport
from glassbox.runtime.branch_decision_models import (
    BranchVerificationRecommendationSource,
)
from glassbox.runtime.branch_decision_risk import accepted_risks
from glassbox.runtime.branch_decision_risk import risk_posture
from glassbox.runtime.branch_decision_verification import verification_posture
from glassbox.runtime.branch_decision_verification import verification_recommendations


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
    verification = verification_posture(candidate.verification_status)
    risk = risk_posture(candidate)
    return BranchCandidateDecisionSupport(
        search_id=candidate.search_id,
        candidate_id=candidate.candidate_id,
        objective=search.objective,
        strategy_label=candidate.strategy_label,
        status=candidate.status,
        selection_state=candidate.selection_state,
        candidate_session_id=candidate.candidate_session_id,
        changed_files=changed_files,
        changed_files_summary=changed_files_summary(changed_files),
        evidence=candidate_evidence(candidate),
        verification_posture=verification,
        cost_estimate=cost_estimate(candidate),
        risk_posture=risk,
        accepted_risks=accepted_risks(candidate),
        verification_recommendations=verification_recommendations(
            search=search,
            candidate=candidate,
            changed_files=changed_files,
            workspace_root=workspace_root,
        ),
        recommended_follow_up_action=recommended_follow_up_action(
            candidate,
            verification_posture=verification,
            risk_posture=risk,
            has_changed_files=bool(changed_files),
        ),
    )


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
