"""Session-state projection handlers for the SQLite-backed event store."""

import sqlite3

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionStarted
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserQuestionAsked
from glassbox.core.types import SessionStatus


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


__all__ = ["_apply_session_state_projection"]
