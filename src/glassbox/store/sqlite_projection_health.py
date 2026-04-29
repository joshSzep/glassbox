"""Projection health inspection helpers for the SQLite store."""

import sqlite3

from glassbox.core.ids import SessionId
from glassbox.core.models import ProjectionHealth
from glassbox.store.sqlite_sessions import get_session

_PROJECTION_TABLES = (
    "session_state",
    "transcript_messages",
    "tool_calls",
    "approvals",
    "runtime_notes",
    "turn_metrics",
    "tasks",
    "task_steps",
    "task_verifications",
)


def inspect_session_projection_health(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> ProjectionHealth:
    """Compare canonical event progress with derived projection progress."""

    session = get_session(connection, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")

    try:
        _ensure_projection_tables_readable(connection, session_id)
        canonical_last_sequence = _canonical_last_sequence(connection, session_id)
        projected_last_sequence = _projected_last_sequence(connection, session_id)
    except sqlite3.Error as exc:
        return ProjectionHealth(
            state="unavailable",
            canonical_last_sequence=session.last_sequence,
            projected_last_sequence=None,
            lag=session.last_sequence,
            estimated_rebuild_event_count=session.last_sequence,
            degraded=True,
            detail=f"projection read failed: {exc}",
        )

    if projected_last_sequence is None:
        if canonical_last_sequence == 0:
            return ProjectionHealth(
                state="ok",
                canonical_last_sequence=canonical_last_sequence,
                projected_last_sequence=None,
                projected_progress_ratio=1.0,
            )
        return ProjectionHealth(
            state="stale",
            canonical_last_sequence=canonical_last_sequence,
            projected_last_sequence=None,
            lag=canonical_last_sequence,
            estimated_rebuild_event_count=canonical_last_sequence,
            projected_progress_ratio=0.0,
            degraded=True,
            detail="session_state projection row is missing",
        )

    if projected_last_sequence < canonical_last_sequence:
        lag = canonical_last_sequence - projected_last_sequence
        return ProjectionHealth(
            state="stale",
            canonical_last_sequence=canonical_last_sequence,
            projected_last_sequence=projected_last_sequence,
            lag=lag,
            estimated_rebuild_event_count=canonical_last_sequence,
            projected_progress_ratio=_progress_ratio(
                projected_last_sequence,
                canonical_last_sequence,
            ),
            degraded=True,
            detail=f"session_state projection is {lag} event(s) behind",
        )

    if projected_last_sequence > canonical_last_sequence:
        return ProjectionHealth(
            state="stale",
            canonical_last_sequence=canonical_last_sequence,
            projected_last_sequence=projected_last_sequence,
            estimated_rebuild_event_count=canonical_last_sequence,
            degraded=True,
            detail="session_state projection is ahead of canonical events",
        )

    return ProjectionHealth(
        state="ok",
        canonical_last_sequence=canonical_last_sequence,
        projected_last_sequence=projected_last_sequence,
        projected_progress_ratio=1.0,
    )


def _progress_ratio(
    projected_last_sequence: int,
    canonical_last_sequence: int,
) -> float:
    if canonical_last_sequence <= 0:
        return 1.0
    return round(min(projected_last_sequence / canonical_last_sequence, 1.0), 3)


def _ensure_projection_tables_readable(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> None:
    for table_name in _PROJECTION_TABLES:
        connection.execute(
            f"select 1 from {table_name} where session_id = ? limit 1",
            (str(session_id),),
        ).fetchone()


def _canonical_last_sequence(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> int:
    row = connection.execute(
        "select coalesce(max(sequence), 0) from events where session_id = ?",
        (str(session_id),),
    ).fetchone()
    return int(row[0])


def _projected_last_sequence(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> int | None:
    row = connection.execute(
        "select last_sequence from session_state where session_id = ?",
        (str(session_id),),
    ).fetchone()
    if row is None:
        return None
    return int(row[0])


__all__ = ["inspect_session_projection_health"]
