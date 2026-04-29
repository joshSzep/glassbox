"""Runtime-note projection read helpers for SQLite-backed stores."""

import sqlite3
from collections.abc import Sequence

from glassbox.core.ids import SessionId
from glassbox.core.models import RuntimeNoteRecord
from glassbox.store.sqlite_sessions import _resolve_session_lineage
from glassbox.store.sqlite_sessions import get_session
from glassbox.store.sqlite_utils import _runtime_note_from_row


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


__all__ = ["list_runtime_notes"]
