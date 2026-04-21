"""Unit tests for service contracts and runtime context wiring."""

import asyncio
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from glassbox.core import (
    ApprovalDecision,
    EventEnvelope,
    MessagePart,
    SessionConfig,
    SessionRecord,
    SessionStarted,
    SessionState,
    SessionStatus,
    TranscriptMessage,
    new_artifact_id,
    new_session_id,
)
from glassbox.runtime import (
    EventBus,
    RuntimeContext,
    RuntimeInfrastructure,
    RuntimeRepositories,
    RuntimeServices,
)
from glassbox.services import ArtifactRepository, SessionRepository, SessionService
from glassbox.store import StoredArtifact


class FakeSessionRepository:
    def create_session(
        self,
        session_id,
        config,
        *,
        status=SessionStatus.IDLE,
        created_at=None,
        updated_at=None,
        last_sequence=0,
    ) -> SessionRecord:
        timestamp = created_at or datetime.now(UTC)
        return SessionRecord(
            session_id=session_id,
            status=status,
            created_at=timestamp,
            updated_at=updated_at or timestamp,
            cwd=config.cwd,
            model_name=config.model_name,
            approval_mode=config.approval_mode,
            last_sequence=last_sequence,
        )

    def get_session(self, session_id):
        return None

    def get_session_state(self, session_id):
        return None

    def list_transcript_messages(self, session_id):
        return [
            TranscriptMessage(
                message_id=new_session_id(),
                role="user",
                parts=[MessagePart(kind="text", text="hello")],
                created_at=datetime.now(UTC),
            )
        ]

    def list_sessions(self, *, status=None, limit=None):
        return []

    def update_session(
        self,
        session_id,
        *,
        status=None,
        updated_at=None,
        cwd=None,
        model_name=None,
        approval_mode=None,
        last_sequence=None,
    ) -> SessionRecord:
        timestamp = updated_at or datetime.now(UTC)
        return SessionRecord(
            session_id=session_id,
            status=status or SessionStatus.RUNNING,
            created_at=timestamp,
            updated_at=timestamp,
            cwd=cwd or Path("/tmp"),
            model_name=model_name or "openai:gpt-5.4",
            approval_mode=approval_mode or "confirm",
            last_sequence=0 if last_sequence is None else last_sequence,
        )

    def append_event(self, event: EventEnvelope) -> EventEnvelope:
        return event

    def append_events(self, events):
        return list(events)

    def read_session_events(self, session_id):
        return []

    def read_session_events_after(self, session_id, after_sequence):
        return []

    def read_events_by_correlation_id(
        self,
        session_id,
        *,
        turn_id=None,
        message_id=None,
        tool_call_id=None,
        approval_id=None,
    ):
        return []

    def rebuild_session_projections(self, session_id) -> None:
        return None


class FakeArtifactRepository:
    def _artifact_event(self, session_id) -> EventEnvelope:
        return EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=SessionStarted(
                cwd="/tmp",
                model_name="openai:gpt-5.4",
                approval_mode="confirm",
            ),
        )

    def write_text_artifact(self, session_id, content, *, suffix):
        return StoredArtifact(
            artifact_id=new_artifact_id(),
            session_id=session_id,
            relative_path=Path("artifact.log"),
            absolute_path=Path("/tmp/artifact.log"),
        )

    def write_binary_artifact(self, session_id, content, *, suffix):
        return StoredArtifact(
            artifact_id=new_artifact_id(),
            session_id=session_id,
            relative_path=Path("artifact.bin"),
            absolute_path=Path("/tmp/artifact.bin"),
        )

    def read_text_artifact(self, relative_path: Path, *, encoding: str = "utf-8"):
        return "artifact"

    def read_binary_artifact(self, relative_path: Path):
        return b"artifact"

    def record_text_artifact(
        self,
        session_id,
        turn_id,
        tool_call_id,
        artifact_kind,
        content,
        *,
        suffix,
    ):
        artifact = self.write_text_artifact(session_id, content, suffix=suffix)
        return artifact, self._artifact_event(session_id)

    def record_binary_artifact(
        self,
        session_id,
        turn_id,
        tool_call_id,
        artifact_kind,
        content,
        *,
        suffix,
    ):
        artifact = self.write_binary_artifact(session_id, content, suffix=suffix)
        return artifact, self._artifact_event(session_id)


class FakeSessionService:
    async def start_session(self, config: SessionConfig) -> SessionState:
        return SessionState(session_id=new_session_id(), status=SessionStatus.RUNNING)

    async def resume_session(self, session_id) -> SessionState:
        return SessionState(session_id=session_id, status=SessionStatus.RUNNING)

    async def stop_session(
        self,
        session_id,
        reason: str = "stopped",
    ) -> SessionState:
        return SessionState(session_id=session_id, status=SessionStatus.COMPLETED)

    async def submit_user_message(self, session_id, text: str) -> None:
        return None

    async def resolve_approval(
        self,
        session_id,
        approval_id,
        decision: ApprovalDecision,
    ) -> None:
        return None

    async def provide_user_answer(
        self,
        session_id,
        question_id,
        answer: str,
    ) -> None:
        return None


def test_runtime_contract_fakes_satisfy_protocols() -> None:
    assert isinstance(FakeSessionRepository(), SessionRepository)
    assert isinstance(FakeArtifactRepository(), ArtifactRepository)
    assert isinstance(FakeSessionService(), SessionService)


def test_runtime_context_groups_services_and_dependencies() -> None:
    session_repository = FakeSessionRepository()
    artifact_repository = FakeArtifactRepository()
    session_service = FakeSessionService()
    bus: EventBus[EventEnvelope] = EventBus()

    context = RuntimeContext(
        repositories=RuntimeRepositories(
            sessions=session_repository,
            artifacts=artifact_repository,
        ),
        services=RuntimeServices(session_service=session_service),
        infrastructure=RuntimeInfrastructure(
            event_bus=bus,
            artifacts_root=Path("/tmp/glassbox-artifacts"),
        ),
    )

    assert context.repositories.sessions is session_repository
    assert context.repositories.artifacts is artifact_repository
    assert context.services.session_service is session_service
    assert context.infrastructure.event_bus is bus
    assert context.infrastructure.artifacts_root == Path("/tmp/glassbox-artifacts")


def test_runtime_context_is_frozen() -> None:
    context = RuntimeContext(
        repositories=RuntimeRepositories(
            sessions=FakeSessionRepository(),
            artifacts=FakeArtifactRepository(),
        ),
        services=RuntimeServices(session_service=FakeSessionService()),
        infrastructure=RuntimeInfrastructure(
            event_bus=EventBus[EventEnvelope](),
            artifacts_root=Path("/tmp/glassbox-artifacts"),
        ),
    )

    with pytest.raises(FrozenInstanceError):
        context.__setattr__(
            "infrastructure",
            RuntimeInfrastructure(
                event_bus=EventBus[EventEnvelope](),
                artifacts_root=Path("/tmp/other"),
            ),
        )


def test_session_service_signature_uses_typed_models() -> None:
    service = FakeSessionService()
    config = SessionConfig(
        model_name="openai:gpt-5.4",
        cwd=Path("/tmp/glassbox"),
        approval_mode="confirm",
    )
    session_state = asyncio.run(service.start_session(config))

    assert isinstance(session_state, SessionState)
    assert session_state.status == SessionStatus.RUNNING
