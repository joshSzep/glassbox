"""Repository protocols for changeset runtime services."""

from typing import Protocol

from glassbox.core import ArtifactId
from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchSearchId
from glassbox.core import BranchSearchRecord
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetSourceRecord
from glassbox.core import ChangesetVerificationPostureRecord
from glassbox.core import EventEnvelope
from glassbox.core import ManualEvidenceId
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceState
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ProjectionHealth
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackFixupInventoryRecord
from glassbox.core import ReviewFeedbackFixupPathRecord
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.core import SessionId
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.core import TaskId
from glassbox.core import TaskRecord
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import ToolAttemptRecord


class ChangesetDerivationRepository(Protocol):
    """Repository methods required by changeset derivation."""

    def get_session(self, session_id: SessionId) -> SessionRecord | None: ...

    def get_session_state(self, session_id: SessionId) -> SessionState | None: ...

    def inspect_session_projection_health(
        self,
        session_id: SessionId,
    ) -> ProjectionHealth: ...

    def get_task(self, task_id: TaskId) -> TaskRecord | None: ...

    def get_branch_search(
        self,
        search_id: BranchSearchId,
    ) -> BranchSearchRecord | None: ...

    def list_branch_candidates(
        self,
        session_id: SessionId,
        search_id: BranchSearchId,
    ) -> list[BranchCandidateRecord]: ...

    def append_events(
        self,
        events: list[EventEnvelope],
    ) -> list[EventEnvelope]: ...


class ChangesetRepository(ChangesetDerivationRepository, Protocol):
    """Repository methods required by changeset query and action services."""

    def list_changesets(
        self,
        *,
        session_id: SessionId | None = None,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[ChangesetRecord]: ...

    def get_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord | None: ...

    def list_changeset_sources(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> list[ChangesetSourceRecord]: ...

    def get_changeset_inventory(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> ChangesetInventoryRecord | None: ...

    def get_changeset_verification_posture(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> ChangesetVerificationPostureRecord | None: ...

    def list_changeset_review_briefs(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> list[ChangesetReviewBriefRecord]: ...

    def list_changeset_readiness(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> list[ChangesetReadinessRecord]: ...

    def list_review_feedback(
        self,
        *,
        session_id: SessionId | None = None,
        changeset_id: ChangesetId | None = None,
        disposition: ReviewFeedbackDisposition | None = None,
        include_archived: bool = False,
        file_path: str | None = None,
        limit: int | None = None,
    ) -> list[ReviewFeedbackRecord]: ...

    def get_review_feedback(
        self,
        feedback_id: ReviewFeedbackId,
    ) -> ReviewFeedbackRecord | None: ...

    def list_review_feedback_scopes(
        self,
        session_id: SessionId,
        feedback_id: ReviewFeedbackId,
    ) -> list[ReviewFeedbackScopeRecord]: ...

    def list_review_feedback_fixup_inventories(
        self,
        session_id: SessionId,
        feedback_id: ReviewFeedbackId,
    ) -> list[ReviewFeedbackFixupInventoryRecord]: ...

    def list_review_feedback_fixup_paths(
        self,
        session_id: SessionId,
        feedback_id: ReviewFeedbackId,
        artifact_id: ArtifactId,
    ) -> list[ReviewFeedbackFixupPathRecord]: ...

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
    ) -> list[ManualEvidenceRecord]: ...

    def get_manual_evidence(
        self,
        evidence_id: ManualEvidenceId,
    ) -> ManualEvidenceRecord | None: ...

    def list_task_verification_ledger(
        self,
        session_id: SessionId,
        task_id: TaskId,
    ) -> list[TaskVerificationLedgerRecord]: ...

    def list_tool_attempts(
        self,
        session_id: SessionId,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ToolAttemptRecord]: ...

    def read_session_events(self, session_id: SessionId) -> list[EventEnvelope]: ...


__all__ = ["ChangesetDerivationRepository", "ChangesetRepository"]
