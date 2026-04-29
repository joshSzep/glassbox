"""Event-log and fork methods for SQLite repositories."""

import sqlite3
from collections.abc import Sequence
from typing import TYPE_CHECKING

import glassbox.store.sqlite_events as event_store
import glassbox.store.sqlite_fork as fork_store
from glassbox.core.events import EventEnvelope
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import MessageId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.models import ResolvedForkPoint


class _SQLiteEventMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def append_event(self, event: EventEnvelope) -> EventEnvelope:
        return event_store.append_event(self._connection, event)

    def append_events(
        self,
        events: Sequence[EventEnvelope],
    ) -> list[EventEnvelope]:
        return event_store.append_events(self._connection, events)

    def record_runtime_note(
        self,
        session_id: SessionId,
        *,
        category: str,
        message: str,
    ) -> EventEnvelope:
        normalized_category = category.strip().lower()
        normalized_message = message.strip()
        if not normalized_category:
            raise ValueError("runtime note category must not be blank")
        if not normalized_message:
            raise ValueError("runtime note message must not be blank")
        return self.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=RuntimeNoteRecorded(
                    category=normalized_category,
                    message=normalized_message,
                ),
            )
        )

    def read_session_events(self, session_id: SessionId) -> list[EventEnvelope]:
        return event_store.read_session_events(self._connection, session_id)

    def read_session_events_after(
        self,
        session_id: SessionId,
        after_sequence: int,
        *,
        limit: int | None = None,
    ) -> list[EventEnvelope]:
        return event_store.read_session_events_after(
            self._connection,
            session_id,
            after_sequence,
            limit=limit,
        )

    def read_events_by_correlation_id(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId | None = None,
        message_id: MessageId | None = None,
        tool_call_id: ToolCallId | None = None,
        approval_id: ApprovalId | None = None,
    ) -> list[EventEnvelope]:
        return event_store.read_events_by_correlation_id(
            self._connection,
            session_id,
            turn_id=turn_id,
            message_id=message_id,
            tool_call_id=tool_call_id,
            approval_id=approval_id,
        )

    def rebuild_session_projections(self, session_id: SessionId) -> None:
        event_store.rebuild_session_projections(self._connection, session_id)

    def resolve_fork_point(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId | None = None,
    ) -> ResolvedForkPoint:
        return fork_store.resolve_fork_point(
            self._connection,
            session_id,
            turn_id=turn_id,
        )

    def build_imported_transcript_events(
        self,
        session_id: SessionId,
        fork_point: ResolvedForkPoint,
    ) -> list[EventEnvelope]:
        return fork_store.build_imported_transcript_events(session_id, fork_point)


__all__ = ["_SQLiteEventMethods"]
