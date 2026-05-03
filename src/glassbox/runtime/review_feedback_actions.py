"""Review-feedback mutation service."""

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetRecord
from glassbox.core import EventEnvelope
from glassbox.core import ReviewFeedbackArchived
from glassbox.core import ReviewFeedbackCreated
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackReopened
from glassbox.core import ReviewFeedbackResolved
from glassbox.core import ReviewFeedbackRiskAccepted
from glassbox.core import ReviewFeedbackScopeAttached
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.core import TaskId
from glassbox.core import TaskVerificationId
from glassbox.core import TurnId
from glassbox.core import new_review_feedback_id
from glassbox.runtime.changeset_models import ReviewFeedbackRecordResult
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_safe_commands import changeset_feedback_show_command
from glassbox.runtime.changeset_safe_commands import show_changeset_command
from glassbox.runtime.review_feedback_scopes import default_feedback_scope_reason
from glassbox.runtime.review_feedback_scopes import resolve_feedback_scope_kind


class ReviewFeedbackActionService:
    """Record local review feedback as changeset evidence."""

    def __init__(self, repository: ChangesetRepository) -> None:
        self._repository = repository

    def add_feedback(
        self,
        changeset_id: ChangesetId,
        *,
        feedback_kind: ReviewFeedbackKind,
        summary: str,
        provenance: ReviewFeedbackProvenance = ReviewFeedbackProvenance.MANUAL,
        body: str | None = None,
        source_label: str | None = None,
        reviewer_label: str | None = None,
        created_by: str = "operator",
        scope_kind: ReviewFeedbackScopeKind = ReviewFeedbackScopeKind.CHANGESET,
        scope_reason: str | None = None,
        file_path: str | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
        feedback_id: ReviewFeedbackId | None = None,
        task_id: TaskId | None = None,
        turn_id: TurnId | None = None,
        artifact_id: ArtifactId | None = None,
        verification_id: TaskVerificationId | None = None,
    ) -> ReviewFeedbackRecordResult:
        changeset = self._require_changeset(changeset_id)
        resolved_feedback_id = feedback_id or new_review_feedback_id()
        resolved_scope_kind = resolve_feedback_scope_kind(
            scope_kind,
            file_path=file_path,
        )
        events = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ReviewFeedbackCreated(
                        feedback_id=resolved_feedback_id,
                        changeset_id=changeset.changeset_id,
                        feedback_kind=feedback_kind,
                        provenance=provenance,
                        summary=summary,
                        body=body,
                        source_label=source_label,
                        reviewer_label=reviewer_label,
                        created_by=created_by,
                        task_id=task_id or changeset.task_id,
                        turn_id=turn_id,
                        artifact_id=artifact_id,
                        verification_id=verification_id,
                    ),
                ),
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ReviewFeedbackScopeAttached(
                        feedback_id=resolved_feedback_id,
                        changeset_id=changeset.changeset_id,
                        scope_kind=resolved_scope_kind,
                        reason=scope_reason
                        or default_feedback_scope_reason(resolved_scope_kind),
                        task_id=task_id or changeset.task_id,
                        turn_id=turn_id,
                        artifact_id=artifact_id,
                        verification_id=verification_id,
                        branch_search_id=changeset.branch_search_id,
                        branch_candidate_id=changeset.branch_candidate_id,
                        file_path=file_path,
                        line_start=line_start,
                        line_end=line_end,
                    ),
                ),
            ]
        )
        return self._result(changeset, resolved_feedback_id, events)

    def resolve_feedback(
        self,
        feedback_id: ReviewFeedbackId,
        *,
        resolution_summary: str,
        resolved_by: str = "operator",
        residual_risk: str | None = None,
    ) -> ReviewFeedbackRecordResult:
        feedback = self._require_feedback(feedback_id)
        events = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=feedback.session_id,
                    sequence=0,
                    payload=ReviewFeedbackResolved(
                        feedback_id=feedback.feedback_id,
                        changeset_id=feedback.changeset_id,
                        resolution_summary=resolution_summary,
                        resolved_by=resolved_by,
                        residual_risk=residual_risk,
                        task_id=feedback.task_id,
                        turn_id=feedback.turn_id,
                        artifact_id=feedback.artifact_id,
                        verification_id=feedback.verification_id,
                    ),
                )
            ]
        )
        return self._result(
            self._require_changeset(feedback.changeset_id),
            feedback_id,
            events,
        )

    def reopen_feedback(
        self,
        feedback_id: ReviewFeedbackId,
        *,
        reason: str,
        reopened_by: str = "operator",
    ) -> ReviewFeedbackRecordResult:
        feedback = self._require_feedback(feedback_id)
        events = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=feedback.session_id,
                    sequence=0,
                    payload=ReviewFeedbackReopened(
                        feedback_id=feedback.feedback_id,
                        changeset_id=feedback.changeset_id,
                        reason=reason,
                        reopened_by=reopened_by,
                        task_id=feedback.task_id,
                        turn_id=feedback.turn_id,
                        artifact_id=feedback.artifact_id,
                        verification_id=feedback.verification_id,
                    ),
                )
            ]
        )
        return self._result(
            self._require_changeset(feedback.changeset_id),
            feedback_id,
            events,
        )

    def archive_feedback(
        self,
        feedback_id: ReviewFeedbackId,
        *,
        reason: str,
        archived_by: str = "operator",
        replacement_feedback_id: ReviewFeedbackId | None = None,
    ) -> ReviewFeedbackRecordResult:
        feedback = self._require_feedback(feedback_id)
        events = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=feedback.session_id,
                    sequence=0,
                    payload=ReviewFeedbackArchived(
                        feedback_id=feedback.feedback_id,
                        changeset_id=feedback.changeset_id,
                        reason=reason,
                        archived_by=archived_by,
                        replacement_feedback_id=replacement_feedback_id,
                        task_id=feedback.task_id,
                        turn_id=feedback.turn_id,
                        artifact_id=feedback.artifact_id,
                        verification_id=feedback.verification_id,
                    ),
                )
            ]
        )
        return self._result(
            self._require_changeset(feedback.changeset_id),
            feedback_id,
            events,
        )

    def accept_risk(
        self,
        feedback_id: ReviewFeedbackId,
        *,
        risk_summary: str,
        acceptance_reason: str,
        accepted_by: str = "operator",
    ) -> ReviewFeedbackRecordResult:
        feedback = self._require_feedback(feedback_id)
        events = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=feedback.session_id,
                    sequence=0,
                    payload=ReviewFeedbackRiskAccepted(
                        feedback_id=feedback.feedback_id,
                        changeset_id=feedback.changeset_id,
                        risk_summary=risk_summary,
                        acceptance_reason=acceptance_reason,
                        accepted_by=accepted_by,
                        task_id=feedback.task_id,
                        turn_id=feedback.turn_id,
                        artifact_id=feedback.artifact_id,
                        verification_id=feedback.verification_id,
                    ),
                )
            ]
        )
        return self._result(
            self._require_changeset(feedback.changeset_id),
            feedback_id,
            events,
        )

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset

    def _require_feedback(self, feedback_id: ReviewFeedbackId) -> ReviewFeedbackRecord:
        feedback = self._repository.get_review_feedback(feedback_id)
        if feedback is None:
            raise ValueError(f"unknown review feedback: {feedback_id}")
        return feedback

    def _result(
        self,
        changeset: ChangesetRecord,
        feedback_id: ReviewFeedbackId,
        events: list[EventEnvelope],
    ) -> ReviewFeedbackRecordResult:
        feedback = self._require_feedback(feedback_id)
        scopes = self._repository.list_review_feedback_scopes(
            changeset.session_id,
            feedback_id,
        )
        return ReviewFeedbackRecordResult(
            feedback=feedback,
            scopes=scopes,
            events=events,
            safe_next_actions=[
                changeset_feedback_show_command(feedback_id),
                show_changeset_command(changeset.changeset_id),
            ],
            non_claims=[
                "review feedback is local evidence, not approval",
                "Glassbox did not stage, commit, push, open a PR, or merge",
            ],
        )


__all__ = ["ReviewFeedbackActionService"]
