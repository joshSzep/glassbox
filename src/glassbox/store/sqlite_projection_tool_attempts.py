"""Tool-attempt projection handlers for SQLite."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.types import ToolAttemptStatus

_TERMINAL_ATTEMPT_STATUSES = {
    ToolAttemptStatus.SUCCEEDED,
    ToolAttemptStatus.FAILED,
    ToolAttemptStatus.CANCELLED,
    ToolAttemptStatus.STALE,
    ToolAttemptStatus.ABANDONED,
}


def _apply_tool_attempt_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if not isinstance(payload, ToolAttemptHeartbeat):
        return

    started_at = event.created_at.isoformat()
    completed_at = (
        event.created_at.isoformat()
        if payload.status in _TERMINAL_ATTEMPT_STATUSES
        else None
    )
    connection.execute(
        """
        insert into tool_attempts (
            tool_attempt_id,
            session_id,
            turn_id,
            tool_call_id,
            task_id,
            tool_name,
            status,
            message,
            started_at,
            last_heartbeat_at,
            heartbeat_expires_at,
            completed_at,
            completed_units,
            total_units,
            output_artifact_id,
            safe_to_retry,
            retry_reason,
            last_sequence
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id, tool_attempt_id) do update set
            turn_id = excluded.turn_id,
            tool_call_id = coalesce(excluded.tool_call_id, tool_attempts.tool_call_id),
            task_id = coalesce(excluded.task_id, tool_attempts.task_id),
            tool_name = excluded.tool_name,
            status = excluded.status,
            message = coalesce(excluded.message, tool_attempts.message),
            last_heartbeat_at = excluded.last_heartbeat_at,
            heartbeat_expires_at = coalesce(
                excluded.heartbeat_expires_at,
                tool_attempts.heartbeat_expires_at
            ),
            completed_at = coalesce(excluded.completed_at, tool_attempts.completed_at),
            completed_units = coalesce(
                excluded.completed_units,
                tool_attempts.completed_units
            ),
            total_units = coalesce(excluded.total_units, tool_attempts.total_units),
            output_artifact_id = coalesce(
                excluded.output_artifact_id,
                tool_attempts.output_artifact_id
            ),
            safe_to_retry = coalesce(
                excluded.safe_to_retry,
                tool_attempts.safe_to_retry
            ),
            retry_reason = coalesce(excluded.retry_reason, tool_attempts.retry_reason),
            last_sequence = excluded.last_sequence
        """,
        (
            str(payload.tool_attempt_id),
            str(event.session_id),
            str(payload.turn_id),
            _optional_text(payload.tool_call_id),
            _optional_text(payload.task_id),
            payload.tool_name,
            payload.status.value,
            payload.message,
            started_at,
            event.created_at.isoformat(),
            _optional_datetime(payload.heartbeat_expires_at),
            completed_at,
            payload.completed_units,
            payload.total_units,
            _optional_text(payload.output_artifact_id),
            _optional_bool(payload.safe_to_retry),
            payload.retry_reason,
            event.sequence,
        ),
    )


def _optional_text(value: object | None) -> str | None:
    return None if value is None else str(value)


def _optional_bool(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _optional_datetime(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


__all__ = ["_apply_tool_attempt_projection"]
