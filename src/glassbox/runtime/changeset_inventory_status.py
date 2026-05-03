"""Inventory freshness helpers for changeset read surfaces."""

from pathlib import Path

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ReviewFeedbackFixupInventoryRecord
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_workspace_diff import workspace_diff_source_digest
from glassbox.runtime.review_responses import ReviewFixupInventoryStatus
from glassbox.runtime.review_responses import review_fixup_inventory_status


def inventory_status(
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
    *,
    workspace_root: Path | None,
) -> ChangesetInventoryStatus:
    """Compare the retained inventory digest with the current workspace."""

    refresh_action = f"glassbox changeset refresh {changeset.changeset_id} --cwd ."
    if inventory is None:
        return ChangesetInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason="no structured change inventory is attached yet",
            safe_next_actions=[refresh_action],
        )
    if workspace_root is None:
        return ChangesetInventoryStatus(
            freshness=inventory.freshness,
            stale=inventory.freshness
            in {
                ChangesetInventoryFreshness.STALE,
                ChangesetInventoryFreshness.SUPERSEDED,
            },
            recorded_source_digest=inventory.source_digest,
            safe_next_actions=[refresh_action],
        )
    current = workspace_diff_source_digest(workspace_root)
    if current.error is not None:
        return ChangesetInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason=f"workspace source digest unavailable: {current.error}",
            recorded_source_digest=inventory.source_digest,
            current_source_digest=current.digest,
            safe_next_actions=[refresh_action],
        )
    if inventory.source_digest is None:
        return ChangesetInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason="latest inventory has no recorded workspace source digest",
            recorded_source_digest=None,
            current_source_digest=current.digest,
            safe_next_actions=[refresh_action],
        )
    source_digest_changed = inventory.source_digest != current.digest
    if source_digest_changed:
        return ChangesetInventoryStatus(
            freshness=ChangesetInventoryFreshness.STALE,
            stale=True,
            reason=(
                "workspace diff source digest changed since the latest inventory "
                "artifact was recorded"
            ),
            recorded_source_digest=inventory.source_digest,
            current_source_digest=current.digest,
            safe_next_actions=[refresh_action],
        )
    return ChangesetInventoryStatus(
        freshness=inventory.freshness,
        stale=inventory.freshness == ChangesetInventoryFreshness.STALE,
        recorded_source_digest=inventory.source_digest,
        current_source_digest=current.digest,
        safe_next_actions=[refresh_action],
    )


def inventory_with_status_freshness(
    inventory: ChangesetInventoryRecord | None,
    status: ChangesetInventoryStatus,
) -> ChangesetInventoryRecord | None:
    """Return an inventory record whose freshness reflects live status."""

    if inventory is None or inventory.freshness == status.freshness:
        return inventory
    return inventory.model_copy(update={"freshness": status.freshness})


def review_fixup_inventory_freshness(
    record: ReviewFeedbackFixupInventoryRecord,
    workspace_root: Path,
) -> ReviewFixupInventoryStatus:
    """Assess retained fixup inventory freshness against the current workspace."""

    current = workspace_diff_source_digest(workspace_root)
    return review_fixup_inventory_status(
        feedback_id=record.feedback_id,
        changeset_id=record.changeset_id,
        recorded_source_digest=record.source_digest,
        current_source_digest=current.digest,
        current_error=current.error,
    )


__all__ = [
    "inventory_status",
    "inventory_with_status_freshness",
    "review_fixup_inventory_freshness",
]
