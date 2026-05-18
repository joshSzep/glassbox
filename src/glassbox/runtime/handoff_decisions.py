"""Durable local custody decisions for handoff packages."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

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
from glassbox.core.types_handoff import HandoffCustodyState
from glassbox.core.types_handoff import HandoffSourceKind


class HandoffDecisionRepository(Protocol):
    """Minimal repository surface needed to record custody decisions."""

    def get_handoff(
        self,
        session_id: SessionId,
        package_id: str,
    ) -> HandoffProjectionRecord | None: ...

    def append_event(self, event: EventEnvelope) -> EventEnvelope: ...


class HandoffDecisionResult(BaseModel):
    """Result returned by CLI and API custody decision actions."""

    model_config = ConfigDict(extra="forbid")

    record: HandoffProjectionRecord
    event_type: str = Field(min_length=1, max_length=120)
    non_claims: list[str] = Field(default_factory=list, max_length=20)


def accept_handoff_custody(
    repository: HandoffDecisionRepository,
    *,
    session_id: SessionId,
    package_id: str,
    accepted_by: str = "operator",
    reason: str | None = None,
    follow_up_intent: HandoffIntent | None = None,
    safe_next_actions: Sequence[str] = (),
) -> HandoffDecisionResult:
    """Accept local custody or imported follow-up for one handoff package."""

    record = _require_handoff(repository, session_id, package_id)
    effective_follow_up = follow_up_intent or record.intent or HandoffIntent.REVIEW_ONLY
    if record.imported:
        payload = ImportedHandoffAcceptedForFollowUp(
            package_id=package_id,
            accepted_by=accepted_by,
            follow_up_intent=effective_follow_up,
            reason=reason,
            safe_next_actions=list(safe_next_actions),
            task_id=_optional_uuid(record.task_id),
            changeset_id=_optional_uuid(record.changeset_id),
        )
    else:
        payload = HandoffCustodyAccepted(
            package_id=package_id,
            accepted_by=accepted_by,
            reason=reason,
            follow_up_intent=effective_follow_up,
            safe_next_actions=list(safe_next_actions),
            task_id=_optional_uuid(record.task_id),
            changeset_id=_optional_uuid(record.changeset_id),
        )
    stored = repository.append_event(
        EventEnvelope(session_id=session_id, sequence=0, payload=payload)
    )
    return _result(repository, session_id, package_id, stored.event_type)


def reject_handoff_custody(
    repository: HandoffDecisionRepository,
    *,
    session_id: SessionId,
    package_id: str,
    rejected_by: str = "operator",
    reason: str,
    safe_next_actions: Sequence[str] = (),
) -> HandoffDecisionResult:
    """Reject local custody while preserving the package inspection record."""

    record = _require_handoff(repository, session_id, package_id)
    stored = repository.append_event(
        EventEnvelope(
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
    )
    return _result(repository, session_id, package_id, stored.event_type)


def archive_handoff(
    repository: HandoffDecisionRepository,
    *,
    session_id: SessionId,
    package_id: str,
    archived_by: str = "operator",
    reason: str,
) -> HandoffDecisionResult:
    """Archive a handoff as historical local workflow evidence."""

    record = _require_handoff(repository, session_id, package_id)
    stored = repository.append_event(
        EventEnvelope(
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
    )
    return _result(repository, session_id, package_id, stored.event_type)


def _require_handoff(
    repository: HandoffDecisionRepository,
    session_id: SessionId,
    package_id: str,
) -> HandoffProjectionRecord:
    record = repository.get_handoff(session_id, package_id)
    if record is None:
        raise ValueError(
            f"unknown handoff package for session {session_id}: {package_id}"
        )
    return record


def _result(
    repository: HandoffDecisionRepository,
    session_id: SessionId,
    package_id: str,
    event_type: str,
) -> HandoffDecisionResult:
    record = _require_handoff(repository, session_id, package_id)
    return HandoffDecisionResult(
        record=record,
        event_type=event_type,
        non_claims=[
            "custody decision is local workflow metadata, not authorization",
            (
                "custody decision is not review, verification, release, "
                "or publication approval"
            ),
            "custody decision does not transfer runtime ownership",
        ],
    )


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


def _optional_uuid(value: str | None) -> TaskId | ChangesetId | None:
    if value is None:
        return None
    return UUID(value)


__all__ = [
    "HandoffDecisionRepository",
    "HandoffDecisionResult",
    "accept_handoff_custody",
    "archive_handoff",
    "custody_action_state",
    "reject_handoff_custody",
    "safe_next_actions_for_decision",
]
