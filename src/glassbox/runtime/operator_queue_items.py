"""Shared helpers for constructing operator queue items."""

from datetime import datetime

from glassbox.core import NextAction
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionSurface
from glassbox.core import NextActionTarget
from glassbox.core import OperatorQueueDedupeKey
from glassbox.core import OperatorQueueDedupeScope
from glassbox.core import OperatorQueueDismissalPolicy
from glassbox.core import OperatorQueueEvidenceSummary
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.core import OperatorQueueState


def operator_queue_item(
    *,
    item_id: str,
    family: OperatorQueueFamily,
    state: OperatorQueueState,
    priority: NextActionPriority,
    severity: NextActionSeverity,
    target: NextActionTarget,
    owner_label: str,
    action_kind: NextActionKind,
    action_title: str,
    action_summary: str,
    evidence_kind: NextActionEvidenceKind,
    evidence_id: str,
    evidence_summary: str,
    dedupe_key: str,
    dismissal_policy: OperatorQueueDismissalPolicy,
    blocking: bool = False,
    action_needed: bool = False,
    stale: bool = False,
    updated_at: datetime | None = None,
) -> OperatorQueueItem:
    """Build a queue item from the common v16 safe-action shape."""

    action = NextAction(
        action_id=item_id.removeprefix("queue:"),
        title=action_title,
        summary=action_summary,
        kind=action_kind,
        priority=priority,
        severity=severity,
        target=target,
        recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
    )
    evidence = NextActionEvidenceRef(
        kind=evidence_kind,
        ref_id=evidence_id,
        summary=evidence_summary,
        freshness="stale" if stale else None,
    )
    return OperatorQueueItem(
        item_id=item_id,
        family=family,
        state=state,
        priority=priority,
        severity=severity,
        target=target,
        owner_surface=NextActionSurface.DASHBOARD,
        owner_label=owner_label,
        safe_next_action=action,
        evidence_summary=OperatorQueueEvidenceSummary(
            summary=evidence_summary,
            supporting_evidence=[] if stale else [evidence],
            stale_evidence=[evidence] if stale else [],
            limitation_count=0,
        ),
        dedupe_key=OperatorQueueDedupeKey(
            scope=OperatorQueueDedupeScope.FAMILY_TARGET,
            key=dedupe_key,
            target=target,
        ),
        dismissal_policy=dismissal_policy,
        action_needed=action_needed,
        blocking=blocking,
        stale=stale,
        updated_at=updated_at,
    )


__all__ = ["operator_queue_item"]
