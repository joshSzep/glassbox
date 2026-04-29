"""Transcript projection read helpers for SQLite-backed stores."""

import sqlite3

from glassbox.core.ids import SessionId
from glassbox.core.models import MessagePart
from glassbox.core.models import TranscriptMessage


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


__all__ = ["list_transcript_messages"]
