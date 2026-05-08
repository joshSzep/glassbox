"""Review-loop response builders for changeset APIs."""

from collections.abc import Sequence

from glassbox.core.models import ManualEvidenceRecord
from glassbox.core.models import ReviewFeedbackRecord
from glassbox.core.models import ReviewFeedbackScopeRecord
from glassbox.runtime.changesets import ManualEvidenceRecordResult
from glassbox.runtime.changesets import ReviewFeedbackFixupInventoryResult
from glassbox.runtime.changesets import ReviewFeedbackRecordResult
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFeedbackResponseStatus
from glassbox.web.review_loop_api import ChangesetReviewResponseSummaryResponse
from glassbox.web.review_loop_api import ManualEvidenceActionResponse
from glassbox.web.review_loop_api import ManualEvidenceResponse
from glassbox.web.review_loop_api import ReviewFeedbackActionResponse
from glassbox.web.review_loop_api import ReviewFeedbackDetailResponse
from glassbox.web.review_loop_api import ReviewFeedbackFixupInventoryActionResponse
from glassbox.web.review_loop_api import ReviewFeedbackFixupInventoryStatusResponse
from glassbox.web.review_loop_api import ReviewFeedbackResponse
from glassbox.web.review_loop_api import ReviewFeedbackResponseStatusResponse
from glassbox.web.review_loop_api import ReviewFeedbackScopeResponse


def build_review_feedback_response(
    feedback: ReviewFeedbackRecord,
) -> ReviewFeedbackResponse:
    return ReviewFeedbackResponse(
        session_id=str(feedback.session_id),
        feedback_id=str(feedback.feedback_id),
        changeset_id=str(feedback.changeset_id),
        feedback_kind=feedback.feedback_kind.value,
        provenance=feedback.provenance.value,
        disposition=feedback.disposition.value,
        summary=feedback.summary,
        body=feedback.body,
        source_label=feedback.source_label,
        reviewer_label=feedback.reviewer_label,
        created_by=feedback.created_by,
        updated_by=feedback.updated_by,
        resolved_by=feedback.resolved_by,
        archived_by=feedback.archived_by,
        accepted_by=feedback.accepted_by,
        source_session_id=_optional_str(feedback.source_session_id),
        task_id=_optional_str(feedback.task_id),
        turn_id=_optional_str(feedback.turn_id),
        artifact_id=_optional_str(feedback.artifact_id),
        verification_id=_optional_str(feedback.verification_id),
        resolution_summary=feedback.resolution_summary,
        residual_risk=feedback.residual_risk,
        risk_summary=feedback.risk_summary,
        acceptance_reason=feedback.acceptance_reason,
        archived_reason=feedback.archived_reason,
        replacement_feedback_id=_optional_str(feedback.replacement_feedback_id),
        reopened_count=feedback.reopened_count,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
        last_sequence=feedback.last_sequence,
    )


def build_manual_evidence_response(
    evidence: ManualEvidenceRecord,
) -> ManualEvidenceResponse:
    return ManualEvidenceResponse(
        session_id=str(evidence.session_id),
        evidence_id=str(evidence.evidence_id),
        evidence_kind=evidence.evidence_kind.value,
        state=evidence.state.value,
        target_kind=evidence.target_kind.value,
        target_id=evidence.target_id,
        changeset_id=_optional_str(evidence.changeset_id),
        feedback_id=_optional_str(evidence.feedback_id),
        artifact_id=_optional_str(evidence.artifact_id),
        artifact_schema_version=evidence.artifact_schema_version,
        summary=evidence.summary,
        source_label=evidence.source_label,
        observed_at=evidence.observed_at,
        created_by=evidence.created_by,
        local_only=evidence.local_only,
        redaction_status=evidence.redaction_status.value,
        freshness=evidence.freshness.value,
        limitations=evidence.limitations,
        non_claims=evidence.non_claims,
        rejected_reason=evidence.rejected_reason,
        archived_reason=evidence.archived_reason,
        superseded_reason=evidence.superseded_reason,
        replacement_evidence_id=_optional_str(evidence.replacement_evidence_id),
        task_id=_optional_str(evidence.task_id),
        turn_id=_optional_str(evidence.turn_id),
        verification_id=_optional_str(evidence.verification_id),
        created_at=evidence.created_at,
        updated_at=evidence.updated_at,
        last_sequence=evidence.last_sequence,
    )


