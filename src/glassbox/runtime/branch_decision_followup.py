"""Follow-up action guidance for branch-search candidates."""

from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchCandidateStatus
from glassbox.runtime.branch_decision_models import BranchPosture


def recommended_follow_up_action(
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


__all__ = ["recommended_follow_up_action"]
