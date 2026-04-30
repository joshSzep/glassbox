"""Tests for bounded continuation-window helpers."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

from glassbox.core import ApprovalDecision
from glassbox.core import BackgroundJobKind
from glassbox.core import BackgroundJobRecord
from glassbox.core import BackgroundJobState
from glassbox.core import new_background_job_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.runtime.continuation_windows import active_continuation_window_job
from glassbox.runtime.continuation_windows import approve_continuation_window
from glassbox.runtime.continuation_windows import continuation_window_from_job
from glassbox.runtime.continuation_windows import deny_continuation_window


def test_approved_continuation_window_carries_deadline_payload() -> None:
    task_id = new_task_id()
    now = datetime(2026, 4, 30, 12, tzinfo=UTC)

    approval = approve_continuation_window(
        task_id=task_id,
        minutes=10,
        requested_by="operator",
        decided_by="operator",
        reason="continue briefly",
        now=now,
    )

    assert approval.requested_event.requested_minutes == 10
    assert approval.resolved_event.decision == ApprovalDecision.APPROVED
    assert approval.resolved_event.approved_until == now + timedelta(minutes=10)
    assert approval.payload["continuation_window_minutes"] == 10


def test_denied_continuation_window_does_not_create_deadline() -> None:
    denial = deny_continuation_window(
        task_id=new_task_id(),
        minutes=5,
        requested_by="operator",
        decided_by="reviewer",
        reason="too risky",
    )

    assert denial.requested_event.requested_minutes == 5
    assert denial.resolved_event.decision == ApprovalDecision.DENIED
    assert denial.resolved_event.approved_until is None


def test_active_window_detection_ignores_expired_and_completed_jobs() -> None:
    task_id = new_task_id()
    now = datetime(2026, 4, 30, 12, tzinfo=UTC)
    active = _job(
        task_id=task_id,
        state=BackgroundJobState.QUEUED,
        approved_until=now + timedelta(minutes=5),
    )
    expired = _job(
        task_id=task_id,
        state=BackgroundJobState.QUEUED,
        approved_until=now - timedelta(minutes=1),
    )
    completed = _job(
        task_id=task_id,
        state=BackgroundJobState.COMPLETED,
        approved_until=now + timedelta(minutes=5),
    )

    assert (
        active_continuation_window_job(
            [expired, completed, active],
            task_id=task_id,
            now=now,
        )
        == active
    )
    assert continuation_window_from_job(active) is not None


def test_continuation_window_rejects_unbounded_minutes() -> None:
    with pytest.raises(ValueError, match="continuation window minutes"):
        approve_continuation_window(
            task_id=new_task_id(),
            minutes=0,
            requested_by="operator",
            decided_by="operator",
            reason=None,
        )


def _job(
    *,
    task_id,
    state: BackgroundJobState,
    approved_until: datetime,
) -> BackgroundJobRecord:
    return BackgroundJobRecord(
        job_id=new_background_job_id(),
        session_id=new_session_id(),
        state=state,
        kind=BackgroundJobKind.MUTATING_CONTINUATION,
        job_type="task-continuation-step",
        title="Continue task",
        requested_by="operator",
        payload={
            "continuation_window_approval_id": ("00000000-0000-0000-0000-000000000111"),
            "continuation_window_approved_until": approved_until.isoformat(),
            "continuation_window_minutes": 5,
        },
        priority=0,
        task_id=task_id,
        created_at=approved_until,
        updated_at=approved_until,
        last_sequence=1,
    )
