"""Transport-agnostic changeset query facade."""

from pathlib import Path

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetRecord
from glassbox.core import ManualEvidenceId
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceState
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackFixupInventoryRecord
from glassbox.core import ReviewFeedbackFixupPathRecord
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.core import SessionId
from glassbox.runtime.changeset_detail import build_changeset_detail_view
from glassbox.runtime.changeset_detail import (
    review_feedback_response_status as _review_feedback_response_status,
)
from glassbox.runtime.changeset_detail import review_response_summary
from glassbox.runtime.changeset_models import ChangesetDetailView
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFeedbackResponseStatus


class ChangesetQueryService:
    """Read-only changeset query service."""

    def __init__(self, repository: ChangesetRepository) -> None:
        self._repository = repository

    def list_changesets(
        self,
        *,
        session_id: SessionId | None = None,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[ChangesetRecord]:
        return self._repository.list_changesets(
            session_id=session_id,
            include_archived=include_archived,
            limit=limit,
        )

    def list_review_feedback(
        self,
        *,
        session_id: SessionId | None = None,
        changeset_id: ChangesetId | None = None,
        disposition: ReviewFeedbackDisposition | None = None,
        include_archived: bool = False,
        file_path: str | None = None,
        limit: int | None = None,
    ) -> list[ReviewFeedbackRecord]:
        return self._repository.list_review_feedback(
            session_id=session_id,
            changeset_id=changeset_id,
            disposition=disposition,
            include_archived=include_archived,
            file_path=file_path,
            limit=limit,
        )

    def get_review_feedback(
        self,
        feedback_id: ReviewFeedbackId,
    ) -> ReviewFeedbackRecord | None:
        return self._repository.get_review_feedback(feedback_id)

    def list_review_feedback_scopes(
        self,
        session_id: SessionId,
        feedback_id: ReviewFeedbackId,
    ) -> list[ReviewFeedbackScopeRecord]:
        return self._repository.list_review_feedback_scopes(session_id, feedback_id)

    def list_review_feedback_fixup_inventories(
        self,
        session_id: SessionId,
        feedback_id: ReviewFeedbackId,
    ) -> list[ReviewFeedbackFixupInventoryRecord]:
        return self._repository.list_review_feedback_fixup_inventories(
            session_id,
            feedback_id,
        )

    def list_review_feedback_fixup_paths(
        self,
        session_id: SessionId,
        feedback_id: ReviewFeedbackId,
        artifact_id: ArtifactId,
    ) -> list[ReviewFeedbackFixupPathRecord]:
        return self._repository.list_review_feedback_fixup_paths(
            session_id,
            feedback_id,
            artifact_id,
        )

    def list_manual_evidence(
        self,
        *,
        session_id: SessionId | None = None,
        changeset_id: ChangesetId | None = None,
        target_kind: ManualEvidenceTargetKind | None = None,
        target_id: str | None = None,
        state: ManualEvidenceState | None = None,
        include_archived: bool = False,
        include_rejected: bool = False,
        include_superseded: bool = False,
        limit: int | None = None,
    ) -> list[ManualEvidenceRecord]:
        return self._repository.list_manual_evidence(
            session_id=session_id,
            changeset_id=changeset_id,
            target_kind=target_kind,
            target_id=target_id,
            state=state,
            include_archived=include_archived,
            include_rejected=include_rejected,
            include_superseded=include_superseded,
            limit=limit,
        )

    def get_manual_evidence(
        self,
        evidence_id: ManualEvidenceId,
    ) -> ManualEvidenceRecord | None:
        return self._repository.get_manual_evidence(evidence_id)

    def get_review_feedback_response_status(
        self,
        feedback_id: ReviewFeedbackId,
        *,
        workspace_root: Path | None = None,
    ) -> ReviewFeedbackResponseStatus:
        return _review_feedback_response_status(
            self._repository,
            feedback_id,
            workspace_root=workspace_root,
        )

    def get_review_response_summary(
        self,
        changeset_id: ChangesetId,
        *,
        workspace_root: Path | None = None,
    ) -> ChangesetReviewResponseSummary:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return review_response_summary(
            self._repository,
            changeset,
            workspace_root=workspace_root,
        )

    def get_detail(
        self,
        changeset_id: ChangesetId,
        *,
        workspace_root: Path | None = None,
    ) -> ChangesetDetailView:
        return build_changeset_detail_view(
            self._repository,
            changeset_id,
            workspace_root=workspace_root,
        )


__all__ = ["ChangesetQueryService"]
