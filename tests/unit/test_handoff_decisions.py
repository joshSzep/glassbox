"""Unit tests for handoff custody decision helpers and queue rows."""

from datetime import UTC
from datetime import datetime

from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffCustodyState
from glassbox.core import HandoffIntent
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffProjectionRecord
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffSourceKind
from glassbox.core import OperatorQueueFamily
from glassbox.runtime.handoff_decisions import custody_action_state
from glassbox.runtime.handoff_decisions import safe_next_actions_for_decision
from glassbox.runtime.operator_queue_handoff_items import build_handoff_queue_items


def test_custody_action_state_names_dashboard_posture() -> None:
    awaiting = _record(HandoffCustodyState.IMPORTED_INSPECTED)
    accepted = _record(HandoffCustodyState.ACCEPTED_FOR_FOLLOW_UP)
    rejected = _record(HandoffCustodyState.REJECTED)
    archived = _record(HandoffCustodyState.ARCHIVED, archived=True)

    assert custody_action_state(awaiting) == "awaiting-recipient"
    assert custody_action_state(accepted) == "accepted-needs-follow-up"
    assert custody_action_state(rejected) == "rejected-needs-sender-review"
    assert custody_action_state(archived) == "archived-historical"


def test_handoff_queue_items_rank_custody_states() -> None:
    awaiting = _record(HandoffCustodyState.IMPORTED_INSPECTED)
    accepted = _record(HandoffCustodyState.ACCEPTED_FOR_FOLLOW_UP)
    rejected = _record(HandoffCustodyState.REJECTED)
    archived = _record(HandoffCustodyState.ARCHIVED, archived=True)

    queue = build_handoff_queue_items([awaiting, accepted, rejected, archived])

    assert [item.owner_label for item in queue] == [
        "Handoff awaiting recipient",
        "Accepted handoff",
        "Rejected handoff",
    ]
    assert queue[0].family == OperatorQueueFamily.REVIEW_BLOCKING
    assert queue[0].action_needed is True
    assert queue[0].blocking is True
    assert queue[1].family == OperatorQueueFamily.ADVISORY
    assert queue[2].family == OperatorQueueFamily.REVIEW_BLOCKING


def test_safe_next_actions_are_read_only_inspection_commands() -> None:
    record = _record(HandoffCustodyState.ACCEPTED)

    assert safe_next_actions_for_decision(record) == [
        f"glassbox handoff show {record.session_id} {record.package_id}",
        f"glassbox session status {record.source_id}",
    ]


def _record(
    custody_state: HandoffCustodyState,
    *,
    archived: bool = False,
) -> HandoffProjectionRecord:
    now = datetime(2026, 5, 18, tzinfo=UTC)
    return HandoffProjectionRecord(
        session_id="00000000-0000-0000-0000-000000000001",
        package_id=f"pkg-{custody_state.value}",
        source_kind=HandoffSourceKind.SESSION,
        source_id="00000000-0000-0000-0000-000000000002",
        package_kind=HandoffPackageKind.SESSION,
        intent=HandoffIntent.REVIEW_ONLY,
        package_digest="digest",
        compatibility_state=HandoffCompatibilityState.SUPPORTED,
        redaction_posture=HandoffRedactionPosture.REDACTED,
        custody_state=custody_state,
        follow_up_intent=HandoffIntent.REVIEW_ONLY,
        imported=True,
        archived=archived,
        created_at=now,
        updated_at=now,
        last_event_type="ImportedHandoffInspected",
        last_sequence=1,
    )
