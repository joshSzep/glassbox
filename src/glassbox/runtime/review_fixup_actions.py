"""Review-feedback fixup inventory action service."""

from pathlib import Path

from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetRecord
from glassbox.core import EventEnvelope
from glassbox.core import ReviewFeedbackFixupInventoryAttached
from glassbox.core import ReviewFeedbackFixupInventoryRecord
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFixupSourceKind
from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
from glassbox.runtime.changeset_inventory_status import review_fixup_inventory_freshness
from glassbox.runtime.changeset_models import ReviewFeedbackFixupInventoryResult
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_workspace_diff import diff_summary_without_local_state
from glassbox.runtime.changeset_workspace_diff import workspace_diff_source_digest
from glassbox.runtime.review_responses import REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION
from glassbox.runtime.review_responses import ReviewFixupInventoryStatus
from glassbox.runtime.review_responses import review_fixup_inventory_artifact_json
from glassbox.runtime.review_responses import (
    review_fixup_inventory_from_change_inventory,
)
from glassbox.runtime.review_responses import review_fixup_inventory_status
from glassbox.services import ArtifactRepository
from glassbox.tools.workflow import DiffSummaryArgs
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import DiffSummaryTool


class ReviewFeedbackFixupInventoryService:
    """Attach bounded fixup inventory evidence to review feedback."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    async def record_workspace_inventory(
        self,
        feedback_id: ReviewFeedbackId,
        workspace_root: Path,
        *,
        source_kind: ReviewFixupSourceKind = (
            ReviewFixupSourceKind.MANUAL_WORKSPACE_EDIT
        ),
        source_summary: str = "operator recorded response-linked workspace inventory",
        recorded_by: str = "operator",
    ) -> ReviewFeedbackFixupInventoryResult:
        if self._artifact_repository is None:
            raise ValueError("artifact repository is required for fixup inventory")
        feedback = self._require_feedback(feedback_id)
        changeset = self._require_changeset(feedback.changeset_id)
        scopes = self._repository.list_review_feedback_scopes(
            feedback.session_id,
            feedback.feedback_id,
        )
        latest_inventory = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        diff_summary = await DiffSummaryTool(workspace_root).execute(
            DiffSummaryArgs(
                scope=DiffSummaryScope.WORKSPACE,
                max_files=1000,
                inline_file_limit=200,
            )
        )
        diff_summary = diff_summary_without_local_state(diff_summary)
        inventory = change_inventory_from_diff_summary(
            diff_summary,
            changeset_id=changeset.changeset_id,
            provenance_events=self._repository.read_session_events(
                changeset.session_id
            ),
        )
        source_digest = workspace_diff_source_digest(workspace_root)
        freshness = (
            ChangesetInventoryFreshness.UNKNOWN
            if source_digest.error is not None
            else ChangesetInventoryFreshness.FRESH
        )
        fixup_inventory = review_fixup_inventory_from_change_inventory(
            inventory,
            feedback=feedback,
            scopes=scopes,
            source_kind=source_kind,
            source_summary=source_summary,
            source_digest=source_digest.digest,
            inventory_freshness=freshness,
            latest_changeset_inventory_artifact_id=(
                str(latest_inventory.artifact_id)
                if latest_inventory is not None
                else None
            ),
        )
        artifact = self._artifact_repository.write_text_artifact(
            changeset.session_id,
            review_fixup_inventory_artifact_json(fixup_inventory),
            suffix=".review-fixup-inventory.json",
        )
        status = review_fixup_inventory_status(
            feedback_id=feedback.feedback_id,
            changeset_id=changeset.changeset_id,
            recorded_source_digest=source_digest.digest,
            current_source_digest=source_digest.digest,
            current_error=source_digest.error,
        )
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ReviewFeedbackFixupInventoryAttached(
                        feedback_id=feedback.feedback_id,
                        changeset_id=changeset.changeset_id,
                        artifact_id=artifact.artifact_id,
                        artifact_schema_version=REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION,
                        source_kind=source_kind,
                        source_summary=source_summary,
                        source_digest=source_digest.digest,
                        inventory_freshness=freshness,
                        changed_path_count=fixup_inventory.changed_path_count,
                        matched_scope_path_count=(
                            fixup_inventory.matched_scope_path_count
                        ),
                        stale=status.stale,
                        stale_reason=status.reason,
                        recorded_by=recorded_by,
                        paths=fixup_inventory.paths,
                        task_id=feedback.task_id or changeset.task_id,
                        turn_id=feedback.turn_id,
                        verification_id=feedback.verification_id,
                    ),
                )
            ]
        )
        return ReviewFeedbackFixupInventoryResult(
            feedback_id=feedback.feedback_id,
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            artifact=artifact,
            inventory=fixup_inventory,
            event=stored[0],
            status=status,
        )

    def assess_record_freshness(
        self,
        record: ReviewFeedbackFixupInventoryRecord,
        workspace_root: Path,
    ) -> ReviewFixupInventoryStatus:
        return review_fixup_inventory_freshness(record, workspace_root)

    def _require_feedback(self, feedback_id: ReviewFeedbackId) -> ReviewFeedbackRecord:
        feedback = self._repository.get_review_feedback(feedback_id)
        if feedback is None:
            raise ValueError(f"unknown review feedback: {feedback_id}")
        return feedback

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


__all__ = ["ReviewFeedbackFixupInventoryService"]
