"""Tests for the reusable interactive terminal session client boundary."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import cast

import httpx
import pytest

from glassbox.cli.interactive_client import DaemonInteractiveSessionClient
from glassbox.cli.interactive_client import InteractiveClientError
from glassbox.cli.interactive_client import InteractiveClientErrorKind
from glassbox.cli.interactive_client import LocalInteractiveSessionClient
from glassbox.core.events import EventEnvelope
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_session_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.core.models import SessionRecord
from glassbox.core.models import SessionState
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.context import RuntimeInfrastructure
from glassbox.runtime.context import RuntimeRepositories
from glassbox.runtime.context import RuntimeServices
from glassbox.runtime.provider_config import RuntimeProviderConfig
from glassbox.runtime.transport import RuntimeEventSubscription
from glassbox.runtime.transport import RuntimeEventTransport
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.services import SessionService


def test_local_client_fetch_snapshot_reads_repository_state(tmp_path: Path) -> None:
    session_id = new_session_id()
    question_id = new_question_id()
    turn_id = new_turn_id()
    repository = _FakeSessionRepository(
        session_id=session_id,
        state=SessionState(
            session_id=session_id,
            status=SessionStatus.AWAITING_USER_INPUT,
            last_sequence=3,
            pending_question_id=question_id,
        ),
        record=SessionRecord(
            session_id=session_id,
            status=SessionStatus.AWAITING_USER_INPUT,
            created_at=_now(),
            updated_at=_now(),
            cwd=tmp_path,
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            last_sequence=3,
        ),
        events=[
            EventEnvelope(
                session_id=session_id,
                sequence=3,
                payload=UserQuestionAsked(
                    question_id=question_id,
                    turn_id=turn_id,
                    tool_call_id=new_tool_call_id(),
                    provider_tool_call_id="provider-ask-1",
                    question="What colour should I use?",
                ),
            )
        ],
    )
    service = _FakeSessionService()
    client = LocalInteractiveSessionClient(
        runtime_context=_runtime_context(tmp_path, repository, service),
        session_id=session_id,
        dashboard_url="http://127.0.0.1:8765/",
    )

    snapshot = asyncio.run(client.fetch_snapshot())

    assert snapshot.session_id == session_id
    assert snapshot.state.status == SessionStatus.AWAITING_USER_INPUT
    assert snapshot.model_name == "openai:gpt-5.4"
    assert snapshot.dashboard_url == "http://127.0.0.1:8765/"
    assert snapshot.pending_question_text == "What colour should I use?"


def test_local_client_mutations_delegate_to_session_service(tmp_path: Path) -> None:
    session_id = new_session_id()
    question_id = new_question_id()
    approval_id = new_approval_id()
    repository = _FakeSessionRepository(
        session_id=session_id,
        state=SessionState(session_id=session_id, status=SessionStatus.RUNNING),
        record=None,
        events=[],
    )
    service = _FakeSessionService()
    client = LocalInteractiveSessionClient(
        runtime_context=_runtime_context(tmp_path, repository, service),
        session_id=session_id,
    )

    asyncio.run(client.submit_message("hello"))
    asyncio.run(client.submit_answer(question_id, "blue"))
    asyncio.run(
        client.resolve_approval(
            approval_id,
            ApprovalDecision.APPROVED,
        )
    )

    assert service.calls == [
        ("message", session_id, "hello"),
        ("answer", session_id, question_id, "blue"),
        ("approval", session_id, approval_id, ApprovalDecision.APPROVED),
    ]


def test_daemon_client_maps_conflict_response_to_common_error() -> None:
    session_id = new_session_id()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/sessions/{session_id}/messages"
        return httpx.Response(409, json={"detail": "session is busy"})

    http_client = httpx.AsyncClient(
        base_url="http://127.0.0.1:8765",
        transport=httpx.MockTransport(handler),
    )
    client = DaemonInteractiveSessionClient(
        http_client,
        session_id,
        "http://127.0.0.1:8765/",
    )

    with pytest.raises(InteractiveClientError) as exc_info:
        asyncio.run(client.submit_message("hello"))

    asyncio.run(client.aclose())
    assert exc_info.value.kind == InteractiveClientErrorKind.CONFLICT
    assert str(exc_info.value) == "session is busy"


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _runtime_context(
    tmp_path: Path,
    repository: _FakeSessionRepository,
    service: _FakeSessionService,
) -> RuntimeContext:
    return RuntimeContext(
        repositories=RuntimeRepositories(
            sessions=cast(SessionRepository, repository),
            artifacts=cast(ArtifactRepository, object()),
        ),
        services=RuntimeServices(session_service=cast(SessionService, service)),
        infrastructure=RuntimeInfrastructure(
            event_bus=cast(RuntimeEventTransport[EventEnvelope], _FakeEventTransport()),
            artifacts_root=tmp_path / ".glassbox" / "artifacts",
            provider_config=RuntimeProviderConfig(),
        ),
    )


@dataclass(slots=True)
class _FakeSessionRepository:
    session_id: Any
    state: SessionState | None
    record: SessionRecord | None
    events: list[EventEnvelope]

    def get_session_state(self, session_id: Any) -> SessionState | None:
        assert session_id == self.session_id
        return self.state

    def get_session(self, session_id: Any) -> SessionRecord | None:
        assert session_id == self.session_id
        return self.record

    def read_session_events(self, session_id: Any) -> list[EventEnvelope]:
        assert session_id == self.session_id
        return self.events

    def read_session_events_after(
        self,
        session_id: Any,
        after_sequence: int,
    ) -> list[EventEnvelope]:
        assert session_id == self.session_id
        return [event for event in self.events if event.sequence > after_sequence]


@dataclass(slots=True)
class _FakeSessionService:
    calls: list[tuple[Any, ...]]

    def __init__(self) -> None:
        self.calls = []

    async def submit_user_message(self, session_id: Any, text: str) -> None:
        self.calls.append(("message", session_id, text))

    async def provide_user_answer(
        self,
        session_id: Any,
        question_id: Any,
        answer: str,
    ) -> None:
        self.calls.append(("answer", session_id, question_id, answer))

    async def resolve_approval(
        self,
        session_id: Any,
        approval_id: Any,
        decision: ApprovalDecision,
    ) -> None:
        self.calls.append(("approval", session_id, approval_id, decision))


class _FakeEventTransport:
    @asynccontextmanager
    async def subscribe(
        self,
    ) -> AsyncIterator[RuntimeEventSubscription[EventEnvelope]]:
        yield cast(RuntimeEventSubscription[EventEnvelope], _EmptySubscription())

    def publish(self, event: EventEnvelope) -> None:
        return None

    def stats(self) -> Any:
        return object()


class _EmptySubscription:
    def __aiter__(self) -> AsyncIterator[EventEnvelope]:
        return self

    async def __anext__(self) -> EventEnvelope:
        raise StopAsyncIteration

    async def get(self) -> EventEnvelope:
        raise StopAsyncIteration

    async def aclose(self) -> None:
        return None
