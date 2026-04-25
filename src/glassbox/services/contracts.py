"""Service and repository contracts for Glassbox runtime wiring."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from typing import runtime_checkable

from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import MessageId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import ForkedSession
from glassbox.core.models import ProjectionHealth
from glassbox.core.models import ResolvedForkPoint
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import SessionConfig
from glassbox.core.models import SessionRecord
from glassbox.core.models import SessionState
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TranscriptMessage
from glassbox.core.models import TurnMetricsRecord
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import SessionStatus
from glassbox.core.types import ToolExecutionStatus


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    """Resolved information for a file-backed session artifact."""

    artifact_id: ArtifactId
    session_id: SessionId
    relative_path: Path
    absolute_path: Path


@runtime_checkable
class SessionRepository(Protocol):
    """Persistence contract for session metadata, events, and projections."""

    def create_session(
        self,
        session_id: SessionId,
        config: SessionConfig,
        *,
        status: SessionStatus = SessionStatus.IDLE,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        last_sequence: int = 0,
    ) -> SessionRecord: ...

    def get_session(self, session_id: SessionId) -> SessionRecord | None: ...

    def get_session_state(self, session_id: SessionId) -> SessionState | None: ...

    def list_transcript_messages(
        self,
        session_id: SessionId,
    ) -> list[TranscriptMessage]: ...

    def list_runtime_notes(
        self,
        session_id: SessionId,
        *,
        include_inherited: bool = True,
    ) -> list[RuntimeNoteRecord]: ...

    def list_sessions(
        self,
        *,
        status: SessionStatus | None = None,
        limit: int | None = None,
    ) -> list[SessionRecord]: ...

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
    ) -> SessionRecord: ...

    def append_event(self, event: EventEnvelope) -> EventEnvelope: ...

    def append_events(
        self,
        events: Sequence[EventEnvelope],
    ) -> list[EventEnvelope]: ...

    def record_runtime_note(
        self,
        session_id: SessionId,
        *,
        category: str,
        message: str,
    ) -> EventEnvelope: ...

    def read_session_events(self, session_id: SessionId) -> list[EventEnvelope]: ...

    def read_session_events_after(
        self,
        session_id: SessionId,
        after_sequence: int,
    ) -> list[EventEnvelope]: ...

    def read_events_by_correlation_id(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId | None = None,
        message_id: MessageId | None = None,
        tool_call_id: ToolCallId | None = None,
        approval_id: ApprovalId | None = None,
    ) -> list[EventEnvelope]: ...

    def rebuild_session_projections(self, session_id: SessionId) -> None: ...

    def inspect_session_projection_health(
        self,
        session_id: SessionId,
    ) -> ProjectionHealth: ...

    def list_tool_calls(
        self,
        session_id: SessionId,
        *,
        status: ToolExecutionStatus | None = None,
    ) -> list[ToolCallRecord]: ...

    def list_approvals(
        self,
        session_id: SessionId,
        *,
        status: ApprovalStatus | None = None,
    ) -> list[ApprovalRecord]: ...

    def list_turn_metrics(
        self,
        session_id: SessionId,
        *,
        limit: int | None = None,
    ) -> list[TurnMetricsRecord]: ...

    def resolve_fork_point(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId | None = None,
    ) -> ResolvedForkPoint: ...

    def build_imported_transcript_events(
        self,
        session_id: SessionId,
        fork_point: ResolvedForkPoint,
    ) -> list[EventEnvelope]: ...


@runtime_checkable
class ArtifactRepository(Protocol):
    """File-backed artifact storage contract for runtime services."""

    def write_text_artifact(
        self,
        session_id: SessionId,
        content: str,
        *,
        suffix: str,
    ) -> StoredArtifact: ...

    def write_binary_artifact(
        self,
        session_id: SessionId,
        content: bytes,
        *,
        suffix: str,
    ) -> StoredArtifact: ...

    def read_text_artifact(
        self,
        relative_path: Path,
        *,
        encoding: str = "utf-8",
    ) -> str: ...

    def read_binary_artifact(self, relative_path: Path) -> bytes: ...

    def record_text_artifact(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        tool_call_id: ToolCallId,
        artifact_kind: str,
        content: str,
        *,
        suffix: str,
    ) -> tuple[StoredArtifact, EventEnvelope]: ...

    def record_binary_artifact(
        self,
        session_id: SessionId,
        turn_id: TurnId,
        tool_call_id: ToolCallId,
        artifact_kind: str,
        content: bytes,
        *,
        suffix: str,
    ) -> tuple[StoredArtifact, EventEnvelope]: ...


@runtime_checkable
class SessionService(Protocol):
    """Top-level orchestration contract used by CLI, runtime, and web layers."""

    async def start_session(self, config: SessionConfig) -> SessionState: ...

    async def fork_session(
        self,
        session_id: SessionId,
        *,
        turn_id: TurnId | None = None,
        branch_label: str | None = None,
    ) -> ForkedSession: ...

    async def record_runtime_note(
        self,
        session_id: SessionId,
        *,
        category: str,
        message: str,
    ) -> None: ...

    async def resume_session(self, session_id: SessionId) -> SessionState: ...

    async def stop_session(
        self,
        session_id: SessionId,
        reason: str = "stopped",
    ) -> SessionState: ...

    async def submit_user_message(self, session_id: SessionId, text: str) -> None: ...

    async def resolve_approval(
        self,
        session_id: SessionId,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None: ...

    async def provide_user_answer(
        self,
        session_id: SessionId,
        question_id: QuestionId,
        answer: str,
    ) -> None: ...
