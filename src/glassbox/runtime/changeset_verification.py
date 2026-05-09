"""Changeset verification preview and evidence recording service."""

import json
from pathlib import Path

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetVerificationPostureUpdated
from glassbox.core import EventEnvelope
from glassbox.core import SessionId
from glassbox.core import TaskId
from glassbox.core import TaskVerificationId
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.changeset_detail import manual_evidence_for_preview
from glassbox.runtime.changeset_detail import review_response_summary_for_preview
from glassbox.runtime.changeset_inventory_status import inventory_status
from glassbox.runtime.changeset_models import ChangesetVerificationEvidenceRecordResult
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_topology import derive_changeset_topology_impacts
from glassbox.runtime.changeset_verification_preview import artifact_ids_from_readiness
from glassbox.runtime.changeset_verification_preview import eval_profile_ids_for_preview
from glassbox.runtime.changeset_verification_preview import inventory_paths_for_preview
from glassbox.runtime.changeset_verification_preview import preview_commands
from glassbox.runtime.changeset_verification_preview import recipe_previews
from glassbox.runtime.changeset_verification_preview import recommendation_for_preview
from glassbox.runtime.changeset_verification_preview import release_surface_previews
from glassbox.runtime.changeset_verification_preview import (
    review_loop_verification_summary,
)
from glassbox.runtime.changeset_verification_preview import stale_evidence_previews
from glassbox.runtime.changeset_verification_preview import target_previews
from glassbox.runtime.changeset_verification_readiness import (
    derive_changeset_verification_readiness,
)
from glassbox.runtime.workspace_profile import load_workspace_profile
from glassbox.services import ArtifactRepository


class ChangesetVerificationService:
    """Preview and record changeset verification posture from retained evidence."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    def preview_plan(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
    ) -> ChangesetVerificationPlanPreview:
        changeset = self._require_changeset(changeset_id)
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, inventory_limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        status = inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        changed_paths = inventory_paths_for_preview(inventory)
        recommendation, recommendation_limitations = recommendation_for_preview(
            workspace_root,
            changed_paths,
        )
        topology_impacts, topology_limitations = derive_changeset_topology_impacts(
            workspace_root=workspace_root,
            changed_paths=changed_paths,
        )
        limitations = [
            *inventory_limitations,
            *recommendation_limitations,
            *topology_limitations,
            *(
                [status.reason]
                if status.reason is not None
                and status.freshness != ChangesetInventoryFreshness.FRESH
                else []
            ),
        ]
        ledger = self._task_ledger_for_changeset(changeset)
        inventory_freshness = status.freshness
        readiness = derive_changeset_verification_readiness(
            inventory=inventory,
            inventory_freshness=inventory_freshness,
            inventory_sequence=(
                inventory_record.last_sequence if inventory_record is not None else None
            ),
            task_ledger=ledger,
            eval_recommendation=recommendation,
            workspace_profile=load_workspace_profile(workspace_root),
        )
        retained_artifact_ids = artifact_ids_from_readiness(readiness)
        response_summary = review_response_summary_for_preview(
            self._repository,
            changeset,
            workspace_root=workspace_root,
        )
        manual_evidence = manual_evidence_for_preview(self._repository, changeset)
        review_loop_summary = review_loop_verification_summary(
            changeset=changeset,
            response_summary=response_summary,
            manual_evidence=manual_evidence,
            readiness=readiness,
            topology_impacts=topology_impacts,
        )
        return ChangesetVerificationPlanPreview(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            inventory_artifact_id=(
                inventory_record.artifact_id if inventory_record is not None else None
            ),
            inventory_freshness=inventory_freshness,
            changed_paths=changed_paths,
            recommended_commands=preview_commands(
                readiness,
                recommendation,
            ),
            eval_profiles=eval_profile_ids_for_preview(recommendation),
            recipes=recipe_previews(recommendation),
            recommended_targets=target_previews(recommendation),
            release_surfaces=release_surface_previews(recommendation),
            stale_evidence=stale_evidence_previews(readiness),
            topology_impacts=topology_impacts,
            review_loop_summary=review_loop_summary,
            reason_groups=(
                recommendation.reason_groups if recommendation is not None else []
            ),
            expected_scope=changed_paths,
            retained_artifact_ids=retained_artifact_ids,
            readiness=readiness,
            limitations=limitations,
            safe_next_actions=list(
                dict.fromkeys(
                    [
                        *readiness.safe_next_actions,
                        *review_loop_summary.safe_next_actions,
                    ]
                )
            ),
            non_claims=[
                *readiness.non_claims,
                *review_loop_summary.non_claims,
                "verification plan preview does not run commands",
                (
                    "publish, deploy, push, and upload commands are not "
                    "recommended as verification"
                ),
            ],
        )

    def record_existing_evidence(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        task_id: TaskId | None = None,
        verification_id: TaskVerificationId | None = None,
    ) -> ChangesetVerificationEvidenceRecordResult:
        changeset = self._require_changeset(changeset_id)
        resolved_task_id = task_id or changeset.task_id
        if resolved_task_id is None:
            raise ValueError(
                "task_id is required when the changeset is not task-backed"
            )
        ledger = self._repository.list_task_verification_ledger(
            changeset.session_id,
            resolved_task_id,
        )
        if verification_id is not None:
            ledger = [
                entry for entry in ledger if entry.verification_id == verification_id
            ]
        if not ledger:
            raise ValueError("no retained task verification evidence matched")
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, _limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        status = inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        recommendation, _limitations = recommendation_for_preview(
            workspace_root,
            inventory_paths_for_preview(inventory),
        )
        readiness = derive_changeset_verification_readiness(
            inventory=inventory,
            inventory_freshness=status.freshness,
            inventory_sequence=(
                inventory_record.last_sequence if inventory_record is not None else None
            ),
            task_ledger=ledger,
            eval_recommendation=recommendation,
            workspace_profile=load_workspace_profile(workspace_root),
        )
        selected = sorted(ledger, key=lambda entry: entry.last_sequence)
        primary = selected[-1]
        retained_artifact_ids = artifact_ids_from_readiness(readiness)
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetVerificationPostureUpdated(
                        changeset_id=changeset.changeset_id,
                        state=readiness.state,
                        summary=readiness.summary,
                        verification_id=primary.verification_id,
                        artifact_id=primary.latest_artifact_id
                        or primary.latest_failed_artifact_id,
                        task_id=resolved_task_id,
                        stale_count=readiness.stale_count,
                        missing_count=readiness.missing_count,
                        failed_count=readiness.failed_count,
                        accepted_risk_count=readiness.accepted_risk_count,
                    ),
                )
            ]
        )
        return ChangesetVerificationEvidenceRecordResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            selected_verification_ids=[entry.verification_id for entry in selected],
            retained_artifact_ids=retained_artifact_ids,
            readiness=readiness,
            event=stored[0],
        )

    def _task_ledger_for_changeset(
        self,
        changeset: ChangesetRecord,
    ) -> list[TaskVerificationLedgerRecord]:
        if changeset.task_id is None:
            return []
        return self._repository.list_task_verification_ledger(
            changeset.session_id,
            changeset.task_id,
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


__all__ = ["ChangesetVerificationService"]