def build_manual_evidence_action_response(
    result: ManualEvidenceRecordResult,
) -> ManualEvidenceActionResponse:
    return ManualEvidenceActionResponse(
        evidence=build_manual_evidence_response(result.evidence),
        artifact_id=(
            str(result.artifact.artifact_id) if result.artifact is not None else None
        ),
        artifact_path=(
            result.artifact.relative_path.as_posix()
            if result.artifact is not None
            else None
        ),
        event_sequence=result.event.sequence,
        safe_next_actions=result.safe_next_actions,
        non_claims=result.non_claims,
    )


def build_review_feedback_scope_response(
    scope: ReviewFeedbackScopeRecord,
) -> ReviewFeedbackScopeResponse:
    return ReviewFeedbackScopeResponse(
        session_id=str(scope.session_id),
        feedback_id=str(scope.feedback_id),
        changeset_id=str(scope.changeset_id),
        scope_kind=scope.scope_kind.value,
        reason=scope.reason,
        source_session_id=_optional_str(scope.source_session_id),
        task_id=_optional_str(scope.task_id),
        turn_id=_optional_str(scope.turn_id),
        artifact_id=_optional_str(scope.artifact_id),
        verification_id=_optional_str(scope.verification_id),
        branch_search_id=_optional_str(scope.branch_search_id),
        branch_candidate_id=_optional_str(scope.branch_candidate_id),
        file_path=scope.file_path,
        line_start=scope.line_start,
        line_end=scope.line_end,
        created_at=scope.created_at,
        last_sequence=scope.last_sequence,
    )


def build_review_feedback_response_status_response(
    status: ReviewFeedbackResponseStatus,
) -> ReviewFeedbackResponseStatusResponse:
    return ReviewFeedbackResponseStatusResponse(
        feedback_id=str(status.feedback_id),
        changeset_id=str(status.changeset_id),
        response_state=status.response_state.value,
        disposition=status.disposition.value,
        summary=status.summary,
        fixup_inventory_count=status.fixup_inventory_count,
        latest_fixup_inventory_artifact_id=_optional_str(
            status.latest_fixup_inventory_artifact_id
        ),
        latest_fixup_inventory_sequence=status.latest_fixup_inventory_sequence,
        latest_fixup_inventory_at=status.latest_fixup_inventory_at,
        latest_source_kind=(
            status.latest_source_kind.value
            if status.latest_source_kind is not None
            else None
        ),
        latest_source_summary=status.latest_source_summary,
        inventory_freshness=status.inventory_freshness.value,
        stale=status.stale,
        stale_reason=status.stale_reason,
        changed_path_count=status.changed_path_count,
        matched_scope_path_count=status.matched_scope_path_count,
        path_summaries=status.path_summaries,
        verification_state=status.verification_state.value,
        verification_reason=status.verification_reason,
        verification_requirement_ids=status.verification_requirement_ids,
        verification_safe_next_actions=status.verification_safe_next_actions,
        blockers=status.blockers,
        safe_next_actions=status.safe_next_actions,
        non_claims=status.non_claims,
    )


