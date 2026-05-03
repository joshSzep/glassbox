"""Runtime service for deriving and inspecting reviewable changesets."""

import json
from pathlib import Path

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessDecided
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefCreated
from glassbox.core import EventEnvelope
from glassbox.core import SessionId
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.changeset_detail import (
    changeset_command_evidence_summary as _changeset_command_evidence_summary,
)
from glassbox.runtime.changeset_detail import (
    manual_evidence_for_preview as _manual_evidence_for_preview,
)
from glassbox.runtime.changeset_detail import (
    review_feedback_for_preview as _review_feedback_for_preview,
)
from glassbox.runtime.changeset_detail import (
    review_response_summary_for_preview as _review_response_summary_for_preview,
)
from glassbox.runtime.changeset_inventory_status import (
    inventory_status as _inventory_status,
)
from glassbox.runtime.changeset_models import ChangesetReviewBriefGenerationResult
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_review_brief_sections import _review_brief_artifact
from glassbox.runtime.changeset_review_brief_sections import _review_brief_limitations
from glassbox.runtime.changeset_review_brief_sections import _review_readiness_reason
from glassbox.runtime.changeset_review_brief_sections import _review_readiness_state
from glassbox.runtime.changeset_verification import ChangesetVerificationService
from glassbox.runtime.review_briefs import REVIEW_BRIEF_ARTIFACT_SCHEMA_VERSION
from glassbox.runtime.review_briefs import review_brief_artifact_json
from glassbox.runtime.review_briefs import review_brief_markdown
from glassbox.services import ArtifactRepository


class ChangesetReviewBriefService:
    """Generate reviewer-safe briefs from deterministic changeset evidence."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    def generate(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        created_by: str = "operator",
    ) -> ChangesetReviewBriefGenerationResult:
        """Generate and retain one redacted review brief for a changeset."""

        if self._artifact_repository is None:
            raise ValueError("artifact repository is required for review briefs")
        changeset = self._require_changeset(changeset_id)
        sources = self._repository.list_changeset_sources(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        verification_posture = self._repository.get_changeset_verification_posture(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, inventory_limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        inventory_status = _inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        verification_plan = ChangesetVerificationService(
            self._repository,
            self._artifact_repository,
        ).preview_plan(changeset.changeset_id, workspace_root)
        command_evidence = _changeset_command_evidence_summary(
            self._repository,
            changeset,
        )
        review_feedback = _review_feedback_for_preview(self._repository, changeset)
        review_response_summary = _review_response_summary_for_preview(
            self._repository,
            changeset,
            workspace_root=workspace_root,
        )
        manual_evidence = _manual_evidence_for_preview(self._repository, changeset)
        limitations = _review_brief_limitations(
            sources=sources,
            inventory=inventory,
            inventory_status=inventory_status,
            inventory_limitations=inventory_limitations,
            verification_plan=verification_plan,
            command_evidence=command_evidence,
            review_response_summary=review_response_summary,
            manual_evidence=manual_evidence,
        )
        review_state, blockers = _review_readiness_state(
            inventory_status=inventory_status,
            verification_plan=verification_plan,
            changeset=changeset,
            review_response_summary=review_response_summary,
        )
        brief = _review_brief_artifact(
            changeset=changeset,
            sources=sources,
            inventory_record=inventory_record,
            inventory=inventory,
            inventory_status=inventory_status,
            verification_posture=verification_posture,
            verification_plan=verification_plan,
            command_evidence=command_evidence,
            review_feedback=review_feedback,
            review_response_summary=review_response_summary,
            manual_evidence=manual_evidence,
            limitations=limitations,
        )
        content = review_brief_artifact_json(brief)
        artifact = self._artifact_repository.write_text_artifact(
            changeset.session_id,
            content,
            suffix=".changeset-review-brief.json",
        )
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetReviewBriefCreated(
                        changeset_id=changeset.changeset_id,
                        artifact_id=artifact.artifact_id,
                        artifact_schema_version=REVIEW_BRIEF_ARTIFACT_SCHEMA_VERSION,
                        render_targets=brief.render_targets,
                        inventory_artifact_id=(
                            inventory_record.artifact_id
                            if inventory_record is not None
                            else None
                        ),
                        verification_id=(
                            verification_posture.verification_id
                            if verification_posture is not None
                            else None
                        ),
                        task_id=changeset.task_id,
                        turn_id=changeset.turn_id,
                        created_by=created_by,
                        redacted=brief.redacted,
                        local_only=brief.local_only,
                    ),
                ),
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetReadinessDecided(
                        changeset_id=changeset.changeset_id,
                        readiness_kind=ChangesetReadinessKind.REVIEW,
                        state=review_state,
                        reason=_review_readiness_reason(review_state, blockers),
                        blockers=blockers,
                        safe_next_actions=brief.safe_inspection_commands,
                        inventory_artifact_id=(
                            inventory_record.artifact_id
                            if inventory_record is not None
                            else None
                        ),
                        review_brief_artifact_id=artifact.artifact_id,
                        verification_id=(
                            verification_posture.verification_id
                            if verification_posture is not None
                            else None
                        ),
                        task_id=changeset.task_id,
                        turn_id=changeset.turn_id,
                        accepted_risk_count=changeset.accepted_risk_count,
                        decided_by=created_by,
                    ),
                ),
            ]
        )
        return ChangesetReviewBriefGenerationResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            artifact=artifact,
            brief=brief,
            markdown=review_brief_markdown(brief),
            event=stored[0],
            readiness_event=stored[1],
            limitations=limitations,
        )

    def _load_inventory_artifact(
        self,
        session_id: SessionId,
        inventory_record: ChangesetInventoryRecord | None,
    ) -> tuple[ChangeInventoryArtifact | None, list[str]]:
        if inventory_record is None:
            return None, ["no structured change inventory is attached yet"]
        if self._artifact_repository is None:
            return None, ["artifact repository is unavailable"]
        try:
            content = self._artifact_repository.read_text_artifact(
                _changeset_inventory_artifact_path(
                    session_id,
                    inventory_record.artifact_id,
                )
            )
            return ChangeInventoryArtifact.model_validate_json(content), []
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return None, [f"change inventory artifact could not be read: {exc}"]

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


def _changeset_inventory_artifact_path(
    session_id: SessionId,
    artifact_id: ArtifactId,
) -> Path:
    return (
        Path(".glassbox")
        / "sessions"
        / str(session_id)
        / "artifacts"
        / f"{artifact_id}.changeset-inventory.json"
    )
