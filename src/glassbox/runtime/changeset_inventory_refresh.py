"""Changeset inventory refresh mutation service."""

from pathlib import Path

from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRefreshed
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetRiskLevel
from glassbox.core import EventEnvelope
from glassbox.core import EventPayloadType
from glassbox.runtime.change_inventory import CHANGE_INVENTORY_ARTIFACT_SCHEMA_VERSION
from glassbox.runtime.change_inventory import change_inventory_artifact_json
from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
from glassbox.runtime.changeset_models import ChangesetInventoryRefreshResult
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_workspace_diff import diff_summary_without_local_state
from glassbox.runtime.changeset_workspace_diff import workspace_diff_source_digest
from glassbox.services import ArtifactRepository
from glassbox.tools.workflow import DiffSummaryArgs
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import DiffSummaryTool


class ChangesetInventoryRefreshService:
    """Record fresh structured inventory artifacts for existing changesets."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    async def refresh_inventory(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        refreshed_by: str = "operator",
    ) -> ChangesetInventoryRefreshResult:
        """Record a fresh structured inventory artifact for one changeset."""

        if self._artifact_repository is None:
            raise ValueError("artifact repository is required for inventory refresh")
        changeset = self._require_changeset(changeset_id)
        previous_inventory = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        events = self._repository.read_session_events(changeset.session_id)
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
            provenance_events=events,
        )
        source_digest = workspace_diff_source_digest(workspace_root)
        content = change_inventory_artifact_json(inventory)
        artifact = self._artifact_repository.write_text_artifact(
            changeset.session_id,
            content,
            suffix=".changeset-inventory.json",
        )
        freshness = (
            ChangesetInventoryFreshness.UNKNOWN
            if source_digest.error is not None
            else ChangesetInventoryFreshness.FRESH
        )
        payloads: list[EventPayloadType] = []
        if previous_inventory is not None:
            payloads.append(
                ChangesetInventoryRefreshed(
                    changeset_id=changeset.changeset_id,
                    artifact_id=previous_inventory.artifact_id,
                    artifact_schema_version=previous_inventory.artifact_schema_version,
                    freshness=ChangesetInventoryFreshness.SUPERSEDED,
                    changed_path_count=previous_inventory.changed_path_count,
                    source_digest=previous_inventory.source_digest,
                    previous_artifact_id=previous_inventory.previous_artifact_id,
                    refreshed_by=refreshed_by,
                    risk_level=previous_inventory.risk_level,
                    risk_summary=previous_inventory.risk_summary,
                    unresolved_risk_count=previous_inventory.unresolved_risk_count,
                    accepted_risk_count=previous_inventory.accepted_risk_count,
                    task_id=previous_inventory.task_id,
                    turn_id=previous_inventory.turn_id,
                    branch_search_id=previous_inventory.branch_search_id,
                    branch_candidate_id=previous_inventory.branch_candidate_id,
                )
            )
        payloads.append(
            ChangesetInventoryRefreshed(
                changeset_id=changeset.changeset_id,
                artifact_id=artifact.artifact_id,
                artifact_schema_version=CHANGE_INVENTORY_ARTIFACT_SCHEMA_VERSION,
                freshness=freshness,
                changed_path_count=inventory.summary.changed_path_count,
                source_digest=source_digest.digest,
                previous_artifact_id=(
                    previous_inventory.artifact_id
                    if previous_inventory is not None
                    else None
                ),
                refreshed_by=refreshed_by,
                risk_level=ChangesetRiskLevel(inventory.summary.risk_level),
                risk_summary=inventory.summary.risk_summary,
                unresolved_risk_count=inventory.summary.unresolved_risk_count,
                accepted_risk_count=inventory.summary.accepted_risk_count,
                task_id=changeset.task_id,
                turn_id=changeset.turn_id,
                branch_search_id=changeset.branch_search_id,
                branch_candidate_id=changeset.branch_candidate_id,
            )
        )
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=payload,
                )
                for payload in payloads
            ]
        )
        return ChangesetInventoryRefreshResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            artifact=artifact,
            inventory=inventory,
            event=stored[-1],
            superseded_event=stored[0] if len(stored) > 1 else None,
            freshness=freshness,
            source_digest=source_digest.digest,
        )

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


__all__ = ["ChangesetInventoryRefreshService"]
