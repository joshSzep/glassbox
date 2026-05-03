"""Explicit operator actions against existing changesets."""

from pathlib import Path

from glassbox.core import ChangesetArchived
from glassbox.core import ChangesetId
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetSourceAttached
from glassbox.core import ChangesetSourceKind
from glassbox.core import EventEnvelope
from glassbox.runtime.changeset_inventory_refresh import (
    ChangesetInventoryRefreshService,
)
from glassbox.runtime.changeset_models import ChangesetInventoryRefreshResult
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_workspace_diff import workspace_diff_reason
from glassbox.runtime.changeset_workspace_diff import workspace_diff_snapshot
from glassbox.services import ArtifactRepository


class ChangesetActionService:
    """Explicit operator actions against an existing changeset."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    def archive_changeset(
        self,
        changeset_id: ChangesetId,
        *,
        reason: str,
        archived_by: str = "operator",
        replacement_changeset_id: ChangesetId | None = None,
    ) -> EventEnvelope:
        changeset = self._require_changeset(changeset_id)
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetArchived(
                        changeset_id=changeset.changeset_id,
                        reason=reason,
                        archived_by=archived_by,
                        replacement_changeset_id=replacement_changeset_id,
                    ),
                )
            ]
        )
        return stored[0]

    def refresh_source_evidence(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        refreshed_by: str = "operator",
    ) -> EventEnvelope:
        changeset = self._require_changeset(changeset_id)
        diff = workspace_diff_snapshot(workspace_root)
        limitation = (
            "basic source refresh only; structured inventory refresh is added "
            "by the change inventory phase"
        )
        if diff.error is not None:
            limitation = f"{limitation}; workspace diff unavailable: {diff.error}"
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetSourceAttached(
                        changeset_id=changeset.changeset_id,
                        source_kind=ChangesetSourceKind.WORKSPACE_DIFF,
                        source_session_id=changeset.session_id,
                        reason=(
                            f"{workspace_diff_reason(diff)}; "
                            f"refreshed by {refreshed_by}"
                        ),
                        limitation=limitation,
                        task_id=changeset.task_id,
                        turn_id=changeset.turn_id,
                        branch_search_id=changeset.branch_search_id,
                        branch_candidate_id=changeset.branch_candidate_id,
                    ),
                )
            ]
        )
        return stored[0]

    async def refresh_inventory(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        refreshed_by: str = "operator",
    ) -> ChangesetInventoryRefreshResult:
        return await ChangesetInventoryRefreshService(
            self._repository,
            self._artifact_repository,
        ).refresh_inventory(
            changeset_id,
            workspace_root,
            refreshed_by=refreshed_by,
        )

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


__all__ = ["ChangesetActionService"]
