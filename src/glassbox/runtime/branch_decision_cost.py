"""Cost estimates for branch-search candidate review."""

from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchCandidateVerificationStatus
from glassbox.runtime.branch_decision_models import BranchCostEstimate


def cost_estimate(candidate: BranchCandidateRecord) -> BranchCostEstimate:
    if candidate.candidate_session_id is None:
        return "unknown"
    if candidate.verification_status == BranchCandidateVerificationStatus.NOT_RUN:
        return "medium"
    return "low"


__all__ = ["cost_estimate"]
