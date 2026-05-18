"""Handoff-derived rows for the unified operator queue."""

from glassbox.core import HandoffCustodyState
from glassbox.core import HandoffProjectionRecord
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import OperatorQueueDismissalPolicy
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.core import OperatorQueueState
from glassbox.runtime.operator_queue_items import operator_queue_item


def build_handoff_queue_items(
    handoffs: list[HandoffProjectionRecord],
) -> list[OperatorQueueItem]:
    """Build queue rows from projected handoff custody records."""

    return [
        item
        for handoff in handoffs
        if not handoff.archived
        for item in [_handoff_queue_item(handoff)]
        if item is not None
    ]


def _handoff_queue_item(
    handoff: HandoffProjectionRecord,
) -> OperatorQueueItem | None:
    state = handoff.custody_state
    if state in {
        HandoffCustodyState.CREATED,
        HandoffCustodyState.PROPOSED,
        HandoffCustodyState.IMPORTED_INSPECTED,
    }:
        return _queue_item(
            handoff,
            suffix="awaiting-recipient",
            family=OperatorQueueFamily.REVIEW_BLOCKING,
            state=OperatorQueueState.ACTION_NEEDED,
            priority=NextActionPriority.ACTION_NEEDED,
            severity=NextActionSeverity.MEDIUM,
            owner_label="Handoff awaiting recipient",
            action_title="Inspect handoff custody",
            action_summary="Accept, reject, or archive this local handoff record.",
            evidence_summary="A handoff package is awaiting a recipient decision.",
            action_needed=True,
            blocking=True,
        )
    if state in {
        HandoffCustodyState.ACCEPTED,
        HandoffCustodyState.ACCEPTED_FOR_FOLLOW_UP,
    }:
        return _queue_item(
            handoff,
            suffix="accepted-follow-up",
            family=OperatorQueueFamily.ADVISORY,
            state=OperatorQueueState.READY,
            priority=NextActionPriority.RECOMMENDED,
            severity=NextActionSeverity.INFO,
            owner_label="Accepted handoff",
            action_title="Inspect accepted follow-up",
            action_summary="Review the accepted handoff before follow-up work.",
            evidence_summary=(
                "A handoff was accepted and has retained follow-up intent."
            ),
            action_needed=True,
            blocking=False,
        )
    if state == HandoffCustodyState.REJECTED:
        return _queue_item(
            handoff,
            suffix="rejected-sender-review",
            family=OperatorQueueFamily.REVIEW_BLOCKING,
            state=OperatorQueueState.ACTION_NEEDED,
            priority=NextActionPriority.ACTION_NEEDED,
            severity=NextActionSeverity.MEDIUM,
            owner_label="Rejected handoff",
            action_title="Review rejected handoff",
            action_summary=handoff.decision_reason
            or "Sender should inspect the retained rejection reason.",
            evidence_summary="A handoff was rejected and needs sender review.",
            action_needed=True,
            blocking=True,
        )
    return None


def _queue_item(
    handoff: HandoffProjectionRecord,
    *,
    suffix: str,
    family: OperatorQueueFamily,
    state: OperatorQueueState,
    priority: NextActionPriority,
    severity: NextActionSeverity,
    owner_label: str,
    action_title: str,
    action_summary: str,
    evidence_summary: str,
    action_needed: bool,
    blocking: bool,
) -> OperatorQueueItem:
    session_id = handoff.session_id
    target = NextActionTarget(
        kind=NextActionTargetKind.SESSION,
        target_id=session_id,
        label=f"Handoff {handoff.package_id}",
    )
    return operator_queue_item(
        item_id=f"queue:handoff:{session_id}:{handoff.package_id}:{suffix}",
        family=family,
        state=state,
        priority=priority,
        severity=severity,
        target=target,
        owner_label=owner_label,
        action_kind=NextActionKind.HANDOFF,
        action_title=action_title,
        action_summary=action_summary,
        evidence_kind=NextActionEvidenceKind.EVENT,
        evidence_id=handoff.package_id,
        evidence_summary=evidence_summary,
        dedupe_key=f"handoff:{session_id}:{handoff.package_id}:{suffix}",
        dismissal_policy=OperatorQueueDismissalPolicy.CANONICAL_DECISION_REQUIRED,
        blocking=blocking,
        action_needed=action_needed,
        updated_at=handoff.updated_at,
    )


__all__ = ["build_handoff_queue_items"]
