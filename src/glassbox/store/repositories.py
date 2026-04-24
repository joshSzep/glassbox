"""Concrete repository adapters backed by the Glassbox store modules."""

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import glassbox.store._sqlite_events as event_store
import glassbox.store._sqlite_fork as fork_store
import glassbox.store._sqlite_queries as query_store
import glassbox.store._sqlite_sessions as session_store
import glassbox.store.artifacts as artifact_store
from glassbox.core.events import EventEnvelope
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import MessageId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import ResolvedForkPoint
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import SessionConfig
from glassbox.core.models import SessionRecord
from glassbox.core.models import SessionState
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.core.models import TurnMetricsRecord
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import SessionStatus
from glassbox.core.types import ToolExecutionStatus
from glassbox.services.contracts import StoredArtifact


class SQLiteSessionRepository:
    """Session repository adapter backed by a SQLite connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

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
    ) -> list[TranscriptMessage]:
        return query_store.list_transcript_messages(self._connection, session_id)

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
    ) -> list[EventEnvelope]:
        return event_store.read_session_events_after(
            self._connection,
            session_id,
            after_sequence,
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

    def list_tool_calls(
        self,
        session_id: SessionId,
        *,
        status: ToolExecutionStatus | None = None,
    ) -> list[ToolCallRecord]:
        return query_store.list_tool_calls(self._connection, session_id, status=status)

    def list_approvals(
        self,
        session_id: SessionId,
        *,
        status: ApprovalStatus | None = None,
    ) -> list[ApprovalRecord]:
        return query_store.list_approvals(self._connection, session_id, status=status)

    def list_turn_metrics(
        self,
        session_id: SessionId,
        *,
        limit: int | None = None,
    ) -> list[TurnMetricsRecord]:
        return query_store.list_turn_metrics(
            self._connection,
            session_id,
            limit=limit,
        )

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


class FilesystemArtifactRepository:
    """Artifact repository adapter backed by the local filesystem and SQLite."""

    def __init__(self, connection: sqlite3.Connection, root_dir: Path) -> None:
        self._connection = connection
        self._root_dir = root_dir

    def write_text_artifact(
        self,
        session_id: SessionId,
        content: str,
        *,
        suffix: str,
    ) -> StoredArtifact:
        return artifact_store.write_text_artifact(
            self._root_dir,
            session_id,
            content,
            suffix=suffix,
        )

    def write_binary_artifact(
        self,
        session_id: SessionId,
        content: bytes,
        *,
        suffix: str,
    ) -> StoredArtifact:
        return artifact_store.write_binary_artifact(
            self._root_dir,
            session_id,
            content,
            suffix=suffix,
        )

    def read_text_artifact(
        self,
        relative_path: Path,
        *,
        encoding: str = "utf-8",
    ) -> str:
        return artifact_store.read_text_artifact(
            self._root_dir,
            relative_path,
            encoding=encoding,
        )

    def read_binary_artifact(self, relative_path: Path) -> bytes:
        return artifact_store.read_binary_artifact(self._root_dir, relative_path)

    def record_text_artifact(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        tool_call_id: ToolCallId,
        artifact_kind: str,
        content: str,
        *,
        suffix: str,
    ) -> tuple[StoredArtifact, EventEnvelope]:
        return artifact_store.record_text_artifact(
            self._connection,
            self._root_dir,
            session_id,
            turn_id,
            tool_call_id,
            artifact_kind,
            content,
            suffix=suffix,
        )

    def record_binary_artifact(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        tool_call_id: ToolCallId,
        artifact_kind: str,
        content: bytes,
        *,
        suffix: str,
    ) -> tuple[StoredArtifact, EventEnvelope]:
        return artifact_store.record_binary_artifact(
            self._connection,
            self._root_dir,
            session_id,
            turn_id,
            tool_call_id,
            artifact_kind,
            content,
            suffix=suffix,
        )
