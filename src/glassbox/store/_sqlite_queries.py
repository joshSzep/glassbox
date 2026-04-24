"""Read-only query helpers for SQLite-backed store projections."""

import sqlite3
from collections.abc import Sequence
from datetime import datetime

from glassbox.core.ids import SessionId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import MessagePart
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.core.models import TurnMetricsRecord
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import ToolExecutionStatus
from glassbox.store._sqlite_sessions import _resolve_session_lineage
from glassbox.store._sqlite_sessions import get_session
from glassbox.store._sqlite_utils import _parse_optional_datetime
from glassbox.store._sqlite_utils import _runtime_note_from_row


def list_transcript_messages(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> list[TranscriptMessage]:
    """Read transcript messages for a session in conversation order."""

    rows = connection.execute(
        """
        select
            message_id,
            role,
            content_text,
            created_at
        from transcript_messages
        where session_id = ?
        order by created_at asc, message_id asc
        """,
        (str(session_id),),
    ).fetchall()
    return [
        TranscriptMessage(
            message_id=row["message_id"],
            role=row["role"],
            parts=[MessagePart(kind="text", text=row["content_text"])],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def list_runtime_notes(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    include_inherited: bool = True,
) -> list[RuntimeNoteRecord]:
    """Read the active runtime note set for a session."""

    session = get_session(connection, session_id)
    if session is None:
        return []

    current_rows = _list_session_runtime_note_rows(connection, session_id)
    current_notes = [_runtime_note_from_row(session_id, row) for row in current_rows]
    if not include_inherited:
        return [note for note in current_notes if not note.inherited]

    if (
        any(note.inherited for note in current_notes)
        or session.parent_session_id is None
    ):
        return current_notes

    notes: list[RuntimeNoteRecord] = []
    for source_session in _resolve_session_lineage(connection, session):
        inherited = source_session.session_id != session_id
        notes.extend(
            RuntimeNoteRecord(
                source_session_id=source_session.session_id,
                source_sequence=row["source_sequence"] or row["sequence"],
                category=row["category"],
                message=row["message"],
                created_at=row["created_at"],
                inherited=inherited,
            )
            for row in _list_session_runtime_note_rows(
                connection,
                source_session.session_id,
            )
        )
    return notes


def list_tool_calls(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    status: ToolExecutionStatus | None = None,
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
            summary
        from tool_calls
        where session_id = ?
    """
    parameters: list[object] = [str(session_id)]
    if status is not None:
        query += " and status = ?"
        parameters.append(status)
    query += " order by started_at asc"

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
            status=ApprovalStatus(row["status"]),
            requested_at=datetime.fromisoformat(row["requested_at"]),
            resolved_at=_parse_optional_datetime(row["resolved_at"]),
            decided_by=row["decided_by"],
        )
        for row in rows
    ]


def list_turn_metrics(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    limit: int | None = None,
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


def _list_session_runtime_note_rows(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> list[sqlite3.Row]:
    rows = connection.execute(
        """
        select
            sequence,
            source_session_id,
            source_sequence,
            category,
            message,
            created_at
        from runtime_notes
        where session_id = ?
        order by sequence asc
        """,
        (str(session_id),),
    ).fetchall()
    return _dedupe_runtime_note_rows(rows)


def _dedupe_runtime_note_rows(rows: Sequence[sqlite3.Row]) -> list[sqlite3.Row]:
    # Keep the latest exact note per source session so the active note set stays
    # bounded while the canonical event log remains append-only.
    retained_rows: dict[tuple[str, str, str], sqlite3.Row] = {}
    for row in rows:
        retained_rows[
            (
                str(row["source_session_id"] or ""),
                row["category"],
                row["message"],
            )
        ] = row
    return sorted(retained_rows.values(), key=lambda row: row["sequence"])


__all__ = [
    "list_approvals",
    "list_runtime_notes",
    "list_tool_calls",
    "list_transcript_messages",
    "list_turn_metrics",
]
