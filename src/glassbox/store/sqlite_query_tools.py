"""Tool-call and approval projection read helpers for SQLite-backed stores."""

import sqlite3
from datetime import datetime

from glassbox.core.ids import SessionId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import ToolCallRecord
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import ToolExecutionStatus
from glassbox.store.sqlite_utils import _parse_optional_datetime


def list_tool_calls(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    status: ToolExecutionStatus | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[ToolCallRecord]:
    """Read tool call records for a session, optionally filtered by status."""

    query = """
        select
            tool_call_id,
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
        from tool_calls
        where session_id = ?
    """
    parameters: list[object] = [str(session_id)]
    if status is not None:
        query += " and status = ?"
        parameters.append(status)
    query += " order by started_at asc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    if offset:
        query += " offset ?"
        parameters.append(offset)

    rows = connection.execute(query, parameters).fetchall()
    return [
        ToolCallRecord(
            tool_call_id=row["tool_call_id"],
            turn_id=row["turn_id"],
            tool_name=row["tool_name"],
            status=ToolExecutionStatus(row["status"]),
            started_at=_parse_optional_datetime(row["started_at"]),
            completed_at=_parse_optional_datetime(row["completed_at"]),
            summary=row["summary"],
            exit_code=row["exit_code"],
            policy_outcome=row["policy_outcome"],
            policy_risk_level=row["policy_risk_level"],
            policy_source_kind=row["policy_source_kind"],
            policy_source_label=row["policy_source_label"],
            policy_reason=row["policy_reason"],
        )
        for row in rows
    ]


def list_approvals(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    status: ApprovalStatus | None = None,
) -> list[ApprovalRecord]:
    """Read approval records for a session, optionally filtered by status."""

    query = """
        select
            approval_id,
            turn_id,
            subject,
            reason,
            policy_outcome,
            policy_risk_level,
            policy_source_kind,
            policy_source_label,
            status,
            requested_at,
            resolved_at,
            decided_by
        from approvals
        where session_id = ?
    """
    parameters: list[object] = [str(session_id)]
    if status is not None:
        query += " and status = ?"
        parameters.append(status)
    query += " order by requested_at asc"

    rows = connection.execute(query, parameters).fetchall()
    return [
        ApprovalRecord(
            approval_id=row["approval_id"],
            turn_id=row["turn_id"],
            subject=row["subject"],
            reason=row["reason"],
            policy_outcome=row["policy_outcome"],
            policy_risk_level=row["policy_risk_level"],
            policy_source_kind=row["policy_source_kind"],
            policy_source_label=row["policy_source_label"],
            status=ApprovalStatus(row["status"]),
            requested_at=datetime.fromisoformat(row["requested_at"]),
            resolved_at=_parse_optional_datetime(row["resolved_at"]),
            decided_by=row["decided_by"],
        )
        for row in rows
    ]


__all__ = ["list_approvals", "list_tool_calls"]
