"""Session row and lineage helpers for the internal SQLite store modules."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from glassbox.core.ids import SessionId, TurnId
from glassbox.core.models import SessionConfig, SessionRecord, SessionState
from glassbox.core.types import ApprovalMode, SessionStatus
from glassbox.store._sqlite_utils import _session_from_row, _stringify_identifier


def create_session(
    connection: sqlite3.Connection,
    session_id: SessionId,
    config: SessionConfig,
    *,
    status: SessionStatus = SessionStatus.IDLE,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    last_sequence: int = 0,
) -> SessionRecord:
    """Create and return a coarse session metadata row."""

    effective_created_at = created_at or datetime.now(UTC)
    effective_updated_at = updated_at or effective_created_at
    with connection:
        connection.execute(
            """
            insert into sessions (
                session_id,
                status,
                created_at,
                updated_at,
                cwd,
                model_name,
                approval_mode,
                parent_session_id,
                forked_from_turn_id,
                forked_from_sequence,
                branch_label,
                last_sequence
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(session_id),
                status,
                effective_created_at.isoformat(),
                effective_updated_at.isoformat(),
                str(config.cwd),
                config.model_name,
                config.approval_mode,
                _stringify_identifier(config.parent_session_id),
                _stringify_identifier(config.forked_from_turn_id),
                config.forked_from_sequence,
                config.branch_label,
                last_sequence,
            ),
        )
    created_session = get_session(connection, session_id)
    if created_session is None:
        raise RuntimeError("create_session did not persist the session row")
    return created_session


def update_session(
    connection: sqlite3.Connection,
    session_id: SessionId,
    *,
    status: SessionStatus | None = None,
    updated_at: datetime | None = None,
    cwd: Path | None = None,
    model_name: str | None = None,
    approval_mode: str | None = None,
    last_sequence: int | None = None,
    parent_session_id: SessionId | None = None,
    forked_from_turn_id: TurnId | None = None,
    forked_from_sequence: int | None = None,
    branch_label: str | None = None,
) -> SessionRecord:
    """Update coarse session metadata and return the stored row."""

    session = get_session(connection, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    if approval_mode is not None:
        try:
            approval_mode = ApprovalMode(approval_mode)
        except ValueError as exc:
            raise ValueError(f"invalid approval mode: {approval_mode}") from exc

    changes: dict[str, object] = {
        "status": status or session.status,
        "updated_at": (updated_at or datetime.now(UTC)).isoformat(),
        "cwd": str(cwd or session.cwd),
        "model_name": model_name or session.model_name,
        "approval_mode": approval_mode or session.approval_mode,
        "parent_session_id": _stringify_identifier(parent_session_id)
        if parent_session_id is not None
        else _stringify_identifier(session.parent_session_id),
        "forked_from_turn_id": _stringify_identifier(forked_from_turn_id)
        if forked_from_turn_id is not None
        else _stringify_identifier(session.forked_from_turn_id),
        "forked_from_sequence": (
            session.forked_from_sequence
            if forked_from_sequence is None
            else forked_from_sequence
        ),
        "branch_label": (
            branch_label if branch_label is not None else session.branch_label
        ),
        "last_sequence": (
            session.last_sequence if last_sequence is None else last_sequence
        ),
    }
    with connection:
        connection.execute(
            """
            update sessions
            set
                status = ?,
                updated_at = ?,
                cwd = ?,
                model_name = ?,
                approval_mode = ?,
                parent_session_id = ?,
                forked_from_turn_id = ?,
                forked_from_sequence = ?,
                branch_label = ?,
                last_sequence = ?
            where session_id = ?
            """,
            (
                changes["status"],
                changes["updated_at"],
                changes["cwd"],
                changes["model_name"],
                changes["approval_mode"],
                changes["parent_session_id"],
                changes["forked_from_turn_id"],
                changes["forked_from_sequence"],
                changes["branch_label"],
                changes["last_sequence"],
                str(session_id),
            ),
        )
    updated_session = get_session(connection, session_id)
    if updated_session is None:
        raise RuntimeError("update_session did not preserve the session row")
    return updated_session


def get_session(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> SessionRecord | None:
    """Fetch a persisted session metadata row by session identifier."""

    row = connection.execute(
        """
        select
            session_id,
            status,
            created_at,
            updated_at,
            cwd,
            model_name,
            approval_mode,
            parent_session_id,
            forked_from_turn_id,
            forked_from_sequence,
            branch_label,
            last_sequence
        from sessions
        where session_id = ?
        """,
        (str(session_id),),
    ).fetchone()
    if row is None:
        return None
    return _session_from_row(row)


def get_session_state(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> SessionState | None:
    """Fetch the projected runtime-facing state for a session."""

    row = connection.execute(
        """
        select
            session_id,
            status,
            current_turn_id,
            pending_approval_id,
            pending_question_id,
            last_sequence
        from session_state
        where session_id = ?
        """,
        (str(session_id),),
    ).fetchone()
    if row is None:
        session = get_session(connection, session_id)
        if session is None:
            return None
        return SessionState(
            session_id=session.session_id,
            status=session.status,
            last_sequence=session.last_sequence,
        )

    return SessionState.model_validate(
        {
            "session_id": row["session_id"],
            "status": row["status"],
            "current_turn_id": row["current_turn_id"],
            "pending_approval_id": row["pending_approval_id"],
            "pending_question_id": row["pending_question_id"],
            "last_sequence": row["last_sequence"],
        }
    )


def list_sessions(
    connection: sqlite3.Connection,
    *,
    status: SessionStatus | None = None,
    limit: int | None = None,
) -> list[SessionRecord]:
    """List session metadata rows by recency, optionally filtered by status."""

    query = """
        select
            session_id,
            status,
            created_at,
            updated_at,
            cwd,
            model_name,
            approval_mode,
            parent_session_id,
            forked_from_turn_id,
            forked_from_sequence,
            branch_label,
            last_sequence
        from sessions
    """
    parameters: list[object] = []
    if status is not None:
        query += " where status = ?"
        parameters.append(status)
    query += " order by updated_at desc"
    if limit is not None:
        query += " limit ?"
        parameters.append(limit)

    rows = connection.execute(query, parameters).fetchall()
    return [_session_from_row(row) for row in rows]


def _resolve_session_lineage(
    connection: sqlite3.Connection,
    session: SessionRecord,
) -> list[SessionRecord]:
    lineage: list[SessionRecord] = [session]
    current_session = session
    while current_session.parent_session_id is not None:
        parent_session = get_session(connection, current_session.parent_session_id)
        if parent_session is None:
            break
        lineage.append(parent_session)
        current_session = parent_session
    lineage.reverse()
    return lineage


__all__ = [
    "_resolve_session_lineage",
    "create_session",
    "get_session",
    "get_session_state",
    "list_sessions",
    "update_session",
]
