"""Risk posture and accepted-risk labels for branch-search candidates."""

from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchCandidateStatus
from glassbox.core import BranchCandidateVerificationStatus
from glassbox.runtime.branch_decision_models import BranchPosture


def risk_posture(candidate: BranchCandidateRecord) -> BranchPosture:
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


def accepted_risks(candidate: BranchCandidateRecord) -> list[str]:
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


__all__ = [
    "accepted_risks",
    "risk_posture",
]
