"""Tool-call projection handlers for the SQLite-backed event store."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted


def _apply_tool_call_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, ModelToolCallRequested):
        connection.execute(
            """
            insert into tool_calls (
                tool_call_id,
                session_id,
                turn_id,
                tool_name,
                status,
                started_at,
                completed_at,
                summary,
                exit_code,
                policy_outcome,
                policy_risk_level,
                policy_source_kind,
                policy_source_label,
                policy_reason
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(tool_call_id) do update set
                turn_id = excluded.turn_id,
                tool_name = excluded.tool_name,
                status = excluded.status,
                policy_outcome = coalesce(
                    excluded.policy_outcome,
                    tool_calls.policy_outcome
                ),
                policy_risk_level = coalesce(
                    excluded.policy_risk_level,
                    tool_calls.policy_risk_level
                ),
                policy_source_kind = coalesce(
                    excluded.policy_source_kind,
                    tool_calls.policy_source_kind
                ),
                policy_source_label = coalesce(
                    excluded.policy_source_label,
                    tool_calls.policy_source_label
                ),
                policy_reason = coalesce(
                    excluded.policy_reason,
                    tool_calls.policy_reason
                )
            """,
            (
                str(payload.tool_call_id),
                str(event.session_id),
                str(payload.turn_id),
                payload.tool_name,
                "requested",
                None,
                None,
                None,
                None,
                payload.policy_outcome,
                payload.policy_risk_level,
                payload.policy_source_kind,
                payload.policy_source_label,
                payload.policy_reason,
            ),
        )
        return

    if isinstance(payload, ToolExecutionStarted):
        connection.execute(
            """
            insert into tool_calls (
                tool_call_id,
                session_id,
                turn_id,
                tool_name,
                status,
                started_at,
                completed_at,
                summary,
                exit_code,
                policy_outcome,
                policy_risk_level,
                policy_source_kind,
                policy_source_label,
                policy_reason
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(tool_call_id) do update set
                turn_id = excluded.turn_id,
                tool_name = excluded.tool_name,
                status = excluded.status,
                started_at = excluded.started_at,
                policy_outcome = coalesce(
                    excluded.policy_outcome,
                    tool_calls.policy_outcome
                ),
                policy_risk_level = coalesce(
                    excluded.policy_risk_level,
                    tool_calls.policy_risk_level
                ),
                policy_source_kind = coalesce(
                    excluded.policy_source_kind,
                    tool_calls.policy_source_kind
                ),
                policy_source_label = coalesce(
                    excluded.policy_source_label,
                    tool_calls.policy_source_label
                ),
                policy_reason = coalesce(
                    excluded.policy_reason,
                    tool_calls.policy_reason
                )
            """,
            (
                str(payload.tool_call_id),
                str(event.session_id),
                str(payload.turn_id),
                payload.tool_name,
                "running",
                event.created_at.isoformat(),
                None,
                None,
                None,
                payload.policy_outcome,
                payload.policy_risk_level,
                payload.policy_source_kind,
                payload.policy_source_label,
                payload.policy_reason,
            ),
        )
        return

    if isinstance(payload, ToolExecutionCompleted):
        connection.execute(
            """
            update tool_calls
            set
                status = ?,
                completed_at = ?,
                summary = ?,
                exit_code = ?
            where tool_call_id = ?
            """,
            (
                "succeeded" if payload.success else "failed",
                event.created_at.isoformat(),
                payload.summary,
                payload.exit_code,
                str(payload.tool_call_id),
            ),
        )


__all__ = ["_apply_tool_call_projection"]
