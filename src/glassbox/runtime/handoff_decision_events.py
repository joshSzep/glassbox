"""Event builders for local handoff custody decisions."""

from collections.abc import Sequence
from uuid import UUID

from glassbox.core import ChangesetId
from glassbox.core import EventEnvelope
from glassbox.core import HandoffArchived
from glassbox.core import HandoffCustodyAccepted
from glassbox.core import HandoffCustodyRejected
from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.core import ImportedHandoffAcceptedForFollowUp
from glassbox.core import SessionId
from glassbox.core import TaskId


def build_accept_event(
    record: HandoffProjectionRecord,
    *,
    session_id: SessionId,
    package_id: str,
    accepted_by: str,
    reason: str | None,
    follow_up_intent: HandoffIntent | None,
    safe_next_actions: Sequence[str],
) -> EventEnvelope:
    """Build the accept or imported-follow-up custody event."""

    effective_follow_up = follow_up_intent or record.intent or HandoffIntent.REVIEW_ONLY
    payload = (
        ImportedHandoffAcceptedForFollowUp(
            package_id=package_id,
            accepted_by=accepted_by,
            follow_up_intent=effective_follow_up,
            reason=reason,
            safe_next_actions=list(safe_next_actions),
            task_id=_optional_uuid(record.task_id),
            changeset_id=_optional_uuid(record.changeset_id),
        )
        if record.imported
        else HandoffCustodyAccepted(
            package_id=package_id,
            accepted_by=accepted_by,
            reason=reason,
            follow_up_intent=effective_follow_up,
            safe_next_actions=list(safe_next_actions),
            task_id=_optional_uuid(record.task_id),
            changeset_id=_optional_uuid(record.changeset_id),
        )
    )
    return EventEnvelope(session_id=session_id, sequence=0, payload=payload)


def build_reject_event(
    record: HandoffProjectionRecord,
    *,
    session_id: SessionId,
    package_id: str,
    rejected_by: str,
    reason: str,
    safe_next_actions: Sequence[str],
) -> EventEnvelope:
    """Build the custody rejection event."""

    return EventEnvelope(
        session_id=session_id,
        sequence=0,
        payload=HandoffCustodyRejected(
            package_id=package_id,
            rejected_by=rejected_by,
            reason=reason,
            safe_next_actions=list(safe_next_actions),
            task_id=_optional_uuid(record.task_id),
            changeset_id=_optional_uuid(record.changeset_id),
        ),
    )


def build_archive_event(
    record: HandoffProjectionRecord,
    *,
    session_id: SessionId,
    package_id: str,
    archived_by: str,
    reason: str,
) -> EventEnvelope:
    """Build the handoff archive event."""

    return EventEnvelope(
        session_id=session_id,
        sequence=0,
        payload=HandoffArchived(
            package_id=package_id,
            archived_by=archived_by,
            reason=reason,
            task_id=_optional_uuid(record.task_id),
            changeset_id=_optional_uuid(record.changeset_id),
        ),
    )


def _optional_uuid(value: str | None) -> TaskId | ChangesetId | None:
    if value is None:
        return None
    return UUID(value)


__all__ = [
    "build_accept_event",
    "build_archive_event",
    "build_reject_event",
]
