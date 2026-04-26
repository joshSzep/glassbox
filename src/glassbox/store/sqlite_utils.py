"""Shared helper functions for the internal SQLite store modules."""

import json
import sqlite3
from datetime import datetime
from typing import cast
from uuid import UUID
from uuid import uuid5

from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import MessageId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import SessionRecord

IMPORTED_MESSAGE_NAMESPACE = UUID("2af6228d-37a0-4b62-9c58-7a4a2fdcb5fb")

type CorrelationValue = TurnId | MessageId | ToolCallId | ApprovalId | QuestionId


def _stringify_identifier(value: CorrelationValue | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _event_from_row(row: sqlite3.Row) -> EventEnvelope:
    payload_data = json.loads(row["payload_json"])
    return EventEnvelope.model_validate(
        {
            "event_id": row["event_id"],
            "session_id": row["session_id"],
            "sequence": row["sequence"],
            "event_type": row["event_type"],
            "event_version": row["event_version"],
            "created_at": row["created_at"],
            "payload": payload_data,
        }
    )


def _session_from_row(row: sqlite3.Row) -> SessionRecord:
    return SessionRecord.model_validate(
        {
            "session_id": row["session_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "cwd": row["cwd"],
            "model_name": row["model_name"],
            "approval_mode": row["approval_mode"],
            "parent_session_id": row["parent_session_id"],
            "forked_from_turn_id": row["forked_from_turn_id"],
            "forked_from_sequence": row["forked_from_sequence"],
            "branch_label": row["branch_label"],
            "last_sequence": row["last_sequence"],
        }
    )


def _derived_imported_message_id(
    session_id: SessionId,
    source_message_id: MessageId,
) -> MessageId:
    return uuid5(
        IMPORTED_MESSAGE_NAMESPACE,
        f"{session_id}:{source_message_id}",
    )


def _runtime_note_from_row(
    session_id: SessionId,
    row: sqlite3.Row,
) -> RuntimeNoteRecord:
    source_session_id_value = row["source_session_id"]
    source_session_id = (
        session_id
        if not source_session_id_value
        else cast(SessionId, source_session_id_value)
    )
    return RuntimeNoteRecord(
        source_session_id=source_session_id,
        source_sequence=row["source_sequence"] or row["sequence"],
        category=row["category"],
        message=row["message"],
        created_at=row["created_at"],
        inherited=source_session_id != str(session_id),
    )


__all__ = [
    "CorrelationValue",
    "_derived_imported_message_id",
    "_event_from_row",
    "_parse_optional_datetime",
    "_runtime_note_from_row",
    "_session_from_row",
    "_stringify_identifier",
]
