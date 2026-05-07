"""Changeset CLI JSON payload builders."""

from glassbox.core import ReviewFeedbackRecord
from glassbox.runtime.branch_candidate_adoption import BranchCandidateAdoptionResult
from glassbox.runtime.changesets import ChangesetReviewBriefGenerationResult
from glassbox.runtime.changesets import ReviewFeedbackFixupInventoryResult
from glassbox.runtime.changesets import ReviewFeedbackRecordResult
from glassbox.runtime.precommit_evidence import PreCommitEvidenceRecordResult
from glassbox.runtime.review_responses import ReviewFeedbackResponseStatus


def _review_brief_payload(
    result: ChangesetReviewBriefGenerationResult,
) -> dict[str, object]:
    return {
        "changeset_id": str(result.changeset_id),
        "session_id": str(result.session_id),
        "artifact_id": str(result.artifact.artifact_id),
        "artifact_path": result.artifact.relative_path.as_posix(),
        "brief": result.brief.model_dump(mode="json"),
        "markdown": result.markdown,
        "event": result.event.model_dump(mode="json"),
        "readiness_event": result.readiness_event.model_dump(mode="json"),
        "limitations": result.limitations,
        "limitation_summary": (
            result.limitation_summary.model_dump(mode="json")
            if result.limitation_summary is not None
            else None
        ),
    }


def _precommit_evidence_payload(
    result: PreCommitEvidenceRecordResult,
) -> dict[str, object]:
    return {
        "changeset_id": str(result.changeset_id),
        "session_id": str(result.session_id),
        "artifact_id": str(result.artifact.artifact_id),
        "artifact_path": result.artifact.relative_path.as_posix(),
        "evidence": result.evidence.model_dump(mode="json"),
        "verification_event": result.verification_event.model_dump(mode="json"),
        "readiness_event": result.readiness_event.model_dump(mode="json"),
        "commit_readiness": result.commit_readiness.model_dump(mode="json"),
    }


def _feedback_payload(
    feedback: ReviewFeedbackRecord,
    *,
    scopes,
    response_status: ReviewFeedbackResponseStatus | None = None,
) -> dict[str, object]:
    return {
        "feedback": feedback.model_dump(mode="json"),
        "scopes": [scope.model_dump(mode="json") for scope in scopes],
        "response_status": (
            response_status.model_dump(mode="json")
            if response_status is not None
            else None
        ),
        "non_claims": [
            "review feedback is local evidence, not approval",
            "Glassbox did not stage, commit, push, open a PR, or merge",
        ],
    }


def _feedback_result_payload(result: ReviewFeedbackRecordResult) -> dict[str, object]:
    return {
        **_feedback_payload(result.feedback, scopes=result.scopes),
        "events": [event.model_dump(mode="json") for event in result.events],
        "safe_next_actions": result.safe_next_actions,
        "non_claims": result.non_claims,
    }


def _fixup_inventory_payload(
    result: ReviewFeedbackFixupInventoryResult,
    *,
    response_status: ReviewFeedbackResponseStatus,
) -> dict[str, object]:
    return {
        "feedback_id": str(result.feedback_id),
        "changeset_id": str(result.changeset_id),
        "session_id": str(result.session_id),
        "artifact_id": str(result.artifact.artifact_id),
        "artifact_path": result.artifact.relative_path.as_posix(),
        "inventory": result.inventory.model_dump(mode="json"),
        "event": result.event.model_dump(mode="json"),
        "status": result.status.model_dump(mode="json"),
        "response_status": response_status.model_dump(mode="json"),
        "safe_next_actions": response_status.safe_next_actions,
        "non_claims": result.inventory.non_claims,
    }


def _adoption_result_payload(
    result: BranchCandidateAdoptionResult,
) -> dict[str, object]:
    return {
        "preview": result.preview.model_dump(mode="json"),
        "changeset": result.changeset.model_dump(mode="json"),
        "safe_copy": (
            "Glassbox recorded candidate adoption evidence only; it did not "
            "merge, commit, push, or open a PR."
        ),
    }
