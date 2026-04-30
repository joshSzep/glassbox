"""Derived long-running cockpit summaries."""

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from typing import Literal

from glassbox.core.events import EventEnvelope
from glassbox.core.models import LongRunStatusRecord
from glassbox.core.models import SessionRecord
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import ToolAttemptRecord
from glassbox.core.types import ToolAttemptStatus

_ACTIVE_ATTEMPT_STATUSES = {
    ToolAttemptStatus.STARTED,
    ToolAttemptStatus.RUNNING,
    ToolAttemptStatus.WAITING,
}
_STUCK_ATTEMPT_STATUSES = {
    ToolAttemptStatus.STALE,
    ToolAttemptStatus.FAILED,
}
_TERMINAL_SESSION_STATUSES = {"completed", "cancelled", "failed"}
LongRunState = Literal["healthy", "idle", "paused", "stale", "stuck", "completed"]


def build_long_run_status(
    record: SessionRecord,
    *,
    status: str,
    events: Sequence[EventEnvelope],
    latest_checkpoint: TaskCheckpointRecord | None,
    recent_tool_attempts: Sequence[ToolAttemptRecord],
    now: datetime | None = None,
) -> LongRunStatusRecord:
    """Build a compact operator-facing long-run status from durable evidence."""

    current_time = _aware(now or datetime.now(UTC))
    last_event = events[-1] if events else None
    current_attempt = _current_attempt(recent_tool_attempts)
    heartbeat_at = (
        _aware(current_attempt.last_heartbeat_at)
        if current_attempt is not None and current_attempt.last_heartbeat_at is not None
        else None
    )
    heartbeat_expires_at = (
        _aware(current_attempt.heartbeat_expires_at)
        if (
            current_attempt is not None
            and current_attempt.heartbeat_expires_at is not None
        )
        else None
    )
    heartbeat_age_seconds = (
        _elapsed_seconds(heartbeat_at, current_time) if heartbeat_at else None
    )
    state, stuck_reason = _classify_state(
        status,
        current_attempt=current_attempt,
        heartbeat_expires_at=heartbeat_expires_at,
        now=current_time,
    )

    return LongRunStatusRecord(
        state=state,
        current_phase=_current_phase(latest_checkpoint, current_attempt),
        last_event_type=last_event.event_type if last_event else None,
        last_event_sequence=last_event.sequence if last_event else None,
        last_event_at=last_event.created_at if last_event else None,
        current_attempt_id=(
            current_attempt.tool_attempt_id if current_attempt is not None else None
        ),
        current_attempt_tool_name=(
            current_attempt.tool_name if current_attempt is not None else None
        ),
        current_attempt_status=(
            current_attempt.status.value if current_attempt is not None else None
        ),
        heartbeat_at=heartbeat_at,
        heartbeat_expires_at=heartbeat_expires_at,
        heartbeat_age_seconds=heartbeat_age_seconds,
        elapsed_seconds=_elapsed_seconds(_aware(record.created_at), current_time),
        stuck_reason=stuck_reason,
        progress_summary=_progress_summary(
            status,
            latest_checkpoint=latest_checkpoint,
            current_attempt=current_attempt,
            state=state,
            heartbeat_age_seconds=heartbeat_age_seconds,
        ),
    )


def _current_attempt(
    attempts: Sequence[ToolAttemptRecord],
) -> ToolAttemptRecord | None:
    for attempt in attempts:
        if attempt.status in _ACTIVE_ATTEMPT_STATUSES:
            return attempt
    return attempts[0] if attempts else None


def _classify_state(
    status: str,
    *,
    current_attempt: ToolAttemptRecord | None,
    heartbeat_expires_at: datetime | None,
    now: datetime,
) -> tuple[LongRunState, str | None]:
    if current_attempt is not None:
        if current_attempt.status in _STUCK_ATTEMPT_STATUSES:
            return "stuck", f"tool attempt is {current_attempt.status.value}"
        if heartbeat_expires_at is not None and heartbeat_expires_at <= now:
            return "stale", "tool attempt heartbeat expired"
        if current_attempt.status == ToolAttemptStatus.WAITING:
            return "paused", "tool attempt is waiting"

    if status in {"awaiting_approval", "awaiting_user_input"}:
        return "paused", f"session is {status}"
    if status == "running":
        return "healthy", None
    if status in _TERMINAL_SESSION_STATUSES:
        return "completed", None
    return "idle", None


def _current_phase(
    checkpoint: TaskCheckpointRecord | None,
    attempt: ToolAttemptRecord | None,
) -> str | None:
    if checkpoint is not None and checkpoint.current_phase is not None:
        return checkpoint.current_phase.value
    if attempt is not None:
        return f"tool:{attempt.tool_name}"
    return None


def _progress_summary(
    status: str,
    *,
    latest_checkpoint: TaskCheckpointRecord | None,
    current_attempt: ToolAttemptRecord | None,
    state: str,
    heartbeat_age_seconds: int | None,
) -> str:
    if current_attempt is not None:
        detail = current_attempt.message or current_attempt.status.value
        if heartbeat_age_seconds is not None:
            detail += f"; heartbeat {heartbeat_age_seconds}s ago"
        return f"{current_attempt.tool_name}: {detail}"
    if latest_checkpoint is not None:
        return f"{latest_checkpoint.objective}; next: {latest_checkpoint.next_action}"
    if state == "completed":
        return f"session {status}"
    if state == "paused":
        return f"session {status}"
    return "waiting for the next durable progress event"


def _elapsed_seconds(start: datetime, end: datetime) -> int:
    return max(int((end - _aware(start)).total_seconds()), 0)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


__all__ = ["build_long_run_status"]
