"""Retained evidence extraction for branch-search candidates."""

from glassbox.core import BranchCandidateRecord
from glassbox.runtime.branch_decision_models import BranchDecisionEvidence


def candidate_evidence(
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


__all__ = ["candidate_evidence"]
