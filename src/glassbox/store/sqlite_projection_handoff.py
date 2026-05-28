"""Handoff workflow projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import HandoffArchived
from glassbox.core.events import HandoffCustodyAccepted
from glassbox.core.events import HandoffCustodyProposed
from glassbox.core.events import HandoffCustodyRejected
from glassbox.core.events import HandoffPackageCreated
from glassbox.core.events import ImportedHandoffAcceptedForFollowUp
from glassbox.core.events import ImportedHandoffInspected
from glassbox.core.types import HandoffCustodyState
from glassbox.store.sqlite_projection_handoff_mutations import upsert_handoff_projection


def _apply_handoff_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, HandoffPackageCreated):
        upsert_handoff_projection(
            connection,
            event,
            package_id=payload.package_id,
            source_kind=payload.source_kind.value,
            source_id=payload.source_id,
            task_id=_optional_str(payload.task_id),
            changeset_id=_optional_str(payload.changeset_id),
            package_kind=payload.package_kind.value,
            intent=payload.intent.value,
            artifact_id=_optional_str(payload.artifact_id),
            package_digest=payload.package_digest,
            compatibility_state=payload.compatibility_state.value,
            redaction_posture=payload.redaction_posture.value,
            local_only_count=payload.local_only_count,
            custody_state=HandoffCustodyState.CREATED.value,
            expected_custodian=payload.expected_custodian,
            exported_by=payload.exported_by,
            note=payload.note,
        )
        return
    if isinstance(payload, HandoffCustodyProposed):
        upsert_handoff_projection(
            connection,
            event,
            package_id=payload.package_id,
            source_kind=payload.source_kind.value,
            task_id=_optional_str(payload.task_id),
            changeset_id=_optional_str(payload.changeset_id),
            intent=payload.intent.value,
            custody_state=HandoffCustodyState.PROPOSED.value,
            expected_custodian=payload.proposed_custodian,
            current_custodian=payload.proposed_custodian,
            decision_by=payload.proposed_by,
            decision_reason=payload.reason,
        )
        return
    if isinstance(payload, HandoffCustodyAccepted):
        upsert_handoff_projection(
            connection,
            event,
            package_id=payload.package_id,
            task_id=_optional_str(payload.task_id),
            changeset_id=_optional_str(payload.changeset_id),
            custody_state=HandoffCustodyState.ACCEPTED.value,
            current_custodian=payload.accepted_by,
            decision_by=payload.accepted_by,
            decision_reason=payload.reason,
            follow_up_intent=(
                payload.follow_up_intent.value if payload.follow_up_intent else None
            ),
            safe_next_actions=payload.safe_next_actions,
        )
        return
    if isinstance(payload, HandoffCustodyRejected):
        upsert_handoff_projection(
            connection,
            event,
            package_id=payload.package_id,
            task_id=_optional_str(payload.task_id),
            changeset_id=_optional_str(payload.changeset_id),
            custody_state=HandoffCustodyState.REJECTED.value,
            decision_by=payload.rejected_by,
            decision_reason=payload.reason,
            safe_next_actions=payload.safe_next_actions,
        )
        return
    if isinstance(payload, ImportedHandoffInspected):
        upsert_handoff_projection(
            connection,
            event,
            package_id=payload.package_id,
            source_kind=payload.source_kind.value,
            source_id=payload.source_id,
            task_id=_optional_str(payload.task_id),
            changeset_id=_optional_str(payload.changeset_id),
            package_kind=payload.package_kind.value if payload.package_kind else None,
            intent=payload.intent.value if payload.intent else None,
            package_digest=payload.package_digest,
            compatibility_state=payload.compatibility_state.value,
            redaction_posture=payload.redaction_posture.value,
            local_only_count=payload.local_only_count,
            custody_state=HandoffCustodyState.IMPORTED_INSPECTED.value,
            decision_by=payload.inspected_by,
            safe_next_actions=payload.safe_next_actions,
            note=payload.note,
            imported=True,
        )
        return
    if isinstance(payload, ImportedHandoffAcceptedForFollowUp):
        upsert_handoff_projection(
            connection,
            event,
            package_id=payload.package_id,
            task_id=_optional_str(payload.task_id),
            changeset_id=_optional_str(payload.changeset_id),
            custody_state=HandoffCustodyState.ACCEPTED_FOR_FOLLOW_UP.value,
            current_custodian=payload.accepted_by,
            decision_by=payload.accepted_by,
            decision_reason=payload.reason,
            follow_up_intent=payload.follow_up_intent.value,
            safe_next_actions=payload.safe_next_actions,
            imported=True,
        )
        return
    if isinstance(payload, HandoffArchived):
        upsert_handoff_projection(
            connection,
            event,
            package_id=payload.package_id,
            task_id=_optional_str(payload.task_id),
            changeset_id=_optional_str(payload.changeset_id),
            custody_state=HandoffCustodyState.ARCHIVED.value,
            decision_by=payload.archived_by,
            decision_reason=payload.reason,
            archived=True,
        )


def _optional_str(value: object | None) -> str | None:
    return str(value) if value is not None else None


__all__ = ["_apply_handoff_projection"]
