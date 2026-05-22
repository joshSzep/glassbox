"""Action-state helpers for handoff custody decisions."""

from glassbox.core import HandoffProjectionRecord
from glassbox.core.types_handoff import HandoffCustodyState
from glassbox.core.types_handoff import HandoffSourceKind


def safe_next_actions_for_decision(record: HandoffProjectionRecord) -> list[str]:
    """Default read-only actions to carry with custody decision events."""

    actions = [f"glassbox handoff show {record.session_id} {record.package_id}"]
    if record.source_kind == HandoffSourceKind.SESSION and record.source_id:
        actions.append(f"glassbox session status {record.source_id}")
    return actions


def custody_action_state(record: HandoffProjectionRecord) -> str:
    """Stable dashboard/API action state for a projected handoff record."""

    if record.archived or record.custody_state == HandoffCustodyState.ARCHIVED:
        return "archived-historical"
    if record.custody_state in {
        HandoffCustodyState.CREATED,
        HandoffCustodyState.PROPOSED,
        HandoffCustodyState.IMPORTED_INSPECTED,
    }:
        return "awaiting-recipient"
    if record.custody_state in {
        HandoffCustodyState.ACCEPTED,
        HandoffCustodyState.ACCEPTED_FOR_FOLLOW_UP,
    }:
        return "accepted-needs-follow-up"
    if record.custody_state == HandoffCustodyState.REJECTED:
        return "rejected-needs-sender-review"
    return "inspect"


__all__ = [
    "custody_action_state",
    "safe_next_actions_for_decision",
]
