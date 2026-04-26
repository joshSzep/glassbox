"""Transcript projection handlers for the SQLite-backed event store."""

import sqlite3

from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionStarted
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.store.sqlite_utils import _stringify_identifier


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


__all__ = ["_apply_transcript_projection"]
