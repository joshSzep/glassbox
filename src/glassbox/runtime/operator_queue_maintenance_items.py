"""Maintenance-cue rows for the unified operator queue."""

from collections.abc import Sequence

from glassbox.core import MaintenanceCue
from glassbox.core import NextAction
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSurface
from glassbox.core import OperatorQueueDedupeKey
from glassbox.core import OperatorQueueDedupeScope
from glassbox.core import OperatorQueueDismissalPolicy
from glassbox.core import OperatorQueueEvidenceSummary
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.core import OperatorQueueState


def build_maintenance_queue_items(
    cues: Sequence[MaintenanceCue],
) -> list[OperatorQueueItem]:
    """Project authoritative maintenance cues into queue rows."""

    return [_maintenance_cue_item(cue) for cue in cues]


def _maintenance_cue_item(cue: MaintenanceCue) -> OperatorQueueItem:
    state = _maintenance_cue_state(cue)
    stale = bool(cue.stale_evidence)
    action_needed = cue.priority in {
        NextActionPriority.ACTION_NEEDED,
        NextActionPriority.DEGRADED,
    }
    action = (
        cue.safe_next_actions[0]
        if cue.safe_next_actions
        else NextAction(
            action_id=f"{cue.kind.value}:inspect",
            title=cue.title,
            summary=cue.summary,
            kind=NextActionKind.INSPECT,
            priority=cue.priority,
            severity=cue.severity,
            target=cue.target,
            recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
        )
    )
    limitations = list(cue.limitations)
    if cue.destructive_remediation_note is not None:
        limitations.append(cue.destructive_remediation_note)
    return OperatorQueueItem(
        item_id=f"queue:maintenance:{cue.kind.value}",
        family=OperatorQueueFamily.MAINTENANCE,
        state=state,
        priority=cue.priority,
        severity=cue.severity,
        target=cue.target,
        owner_surface=NextActionSurface.DASHBOARD,
        owner_label=cue.title,
        safe_next_action=action,
        evidence_summary=OperatorQueueEvidenceSummary(
            summary=cue.summary,
            supporting_evidence=cue.supporting_evidence,
            missing_evidence=cue.missing_evidence,
            stale_evidence=cue.stale_evidence,
            limitation_count=len(limitations),
        ),
        dedupe_key=OperatorQueueDedupeKey(
            scope=OperatorQueueDedupeScope.WORKSPACE_SINGLETON,
            key=f"maintenance:{cue.kind.value}",
            target=cue.target,
        ),
        dismissal_policy=OperatorQueueDismissalPolicy.NOT_DISMISSIBLE,
        action_needed=action_needed,
        stale=stale,
        limitations=limitations,
    )


def _maintenance_cue_state(cue: MaintenanceCue) -> OperatorQueueState:
    if cue.priority == NextActionPriority.ACTION_NEEDED:
        return OperatorQueueState.ACTION_NEEDED
    if cue.priority == NextActionPriority.DEGRADED:
        return OperatorQueueState.DEGRADED
    if cue.stale_evidence:
        return OperatorQueueState.STALE
    return OperatorQueueState.WATCHING


__all__ = ["build_maintenance_queue_items"]
