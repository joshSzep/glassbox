"""Runtime-note projection handlers for the SQLite-backed event store."""

import sqlite3

from glassbox.core.events import EventEnvelope
from glassbox.core.events import RuntimeNoteImported
from glassbox.core.events import RuntimeNoteRecorded


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


__all__ = ["_apply_runtime_note_projection"]
