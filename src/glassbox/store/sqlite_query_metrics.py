"""Turn-metric projection read helpers for SQLite-backed stores."""

import sqlite3

from glassbox.core.ids import SessionId
from glassbox.core.models import TurnMetricsRecord
from glassbox.store.sqlite_utils import _parse_optional_datetime


def list_turn_metrics(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[TurnMetricsRecord]:
    """Read aggregated per-turn runtime metrics for a session."""

    query = """
        select
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
        from turn_metrics
        where session_id = ?
        order by coalesce(started_at, completed_at) desc, turn_id desc
    """
    parameters: list[object] = [str(session_id)]
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    if offset:
        query += " offset ?"
        parameters.append(offset)

    rows = connection.execute(query, parameters).fetchall()
    return [
        TurnMetricsRecord(
            turn_id=row["turn_id"],
            started_at=_parse_optional_datetime(row["started_at"]),
            completed_at=_parse_optional_datetime(row["completed_at"]),
            turn_duration_ms=row["turn_duration_ms"],
            model_call_count=row["model_call_count"],
            model_duration_ms_total=row["model_duration_ms_total"],
            model_input_tokens_total=row["model_input_tokens_total"],
            model_output_tokens_total=row["model_output_tokens_total"],
            tool_call_count=row["tool_call_count"],
            tool_duration_ms_total=row["tool_duration_ms_total"],
            succeeded_tool_call_count=row["succeeded_tool_call_count"],
            failed_tool_call_count=row["failed_tool_call_count"],
        )
        for row in rows
    ]


__all__ = ["list_turn_metrics"]
