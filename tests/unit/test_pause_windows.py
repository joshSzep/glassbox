"""Tests for local pause-window reconstruction."""

from datetime import UTC
from datetime import datetime

from glassbox.core import EventEnvelope
from glassbox.core import PauseWindowCancelled
from glassbox.core import PauseWindowPolicy
from glassbox.core import PauseWindowScheduled
from glassbox.core import PauseWindowTriggered
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.runtime.pause_windows import active_pause_windows
from glassbox.runtime.pause_windows import cancel_pause_window
from glassbox.runtime.pause_windows import pause_window_triggered_event
from glassbox.runtime.pause_windows import schedule_pause_window
from glassbox.runtime.pause_windows import triggered_pause_window


def test_pause_window_triggers_before_time() -> None:
    task_id = new_task_id()
    scheduled = schedule_pause_window(
        scope="task",
        task_id=task_id,
        policy=PauseWindowPolicy.BEFORE_TIME,
        pause_before=datetime(2026, 4, 30, 12, tzinfo=UTC),
        reason="pause before local stop window",
    )

    windows = active_pause_windows(
        [_envelope(task_id, scheduled)],
        task_id=task_id,
    )
    triggered = triggered_pause_window(
        windows,
        now=datetime(2026, 4, 30, 12, 1, tzinfo=UTC),
    )

    assert triggered is not None
    event = pause_window_triggered_event(triggered, job_id=None)
    assert isinstance(event, PauseWindowTriggered)
    assert event.policy == PauseWindowPolicy.BEFORE_TIME


def test_cancelled_pause_window_is_not_active() -> None:
    task_id = new_task_id()
    scheduled = schedule_pause_window(
        scope="task",
        task_id=task_id,
        policy=PauseWindowPolicy.BEFORE_RISKY_ACTION,
        reason="inspect before mutation",
    )
    cancelled = cancel_pause_window(
        pause_window_id=scheduled.pause_window_id,
        task_id=task_id,
        cancelled_by="operator",
        reason="manual override",
    )

    assert isinstance(cancelled, PauseWindowCancelled)
    assert (
        active_pause_windows(
            [_envelope(task_id, scheduled), _envelope(task_id, cancelled)],
            task_id=task_id,
        )
        == []
    )


def test_pause_window_triggers_before_risky_action() -> None:
    task_id = new_task_id()
    scheduled = schedule_pause_window(
        scope="task",
        task_id=task_id,
        policy=PauseWindowPolicy.BEFORE_RISKY_ACTION,
        reason="operator wants review",
    )

    triggered = triggered_pause_window(
        active_pause_windows([_envelope(task_id, scheduled)], task_id=task_id),
        before_risky_action=True,
    )

    assert triggered is not None
    assert triggered.pause_window_id == scheduled.pause_window_id


def test_pause_window_triggers_after_checkpoint() -> None:
    task_id = new_task_id()
    checkpoint_id = new_task_checkpoint_id()
    scheduled = schedule_pause_window(
        scope="task",
        task_id=task_id,
        policy=PauseWindowPolicy.AFTER_CHECKPOINT,
        checkpoint_id=checkpoint_id,
        reason="pause after checkpoint",
    )

    triggered = triggered_pause_window(
        active_pause_windows([_envelope(task_id, scheduled)], task_id=task_id),
        completed_checkpoint_id=checkpoint_id,
    )

    assert triggered is not None
    assert triggered.checkpoint_id == checkpoint_id


def _envelope(task_id, payload: PauseWindowScheduled | PauseWindowCancelled):
    return EventEnvelope(
        session_id=new_session_id(),
        sequence=0,
        payload=payload,
        created_at=datetime.now(UTC),
    )
