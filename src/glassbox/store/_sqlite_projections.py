"""Projection application helpers for the SQLite-backed event store."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelCallCompleted
from glassbox.core.events import ModelCallStarted
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import RuntimeNoteImported
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionStarted
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.types import SessionStatus
from glassbox.store._sqlite_utils import _stringify_identifier


def _apply_projection_event(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    _apply_session_state_projection(connection, event)
    _apply_transcript_projection(connection, event)
    _apply_tool_call_projection(connection, event)
    _apply_approval_projection(connection, event)
    _apply_runtime_note_projection(connection, event)
    _apply_turn_metrics_projection(connection, event)


def _clear_session_projections(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> None:
    session_id_value = str(session_id)
    connection.execute(
        "delete from session_state where session_id = ?",
        (session_id_value,),
    )
    connection.execute(
        "delete from transcript_messages where session_id = ?",
        (session_id_value,),
    )
    connection.execute(
        "delete from tool_calls where session_id = ?",
        (session_id_value,),
    )
    connection.execute(
        "delete from approvals where session_id = ?",
        (session_id_value,),
    )
    connection.execute(
        "delete from runtime_notes where session_id = ?",
        (session_id_value,),
    )
    connection.execute(
        "delete from turn_metrics where session_id = ?",
        (session_id_value,),
    )


def _apply_session_state_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    existing_row = connection.execute(
        """
        select status, current_turn_id, pending_approval_id, pending_question_id
        from session_state
        where session_id = ?
        """,
        (str(event.session_id),),
    ).fetchone()
    current_turn_id = (
        existing_row["current_turn_id"] if existing_row is not None else None
    )
    pending_approval_id = (
        existing_row["pending_approval_id"] if existing_row is not None else None
    )
    pending_question_id = (
        existing_row["pending_question_id"] if existing_row is not None else None
    )
    status = (
        existing_row["status"] if existing_row is not None else SessionStatus.RUNNING
    )

    payload = event.payload
    if isinstance(payload, SessionStarted):
        status = SessionStatus.RUNNING
    elif isinstance(payload, TurnStarted):
        current_turn_id = str(payload.turn_id)
        status = SessionStatus.RUNNING
    elif isinstance(payload, TurnCompleted):
        current_turn_id = None
        if payload.outcome == "completed":
            status = SessionStatus.RUNNING
    elif isinstance(payload, TurnFailed):
        current_turn_id = None
        status = SessionStatus.RUNNING
    elif isinstance(payload, ApprovalRequested):
        pending_approval_id = str(payload.approval_id)
        status = SessionStatus.AWAITING_APPROVAL
    elif isinstance(payload, ApprovalResolved):
        pending_approval_id = None
        status = SessionStatus.RUNNING
    elif isinstance(payload, UserQuestionAsked):
        pending_question_id = str(payload.question_id)
        status = SessionStatus.AWAITING_USER_INPUT
    elif isinstance(payload, UserAnswerProvided):
        pending_question_id = None
        status = SessionStatus.RUNNING
    elif isinstance(payload, SessionCompleted):
        current_turn_id = None
        pending_approval_id = None
        pending_question_id = None
        status = SessionStatus.COMPLETED
    elif isinstance(payload, SessionFailed):
        current_turn_id = None
        pending_approval_id = None
        pending_question_id = None
        status = SessionStatus.FAILED

    connection.execute(
        """
        insert into session_state (
            session_id,
            status,
            current_turn_id,
            pending_approval_id,
            pending_question_id,
            last_sequence,
            updated_at
        ) values (?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id) do update set
            status = excluded.status,
            current_turn_id = excluded.current_turn_id,
            pending_approval_id = excluded.pending_approval_id,
            pending_question_id = excluded.pending_question_id,
            last_sequence = excluded.last_sequence,
            updated_at = excluded.updated_at
        """,
        (
            str(event.session_id),
            status,
            current_turn_id,
            pending_approval_id,
            pending_question_id,
            event.sequence,
            event.created_at.isoformat(),
        ),
    )


def _apply_transcript_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, SessionStarted | TurnStarted | TurnCompleted | TurnFailed):
        return

    if isinstance(payload, UserMessageReceived):
        connection.execute(
            """
            insert into transcript_messages (
                message_id,
                session_id,
                turn_id,
                role,
                status,
                created_at,
                completed_at,
                content_text
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(message_id) do update set
                turn_id = excluded.turn_id,
                role = excluded.role,
                status = excluded.status,
                created_at = excluded.created_at,
                completed_at = excluded.completed_at,
                content_text = excluded.content_text
            """,
            (
                str(payload.message_id),
                str(event.session_id),
                _stringify_identifier(event.turn_id),
                "user",
                "completed",
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                payload.text,
            ),
        )
        return

    if isinstance(payload, TranscriptMessageImported):
        content_text = "".join(part.text for part in payload.parts)
        connection.execute(
            """
            insert into transcript_messages (
                message_id,
                session_id,
                turn_id,
                role,
                status,
                created_at,
                completed_at,
                content_text
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(message_id) do update set
                role = excluded.role,
                status = excluded.status,
                created_at = excluded.created_at,
                completed_at = excluded.completed_at,
                content_text = excluded.content_text
            """,
            (
                str(payload.message_id),
                str(event.session_id),
                None,
                payload.role,
                "completed",
                payload.source_created_at.isoformat(),
                payload.source_created_at.isoformat(),
                content_text,
            ),
        )
        return

    if isinstance(payload, AssistantMessageStarted):
        connection.execute(
            """
            insert into transcript_messages (
                message_id,
                session_id,
                turn_id,
                role,
                status,
                created_at,
                completed_at,
                content_text
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(message_id) do update set
                turn_id = excluded.turn_id,
                role = excluded.role,
                status = excluded.status,
                created_at = excluded.created_at,
                content_text = excluded.content_text
            """,
            (
                str(payload.message_id),
                str(event.session_id),
                _stringify_identifier(event.turn_id),
                "assistant",
                "streaming",
                event.created_at.isoformat(),
                None,
                "",
            ),
        )
        return

    if isinstance(payload, AssistantMessageDelta):
        connection.execute(
            """
            insert into transcript_messages (
                message_id,
                session_id,
                turn_id,
                role,
                status,
                created_at,
                completed_at,
                content_text
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(message_id) do update set
                turn_id = coalesce(excluded.turn_id, transcript_messages.turn_id),
                role = excluded.role,
                status = excluded.status,
                content_text = transcript_messages.content_text || excluded.content_text
            """,
            (
                str(payload.message_id),
                str(event.session_id),
                _stringify_identifier(event.turn_id),
                "assistant",
                "streaming",
                event.created_at.isoformat(),
                None,
                payload.delta,
            ),
        )
        return

    if isinstance(payload, AssistantMessageCompleted):
        content_text = "".join(part.text for part in payload.parts)
        connection.execute(
            """
            insert into transcript_messages (
                message_id,
                session_id,
                turn_id,
                role,
                status,
                created_at,
                completed_at,
                content_text
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(message_id) do update set
                turn_id = coalesce(excluded.turn_id, transcript_messages.turn_id),
                role = excluded.role,
                status = excluded.status,
                completed_at = excluded.completed_at,
                content_text = excluded.content_text
            """,
            (
                str(payload.message_id),
                str(event.session_id),
                _stringify_identifier(event.turn_id),
                "assistant",
                "completed",
                event.created_at.isoformat(),
                event.created_at.isoformat(),
                content_text,
            ),
        )


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
                exit_code
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(tool_call_id) do update set
                turn_id = excluded.turn_id,
                tool_name = excluded.tool_name,
                status = excluded.status
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
                exit_code
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(tool_call_id) do update set
                turn_id = excluded.turn_id,
                tool_name = excluded.tool_name,
                status = excluded.status,
                started_at = excluded.started_at
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


def _apply_approval_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, ApprovalRequested):
        connection.execute(
            """
            insert into approvals (
                approval_id,
                session_id,
                turn_id,
                subject,
                reason,
                status,
                requested_at,
                resolved_at,
                decided_by
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(approval_id) do update set
                turn_id = excluded.turn_id,
                subject = excluded.subject,
                reason = excluded.reason,
                status = excluded.status,
                requested_at = excluded.requested_at
            """,
            (
                str(payload.approval_id),
                str(event.session_id),
                str(payload.turn_id),
                payload.subject,
                payload.reason,
                "pending",
                event.created_at.isoformat(),
                None,
                None,
            ),
        )
        return

    if isinstance(payload, ApprovalResolved):
        connection.execute(
            """
            update approvals
            set
                status = ?,
                resolved_at = ?,
                decided_by = ?
            where approval_id = ?
            """,
            (
                payload.decision,
                event.created_at.isoformat(),
                payload.decided_by,
                str(payload.approval_id),
            ),
        )


def _apply_runtime_note_projection(
    connection: sqlite3.Connection,
    event: EventEnvelope,
) -> None:
    payload = event.payload
    if isinstance(payload, RuntimeNoteRecorded):
        source_session_id = event.session_id
        source_sequence = event.sequence
        created_at = event.created_at.isoformat()
    elif isinstance(payload, RuntimeNoteImported):
        source_session_id = payload.source_session_id
        source_sequence = payload.source_sequence
        created_at = payload.source_created_at.isoformat()
    else:
        return

    connection.execute(
        """
        insert into runtime_notes (
            session_id,
            sequence,
            source_session_id,
            source_sequence,
            category,
            message,
            created_at
        ) values (?, ?, ?, ?, ?, ?, ?)
        on conflict(session_id, sequence) do update set
            source_session_id = excluded.source_session_id,
            source_sequence = excluded.source_sequence,
            category = excluded.category,
            message = excluded.message,
            created_at = excluded.created_at
        """,
        (
            str(event.session_id),
            event.sequence,
            str(source_session_id),
            source_sequence,
            payload.category,
            payload.message,
            created_at,
        ),
    )


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


__all__ = ["_apply_projection_event", "_clear_session_projections"]
