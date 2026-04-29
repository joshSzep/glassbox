"""Read-only query helpers for SQLite-backed store projections."""

import sqlite3
from collections.abc import Sequence
from datetime import datetime

from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import MessagePart
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import TaskRecord
from glassbox.core.models import TaskStepRecord
from glassbox.core.models import TaskVerificationRecord
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.core.models import TurnMetricsRecord
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import TaskBlockedReason
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskStepStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import ToolExecutionStatus
from glassbox.store.sqlite_sessions import _resolve_session_lineage
from glassbox.store.sqlite_sessions import get_session
from glassbox.store.sqlite_utils import _parse_optional_datetime
from glassbox.store.sqlite_utils import _runtime_note_from_row


def list_transcript_messages(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[TranscriptMessage]:
    """Read transcript messages for a session in conversation order."""

    query = """
        select
            message_id,
            role,
            content_text,
            created_at
        from transcript_messages
        where session_id = ?
        order by created_at asc, message_id asc
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


def list_tasks(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    status: TaskPlanStatus | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[TaskRecord]:
    """Read task summaries for a session."""

    query = _task_record_select_sql() + " where tasks.session_id = ?"
    parameters: list[object] = [str(session_id)]
    if status is not None:
        query += " and tasks.status = ?"
        parameters.append(status.value)
    query += " group by tasks.session_id, tasks.task_id order by tasks.updated_at desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)
    if offset:
        query += " offset ?"
        parameters.append(offset)

    rows = connection.execute(query, parameters).fetchall()
    return [_task_record_from_row(row) for row in rows]


def get_task(
    connection: sqlite3.Connection,
    session_id: SessionId,
    task_id: TaskId,
) -> TaskRecord | None:
    """Read one task summary by ID."""

    row = connection.execute(
        _task_record_select_sql()
        + """
        where tasks.session_id = ? and tasks.task_id = ?
        group by tasks.session_id, tasks.task_id
        """,
        (str(session_id), str(task_id)),
    ).fetchone()
    if row is None:
        return None
    return _task_record_from_row(row)


def list_task_steps(
    connection: sqlite3.Connection,
    session_id: SessionId,
    task_id: TaskId,
) -> list[TaskStepRecord]:
    """Read task steps in plan order."""

    rows = connection.execute(
        """
        select
            task_id,
            step_id,
            title,
            description,
            step_order,
            status,
            blocked_reason
        from task_steps
        where session_id = ? and task_id = ?
        order by step_order asc, step_id asc
        """,
        (str(session_id), str(task_id)),
    ).fetchall()
    return [
        TaskStepRecord(
            task_id=row["task_id"],
            step_id=row["step_id"],
            title=row["title"],
            description=row["description"],
            order=row["step_order"],
            status=TaskStepStatus(row["status"]),
            blocked_reason=(
                TaskBlockedReason(row["blocked_reason"])
                if row["blocked_reason"]
                else None
            ),
        )
        for row in rows
    ]


def list_task_verifications(
    connection: sqlite3.Connection,
    session_id: SessionId,
    task_id: TaskId,
) -> list[TaskVerificationRecord]:
    """Read verification runs for a task."""

    rows = connection.execute(
        """
        select
            task_id,
            verification_id,
            step_id,
            status,
            check_name,
            summary
        from task_verifications
        where session_id = ? and task_id = ?
        order by coalesce(started_at, completed_at) asc, verification_id asc
        """,
        (str(session_id), str(task_id)),
    ).fetchall()
    return [
        TaskVerificationRecord(
            task_id=row["task_id"],
            verification_id=row["verification_id"],
            step_id=row["step_id"],
            status=TaskVerificationStatus(row["status"]),
            check_name=row["check_name"],
            summary=row["summary"],
        )
        for row in rows
    ]


def list_open_blocked_tasks(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> list[TaskRecord]:
    """Read paused or failed tasks with a blocked reason."""

    rows = connection.execute(
        _task_record_select_sql()
        + """
        where tasks.session_id = ?
          and tasks.blocked_reason is not null
          and tasks.status in (?, ?)
        group by tasks.session_id, tasks.task_id
        order by tasks.updated_at desc
        """,
        (
            str(session_id),
            TaskPlanStatus.PAUSED.value,
            TaskPlanStatus.FAILED.value,
        ),
    ).fetchall()
    return [_task_record_from_row(row) for row in rows]


def _task_record_select_sql() -> str:
    return """
        select
            tasks.task_id,
            tasks.session_id,
            tasks.title,
            tasks.goal,
            tasks.status,
            tasks.source_turn_id,
            tasks.current_step_id,
            tasks.blocked_reason,
            tasks.blocked_detail,
            tasks.created_at,
            tasks.updated_at,
            tasks.last_sequence,
            count(task_steps.step_id) as step_count
        from tasks
        left join task_steps
          on task_steps.session_id = tasks.session_id
         and task_steps.task_id = tasks.task_id
    """


def _task_record_from_row(row: sqlite3.Row) -> TaskRecord:
    return TaskRecord(
        task_id=row["task_id"],
        session_id=row["session_id"],
        title=row["title"],
        goal=row["goal"],
        status=TaskPlanStatus(row["status"]),
        source_turn_id=row["source_turn_id"],
        current_step_id=row["current_step_id"],
        blocked_reason=(
            TaskBlockedReason(row["blocked_reason"]) if row["blocked_reason"] else None
        ),
        blocked_detail=row["blocked_detail"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_sequence=row["last_sequence"],
        step_count=row["step_count"],
    )


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
    "list_open_blocked_tasks",
    "list_task_steps",
    "list_task_verifications",
    "list_tasks",
    "list_tool_calls",
    "list_transcript_messages",
    "list_turn_metrics",
]
