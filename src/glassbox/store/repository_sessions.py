"""Session metadata and transcript methods for SQLite repositories."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import glassbox.store.sqlite_queries as query_store
import glassbox.store.sqlite_sessions as session_store
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import SessionConfig
from glassbox.core.models import SessionRecord
from glassbox.core.models import SessionState
from glassbox.core.models import TranscriptMessage
from glassbox.core.types import SessionStatus


class _SQLiteSessionMethods:
    if TYPE_CHECKING:
        _connection: sqlite3.Connection

    def create_session(
        self,
        session_id: SessionId,
        config: SessionConfig,
        *,
        status: SessionStatus = SessionStatus.IDLE,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        last_sequence: int = 0,
    ) -> SessionRecord:
        return session_store.create_session(
            self._connection,
            session_id,
            config,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            last_sequence=last_sequence,
        )

    def get_session(self, session_id: SessionId) -> SessionRecord | None:
        return session_store.get_session(self._connection, session_id)

    def get_session_state(self, session_id: SessionId) -> SessionState | None:
        return session_store.get_session_state(self._connection, session_id)

    def list_transcript_messages(
        self,
        session_id: SessionId,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TranscriptMessage]:
        return query_store.list_transcript_messages(
            self._connection,
            session_id,
            limit=limit,
            offset=offset,
        )

    def list_runtime_notes(
        self,
        session_id: SessionId,
        *,
        include_inherited: bool = True,
    ) -> list[RuntimeNoteRecord]:
        return query_store.list_runtime_notes(
            self._connection,
            session_id,
            include_inherited=include_inherited,
        )

    def list_sessions(
        self,
        *,
        status: SessionStatus | None = None,
        limit: int | None = None,
    ) -> list[SessionRecord]:
        return session_store.list_sessions(
            self._connection,
            status=status,
            limit=limit,
        )

    def update_session(
        self,
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
        return session_store.update_session(
            self._connection,
            session_id,
            status=status,
            updated_at=updated_at,
            cwd=cwd,
            model_name=model_name,
            approval_mode=approval_mode,
            last_sequence=last_sequence,
            parent_session_id=parent_session_id,
            forked_from_turn_id=forked_from_turn_id,
            forked_from_sequence=forked_from_sequence,
            branch_label=branch_label,
        )


__all__ = ["_SQLiteSessionMethods"]
