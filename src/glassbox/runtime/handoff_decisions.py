"""Durable local custody decision facade for handoff packages."""

from collections.abc import Sequence

from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.core import SessionId
from glassbox.runtime.handoff_decision_actions import custody_action_state
from glassbox.runtime.handoff_decision_actions import safe_next_actions_for_decision
from glassbox.runtime.handoff_decision_events import build_accept_event
from glassbox.runtime.handoff_decision_events import build_archive_event
from glassbox.runtime.handoff_decision_events import build_reject_event
from glassbox.runtime.handoff_decision_models import HandoffDecisionRepository
from glassbox.runtime.handoff_decision_models import HandoffDecisionResult


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
    stored = repository.append_event(
        build_accept_event(
            record,
            session_id=session_id,
            package_id=package_id,
            accepted_by=accepted_by,
            reason=reason,
            follow_up_intent=follow_up_intent,
            safe_next_actions=safe_next_actions,
        )
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
        build_reject_event(
            record,
            session_id=session_id,
            package_id=package_id,
            rejected_by=rejected_by,
            reason=reason,
            safe_next_actions=safe_next_actions,
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
        build_archive_event(
            record,
            session_id=session_id,
            package_id=package_id,
            archived_by=archived_by,
            reason=reason,
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


__all__ = [
    "HandoffDecisionRepository",
    "HandoffDecisionResult",
    "accept_handoff_custody",
    "archive_handoff",
    "custody_action_state",
    "reject_handoff_custody",
    "safe_next_actions_for_decision",
]