def build_review_response_summary_response(
    summary: ChangesetReviewResponseSummary,
) -> ChangesetReviewResponseSummaryResponse:
    return ChangesetReviewResponseSummaryResponse(
        changeset_id=str(summary.changeset_id),
        total_feedback_count=summary.total_feedback_count,
        open_count=summary.open_count,
        responded_count=summary.responded_count,
        unresolved_count=summary.unresolved_count,
        stale_response_count=summary.stale_response_count,
        accepted_risk_count=summary.accepted_risk_count,
        blocked_count=summary.blocked_count,
        items=[
            build_review_feedback_response_status_response(item)
            for item in summary.items
        ],
        blockers=summary.blockers,
        safe_next_actions=summary.safe_next_actions,
        non_claims=summary.non_claims,
    )


def build_review_feedback_detail_response(
    feedback: ReviewFeedbackRecord,
    scopes: Sequence[ReviewFeedbackScopeRecord],
    response_status: ReviewFeedbackResponseStatus,
) -> ReviewFeedbackDetailResponse:
    return ReviewFeedbackDetailResponse(
        feedback=build_review_feedback_response(feedback),
        scopes=[build_review_feedback_scope_response(scope) for scope in scopes],
        response_status=build_review_feedback_response_status_response(response_status),
        safe_next_actions=[
            f"glassbox changeset feedback show {feedback.feedback_id} --cwd .",
            f"glassbox changeset show {feedback.changeset_id} --cwd .",
        ],
        non_claims=_review_feedback_non_claims(),
    )


def build_review_feedback_action_response(
    result: ReviewFeedbackRecordResult,
) -> ReviewFeedbackActionResponse:
    return ReviewFeedbackActionResponse(
        feedback=build_review_feedback_response(result.feedback),
        scopes=[build_review_feedback_scope_response(scope) for scope in result.scopes],
        event_sequences=[event.sequence for event in result.events],
        safe_next_actions=result.safe_next_actions,
        non_claims=result.non_claims,
    )


def build_review_feedback_fixup_inventory_action_response(
    result: ReviewFeedbackFixupInventoryResult,
    *,
    response_status: ReviewFeedbackResponseStatus,
) -> ReviewFeedbackFixupInventoryActionResponse:
    return ReviewFeedbackFixupInventoryActionResponse(
        feedback_id=str(result.feedback_id),
        changeset_id=str(result.changeset_id),
        session_id=str(result.session_id),
        artifact_id=str(result.artifact.artifact_id),
        artifact_path=result.artifact.relative_path.as_posix(),
        event_sequence=result.event.sequence,
        changed_path_count=result.inventory.changed_path_count,
        matched_scope_path_count=result.inventory.matched_scope_path_count,
        inventory_freshness=result.inventory.inventory_freshness.value,
        path_summaries=[
            (
                f"{path.path}: {path.change_kind}; "
                f"matches feedback scope {str(path.matches_feedback_scope).lower()}"
            )
            for path in result.inventory.paths[:20]
        ],
        status=ReviewFeedbackFixupInventoryStatusResponse(
            freshness=result.status.freshness.value,
            stale=result.status.stale,
            reason=result.status.reason,
            recorded_source_digest=result.status.recorded_source_digest,
            current_source_digest=result.status.current_source_digest,
            safe_next_actions=result.status.safe_next_actions,
        ),
        response_status=build_review_feedback_response_status_response(response_status),
        safe_next_actions=response_status.safe_next_actions,
        non_claims=result.inventory.non_claims,
    )


def _optional_str(value: object | None) -> str | None:
    return str(value) if value is not None else None


def _review_feedback_non_claims() -> list[str]:
    return [
        "review feedback is local evidence, not approval",
        "Glassbox did not stage, commit, push, open a PR, or merge",
    ]


__all__ = (
    "build_review_feedback_response",
    "build_manual_evidence_response",
    "build_manual_evidence_action_response",
    "build_review_feedback_scope_response",
    "build_review_feedback_response_status_response",
    "build_review_response_summary_response",
    "build_review_feedback_detail_response",
    "build_review_feedback_action_response",
    "build_review_feedback_fixup_inventory_action_response",
    "_optional_str",
    "_review_feedback_non_claims",
)
