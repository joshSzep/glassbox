"""Local pause-window helpers for long-running task work."""

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import Literal

from glassbox.core.events import EventEnvelope
from glassbox.core.events import PauseWindowCancelled
from glassbox.core.events import PauseWindowScheduled
from glassbox.core.events import PauseWindowTriggered
from glassbox.core.ids import BackgroundJobId
from glassbox.core.ids import PauseWindowId
from glassbox.core.ids import TaskCheckpointId
from glassbox.core.ids import TaskId
from glassbox.core.ids import new_pause_window_id
from glassbox.core.types import PauseWindowPolicy


@dataclass(frozen=True, slots=True)
class PauseWindow:
    """Active scheduled pause boundary reconstructed from canonical events."""

    pause_window_id: PauseWindowId
    policy: PauseWindowPolicy
    reason: str
    task_id: TaskId | None = None
    checkpoint_id: TaskCheckpointId | None = None
    pause_before: datetime | None = None


def schedule_pause_window(
    *,
    scope: Literal["session", "task"],
    policy: PauseWindowPolicy,
    reason: str,
    scheduled_by: str = "operator",
    task_id: TaskId | None = None,
    checkpoint_id: TaskCheckpointId | None = None,
    pause_before: datetime | None = None,
) -> PauseWindowScheduled:
    """Create canonical evidence for a local pause window."""

    if scope not in {"session", "task"}:
        raise ValueError("pause-window scope must be session or task")
    _validate_policy_shape(
        policy=policy,
        checkpoint_id=checkpoint_id,
        pause_before=pause_before,
    )
    return PauseWindowScheduled(
        pause_window_id=new_pause_window_id(),
        scope=scope,
        policy=policy,
        scheduled_by=scheduled_by,
        task_id=task_id,
        checkpoint_id=checkpoint_id,
        pause_before=pause_before,
        reason=reason,
    )


def cancel_pause_window(
    *,
    pause_window_id: PauseWindowId,
    task_id: TaskId | None,
    cancelled_by: str,
    reason: str,
) -> PauseWindowCancelled:
    """Create canonical evidence for manually overriding a pause window."""

    return PauseWindowCancelled(
        pause_window_id=pause_window_id,
        task_id=task_id,
        cancelled_by=cancelled_by,
        reason=reason,
    )


def active_pause_windows(
    events: list[EventEnvelope],
    *,
    task_id: TaskId,
) -> list[PauseWindow]:
    """Rebuild active task pause windows from canonical events."""

    scheduled: dict[PauseWindowId, PauseWindow] = {}
    inactive: set[PauseWindowId] = set()
    for event in events:
        payload = event.payload
        if isinstance(payload, PauseWindowScheduled):
            if payload.scope == "task" and payload.task_id != task_id:
                continue
            if payload.scope == "session" or payload.task_id == task_id:
                scheduled[payload.pause_window_id] = PauseWindow(
                    pause_window_id=payload.pause_window_id,
                    policy=payload.policy,
                    reason=payload.reason,
                    task_id=payload.task_id,
                    checkpoint_id=payload.checkpoint_id,
                    pause_before=payload.pause_before,
                )
        elif isinstance(payload, PauseWindowCancelled | PauseWindowTriggered):
            inactive.add(payload.pause_window_id)
    return [
        window for window_id, window in scheduled.items() if window_id not in inactive
    ]


def triggered_pause_window(
    windows: list[PauseWindow],
    *,
    now: datetime | None = None,
    before_risky_action: bool = False,
    completed_checkpoint_id: TaskCheckpointId | None = None,
) -> PauseWindow | None:
    """Return the first pause window that should stop work at this boundary."""

    timestamp = now or datetime.now(UTC)
    for window in windows:
        if (
            window.policy == PauseWindowPolicy.BEFORE_TIME
            and window.pause_before is not None
            and timestamp >= window.pause_before
        ):
            return window
        if (
            window.policy == PauseWindowPolicy.AFTER_CHECKPOINT
            and completed_checkpoint_id is not None
            and window.checkpoint_id == completed_checkpoint_id
        ):
            return window
        if (
            window.policy == PauseWindowPolicy.BEFORE_RISKY_ACTION
            and before_risky_action
        ):
            return window
    return None


def pause_window_triggered_event(
    window: PauseWindow,
    *,
    job_id: BackgroundJobId | None,
    triggered_at: datetime | None = None,
) -> PauseWindowTriggered:
    """Create durable stop evidence for a triggered pause window."""

    timestamp = triggered_at or datetime.now(UTC)
    return PauseWindowTriggered(
        pause_window_id=window.pause_window_id,
        scope="task" if window.task_id is not None else "session",
        policy=window.policy,
        task_id=window.task_id,
        job_id=job_id,
        checkpoint_id=window.checkpoint_id,
        triggered_at=timestamp,
        stop_reason=f"Pause window {window.policy.value} triggered: {window.reason}",
    )


def _validate_policy_shape(
    *,
    policy: PauseWindowPolicy,
    checkpoint_id: TaskCheckpointId | None,
    pause_before: datetime | None,
) -> None:
    if policy == PauseWindowPolicy.BEFORE_TIME and pause_before is None:
        raise ValueError("before_time pause windows require pause_before")
    if policy == PauseWindowPolicy.AFTER_CHECKPOINT and checkpoint_id is None:
        raise ValueError("after_checkpoint pause windows require checkpoint_id")


__all__ = [
    "PauseWindow",
    "active_pause_windows",
    "cancel_pause_window",
    "pause_window_triggered_event",
    "schedule_pause_window",
    "triggered_pause_window",
]
