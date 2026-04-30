"""Bounded continuation-window helpers for long-running tasks."""

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from uuid import UUID

from glassbox.core.events import ContinuationWindowExpired
from glassbox.core.events import ContinuationWindowRequested
from glassbox.core.events import ContinuationWindowResolved
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import TaskCheckpointId
from glassbox.core.ids import TaskId
from glassbox.core.ids import new_approval_id
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import BackgroundJobState

MAX_CONTINUATION_WINDOW_MINUTES = 24 * 60


@dataclass(frozen=True, slots=True)
class ContinuationWindowApproval:
    """Canonical approval evidence and job payload for one continuation window."""

    approval_id: ApprovalId
    approved_until: datetime
    requested_event: ContinuationWindowRequested
    resolved_event: ContinuationWindowResolved
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class ContinuationWindowDenial:
    """Canonical denial evidence for one requested continuation window."""

    approval_id: ApprovalId
    requested_event: ContinuationWindowRequested
    resolved_event: ContinuationWindowResolved


@dataclass(frozen=True, slots=True)
class ContinuationWindowState:
    """Parsed continuation-window authority from a background job payload."""

    approval_id: ApprovalId
    approved_until: datetime
    approved_minutes: int
    checkpoint_id: TaskCheckpointId | None = None

    @property
    def expired_at(self) -> datetime:
        return self.approved_until


def approve_continuation_window(
    *,
    task_id: TaskId,
    minutes: int,
    requested_by: str,
    decided_by: str,
    reason: str | None,
    checkpoint_id: TaskCheckpointId | None = None,
    now: datetime | None = None,
) -> ContinuationWindowApproval:
    """Create request/resolution evidence and payload for an approved window."""

    _validate_minutes(minutes)
    timestamp = now or datetime.now(UTC)
    approved_until = timestamp + timedelta(minutes=minutes)
    approval_id = new_approval_id()
    requested = ContinuationWindowRequested(
        approval_id=approval_id,
        scope="task",
        task_id=task_id,
        checkpoint_id=checkpoint_id,
        requested_minutes=minutes,
        requested_by=requested_by,
        reason=reason,
    )
    resolved = ContinuationWindowResolved(
        approval_id=approval_id,
        task_id=task_id,
        checkpoint_id=checkpoint_id,
        decision=ApprovalDecision.APPROVED,
        decided_by=decided_by,
        approved_minutes=minutes,
        approved_until=approved_until,
        reason=reason,
    )
    payload: dict[str, object] = {
        "continuation_window_approval_id": str(approval_id),
        "continuation_window_approved_until": approved_until.isoformat(),
        "continuation_window_minutes": minutes,
    }
    if checkpoint_id is not None:
        payload["continuation_window_checkpoint_id"] = str(checkpoint_id)
    return ContinuationWindowApproval(
        approval_id=approval_id,
        approved_until=approved_until,
        requested_event=requested,
        resolved_event=resolved,
        payload=payload,
    )


def deny_continuation_window(
    *,
    task_id: TaskId,
    minutes: int,
    requested_by: str,
    decided_by: str,
    reason: str | None,
    checkpoint_id: TaskCheckpointId | None = None,
) -> ContinuationWindowDenial:
    """Create request/resolution evidence for a denied continuation window."""

    _validate_minutes(minutes)
    approval_id = new_approval_id()
    requested = ContinuationWindowRequested(
        approval_id=approval_id,
        scope="task",
        task_id=task_id,
        checkpoint_id=checkpoint_id,
        requested_minutes=minutes,
        requested_by=requested_by,
        reason=reason,
    )
    resolved = ContinuationWindowResolved(
        approval_id=approval_id,
        task_id=task_id,
        checkpoint_id=checkpoint_id,
        decision=ApprovalDecision.DENIED,
        decided_by=decided_by,
        reason=reason,
    )
    return ContinuationWindowDenial(
        approval_id=approval_id,
        requested_event=requested,
        resolved_event=resolved,
    )


def continuation_window_from_job(
    job: BackgroundJobRecord,
) -> ContinuationWindowState | None:
    """Parse continuation-window authority from a projected background job."""

    approval_id = job.payload.get("continuation_window_approval_id")
    approved_until = job.payload.get("continuation_window_approved_until")
    minutes = job.payload.get("continuation_window_minutes")
    checkpoint_id = job.payload.get("continuation_window_checkpoint_id")
    if not isinstance(approval_id, str) or not isinstance(approved_until, str):
        return None
    if not isinstance(minutes, int):
        return None
    return ContinuationWindowState(
        approval_id=UUID(approval_id),
        approved_until=datetime.fromisoformat(approved_until),
        approved_minutes=minutes,
        checkpoint_id=UUID(checkpoint_id) if isinstance(checkpoint_id, str) else None,
    )


def active_continuation_window_job(
    jobs: list[BackgroundJobRecord],
    *,
    task_id: TaskId,
    now: datetime | None = None,
) -> BackgroundJobRecord | None:
    """Return an active unexpired continuation-window job for a task, if any."""

    timestamp = now or datetime.now(UTC)
    active_states = {
        BackgroundJobState.QUEUED,
        BackgroundJobState.CLAIMED,
        BackgroundJobState.RUNNING,
        BackgroundJobState.PAUSED,
    }
    for job in jobs:
        if job.task_id != task_id or job.job_type != "task-continuation-step":
            continue
        if job.state not in active_states:
            continue
        window = continuation_window_from_job(job)
        if window is not None and window.approved_until > timestamp:
            return job
    return None


def continuation_window_expired_event(
    job: BackgroundJobRecord,
    window: ContinuationWindowState,
) -> ContinuationWindowExpired:
    """Create durable expiry evidence for an expired continuation window."""

    return ContinuationWindowExpired(
        approval_id=window.approval_id,
        scope="task",
        task_id=job.task_id,
        job_id=job.job_id,
        checkpoint_id=window.checkpoint_id,
        expired_at=window.expired_at,
        stop_reason=(
            "Continuation window expired at "
            f"{window.expired_at.isoformat()} before the job could continue."
        ),
    )


def _validate_minutes(minutes: int) -> None:
    if minutes < 1 or minutes > MAX_CONTINUATION_WINDOW_MINUTES:
        raise ValueError(
            "continuation window minutes must be between 1 and "
            f"{MAX_CONTINUATION_WINDOW_MINUTES}"
        )


__all__ = [
    "ContinuationWindowApproval",
    "ContinuationWindowDenial",
    "ContinuationWindowState",
    "active_continuation_window_job",
    "approve_continuation_window",
    "continuation_window_expired_event",
    "continuation_window_from_job",
    "deny_continuation_window",
]
