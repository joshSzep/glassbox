"""Tool-attempt projection read helpers."""

import sqlite3
from datetime import datetime

from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.models import ToolAttemptRecord
from glassbox.core.types import ToolAttemptStatus


def get_tool_attempt(
    connection: sqlite3.Connection,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
) -> ToolAttemptRecord | None:
    """Read one projected tool attempt."""

    row = connection.execute(
        """
        select *
        from tool_attempts
        where session_id = ? and tool_attempt_id = ?
        """,
        (str(session_id), str(tool_attempt_id)),
    ).fetchone()
    return None if row is None else _tool_attempt_record_from_row(row)


def list_tool_attempts(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    status: ToolAttemptStatus | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[ToolAttemptRecord]:
    """Read projected tool attempts newest-first."""

    query = """
        select *
        from tool_attempts
        where session_id = ?
    """
    parameters: list[object] = [str(session_id)]
    if status is not None:
        query += " and status = ?"
        parameters.append(status.value)
    query += " order by last_sequence desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    elif offset:
        query += " limit -1"
    if offset:
        query += " offset ?"
        parameters.append(offset)

    rows = connection.execute(query, parameters).fetchall()
    return [_tool_attempt_record_from_row(row) for row in rows]


def _tool_attempt_record_from_row(row: sqlite3.Row) -> ToolAttemptRecord:
    return ToolAttemptRecord(
        tool_attempt_id=row["tool_attempt_id"],
        session_id=row["session_id"],
        turn_id=row["turn_id"],
        tool_call_id=row["tool_call_id"],
        task_id=row["task_id"],
        tool_name=row["tool_name"],
        status=ToolAttemptStatus(row["status"]),
        message=row["message"],
        started_at=_optional_datetime(row["started_at"]),
        last_heartbeat_at=_optional_datetime(row["last_heartbeat_at"]),
        heartbeat_expires_at=_optional_datetime(row["heartbeat_expires_at"]),
        completed_at=_optional_datetime(row["completed_at"]),
        completed_units=row["completed_units"],
        total_units=row["total_units"],
        output_artifact_id=row["output_artifact_id"],
        safe_to_retry=_optional_bool(row["safe_to_retry"]),
        retry_reason=row["retry_reason"],
        last_sequence=row["last_sequence"],
    )


def _optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _optional_bool(value: int | None) -> bool | None:
    if value is None:
        return None
    return bool(value)


__all__ = ["get_tool_attempt", "list_tool_attempts"]
