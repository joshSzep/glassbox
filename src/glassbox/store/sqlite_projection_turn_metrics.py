"""Turn-metrics projection handlers for the SQLite-backed event store."""

import sqlite3
from datetime import datetime

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelCallCompleted
from glassbox.core.events import ModelCallStarted
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId


def _ensure_turn_metrics_row(
    connection: sqlite3.Connection,
    session_id: SessionId,
    turn_id: TurnId,
    *,
    started_at: datetime | None = None,
) -> None:
    connection.execute(
        """
        insert into turn_metrics (
            session_id,
            turn_id,
            started_at,
            completed_at,
            turn_duration_ms,
            model_call_count,
            model_duration_ms_total,
            model_input_tokens_total,
            model_output_tokens_total,
            tool_call_count,
            tool_duration_ms_total,
            succeeded_tool_call_count,
            failed_tool_call_count
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id, turn_id) do update set
            started_at = coalesce(turn_metrics.started_at, excluded.started_at)
        """,
        (
            str(session_id),
            str(turn_id),
            started_at.isoformat() if started_at is not None else None,
            None,
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ),
    )


def _apply_turn_metrics_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    turn_id = event.turn_id
    if turn_id is None:
        return

    payload = event.payload

    if isinstance(payload, TurnStarted):
        _ensure_turn_metrics_row(
            connection,
            event.session_id,
            turn_id,
            started_at=event.created_at,
        )
        return

    _ensure_turn_metrics_row(connection, event.session_id, turn_id)

    if isinstance(payload, ModelCallStarted):
        return

    if isinstance(payload, ModelCallCompleted):
        connection.execute(
            """
            update turn_metrics
            set
                model_call_count = model_call_count + 1,
                model_duration_ms_total = model_duration_ms_total + ?,
                model_input_tokens_total = model_input_tokens_total + ?,
                model_output_tokens_total = model_output_tokens_total + ?
            where session_id = ? and turn_id = ?
            """,
            (
                payload.duration_ms,
                payload.input_tokens or 0,
                payload.output_tokens or 0,
                str(event.session_id),
                str(turn_id),
            ),
        )
        return

    if isinstance(payload, ToolExecutionStarted):
        connection.execute(
            """
            update turn_metrics
            set tool_call_count = tool_call_count + 1
            where session_id = ? and turn_id = ?
            """,
            (str(event.session_id), str(turn_id)),
        )
        return

    if isinstance(payload, ToolExecutionCompleted):
        started_at_row = connection.execute(
            """
            select started_at from tool_calls
            where session_id = ? and tool_call_id = ?
            """,
            (str(event.session_id), str(payload.tool_call_id)),
        ).fetchone()
        tool_duration_ms = 0
        if started_at_row is not None and started_at_row["started_at"] is not None:
            started_at = datetime.fromisoformat(started_at_row["started_at"])
            tool_duration_ms = max(
                int((event.created_at - started_at).total_seconds() * 1000),
                0,
            )

        connection.execute(
            """
            update turn_metrics
            set
                tool_duration_ms_total = tool_duration_ms_total + ?,
                succeeded_tool_call_count = succeeded_tool_call_count + ?,
                failed_tool_call_count = failed_tool_call_count + ?
            where session_id = ? and turn_id = ?
            """,
            (
                tool_duration_ms,
                1 if payload.success else 0,
                0 if payload.success else 1,
                str(event.session_id),
                str(turn_id),
            ),
        )
        return

    if isinstance(payload, TurnCompleted | TurnFailed):
        started_at_row = connection.execute(
            """
            select started_at from turn_metrics
            where session_id = ? and turn_id = ?
            """,
            (str(event.session_id), str(turn_id)),
        ).fetchone()
        turn_duration_ms = None
        if started_at_row is not None and started_at_row["started_at"] is not None:
            started_at = datetime.fromisoformat(started_at_row["started_at"])
            turn_duration_ms = max(
                int((event.created_at - started_at).total_seconds() * 1000),
                0,
            )

        connection.execute(
            """
            update turn_metrics
            set completed_at = ?, turn_duration_ms = ?
            where session_id = ? and turn_id = ?
            """,
            (
                event.created_at.isoformat(),
                turn_duration_ms,
                str(event.session_id),
                str(turn_id),
            ),
        )


__all__ = ["_apply_turn_metrics_projection"]
