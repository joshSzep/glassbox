"""HTTP integration tests for session message and question-answer endpoints."""

import asyncio
import sqlite3
from pathlib import Path
from typing import Any
from typing import cast

import httpx
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from glassbox.core import EventEnvelope
from glassbox.core import SessionConfig
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_question_id
from glassbox.core.types import ApprovalDecision
from glassbox.llm import ModelProviderConfig
from glassbox.llm import PydanticAIModelAdapter
from glassbox.llm import PydanticAIModelExecutor
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.context import RuntimeInfrastructure
from glassbox.runtime.context import RuntimeRepositories
from glassbox.runtime.context import RuntimeServices
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.services import SessionService
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import ToolRuntime
from glassbox.tools import build_ask_user_tool_registry
from glassbox.web import create_app


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context), runtime_context


def _ask_user_then_text_response(messages: list, _agent_info: Any) -> ModelResponse:
    saw_tool_return = False
    answer: str | None = None

    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name == "ask_user":
                    saw_tool_return = True
                    assert isinstance(part.content, dict)
                    answer = str(part.content["answer"])

    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="ask_user",
                    args={"question": "What colour should I use?"},
                    tool_call_id="provider-ask-1",
                )
            ]
        )

    return ModelResponse(parts=[TextPart(content=f"I will use: {answer}")])


def _make_ask_user_app(tmp_path: Path, connection: sqlite3.Connection):
    repository = SQLiteSessionRepository(connection)
    artifacts_root = tmp_path / ".glassbox" / "artifacts"
    artifact_repository = FilesystemArtifactRepository(connection, artifacts_root)
    bus: EventBus[EventEnvelope] = EventBus()
    turn_engine = TurnEngine(
        repository,
        bus,
        TurnContextBuilder(repository),
        lambda _session: PydanticAIModelAdapter(
            ModelProviderConfig(provider="openai", model_name="gpt-5.4")
        ),
        lambda _session: PydanticAIModelExecutor(
            FunctionModel(
                function=_ask_user_then_text_response,
                model_name="openai:gpt-5.4",
            )
        ),
        lambda session: ToolRuntime(
            build_ask_user_tool_registry(session.cwd),
            ToolPolicyEngine(),
            ToolPolicyContext(
                workspace_root=session.cwd,
                approval_mode=ApprovalMode.NEVER,
            ),
        ),
    )
    supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
    runtime_context = RuntimeContext(
        repositories=RuntimeRepositories(
            sessions=repository,
            artifacts=artifact_repository,
        ),
        services=RuntimeServices(session_service=supervisor),
        infrastructure=RuntimeInfrastructure(
            event_bus=bus,
            artifacts_root=artifacts_root,
        ),
    )
    return create_app(runtime_context), runtime_context


def test_post_session_message_returns_404_for_unknown_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, _ = _make_app(tmp_path, connection)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    "/sessions/00000000-0000-0000-0000-000000000099/messages",
                    json={"text": "Hello"},
                )

            assert response.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_cancel_returns_404_for_unknown_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, _ = _make_app(tmp_path, connection)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    "/sessions/00000000-0000-0000-0000-000000000099/cancel",
                    json={},
                )

            assert response.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_cancel_calls_session_service(tmp_path: Path) -> None:
    class FakeSessionService:
        def __init__(self) -> None:
            self.calls: list[tuple[SessionId, TurnId | None, str, str | None]] = []

        async def cancel_turn(
            self,
            session_id: SessionId,
            turn_id: TurnId | None = None,
            *,
            requested_by: str = "operator",
            reason: str | None = None,
        ) -> None:
            self.calls.append((session_id, turn_id, requested_by, reason))

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            state = await runtime_context.services.session_service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            fake_service = FakeSessionService()
            app = create_app(
                RuntimeContext(
                    repositories=runtime_context.repositories,
                    services=RuntimeServices(
                        session_service=cast(SessionService, fake_service)
                    ),
                    infrastructure=runtime_context.infrastructure,
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/cancel",
                    json={"reason": "user request", "turn_id": None},
                )

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            assert fake_service.calls == [
                (state.session_id, None, "api", "user request")
            ]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_cancel_returns_409_for_non_cancellable_session(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            state = await runtime_context.services.session_service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/cancel",
                    json={},
                )

            assert response.status_code == 409
            assert "no cancellable active turn" in response.json()["detail"]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_mutation_endpoints_align_conflict_status_and_copy(tmp_path: Path) -> None:
    class ConflictingSessionService:
        async def submit_user_message(self, *_args) -> None:
            raise ValueError("concurrent mutation rejected by live owner")

        async def provide_user_answer(self, *_args) -> None:
            raise ValueError("concurrent mutation rejected by live owner")

        async def resolve_approval(self, *_args) -> None:
            raise ValueError("concurrent mutation rejected by live owner")

        async def fork_session(self, *_args, **_kwargs):
            raise ValueError("concurrent mutation rejected by live owner")

        async def cancel_turn(self, *_args, **_kwargs) -> None:
            raise ValueError("concurrent mutation rejected by live owner")

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            runtime_context = _build_runtime_context(connection, tmp_path)
            state = await runtime_context.services.session_service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            app = create_app(
                RuntimeContext(
                    repositories=runtime_context.repositories,
                    services=RuntimeServices(
                        session_service=cast(
                            SessionService,
                            ConflictingSessionService(),
                        )
                    ),
                    infrastructure=runtime_context.infrastructure,
                )
            )
            question_id = new_question_id()
            approval_id = new_approval_id()

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                responses = [
                    await client.post(
                        f"/sessions/{state.session_id}/messages",
                        json={"text": "another prompt"},
                    ),
                    await client.post(
                        f"/sessions/{state.session_id}/questions/{question_id}",
                        json={"answer": "blue"},
                    ),
                    await client.post(
                        f"/sessions/{state.session_id}/approvals/{approval_id}",
                        json={"decision": ApprovalDecision.APPROVED.value},
                    ),
                    await client.post(
                        f"/sessions/{state.session_id}/approvals/{approval_id}",
                        json={"decision": ApprovalDecision.DENIED.value},
                    ),
                    await client.post(
                        f"/sessions/{state.session_id}/fork",
                        json={"branch_label": "parallel"},
                    ),
                    await client.post(
                        f"/sessions/{state.session_id}/cancel",
                        json={"reason": "parallel request"},
                    ),
                ]

            assert {response.status_code for response in responses} == {409}
            assert {response.json()["detail"] for response in responses} == {
                "concurrent mutation rejected by live owner"
            }
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_message_submits_turn_and_updates_transcript(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)

            repo = runtime_context.repositories.sessions
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/messages",
                    json={"text": "Inspect the repository"},
                )

            transcript = repo.list_transcript_messages(state.session_id)

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            assert transcript[-2].role == "user"
            assert transcript[-2].parts[0].text == "Inspect the repository"
            assert transcript[-1].role == "assistant"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_message_returns_409_for_non_actionable_session(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_ask_user_app(tmp_path, connection)

            repo = runtime_context.repositories.sessions
            state = await runtime_context.services.session_service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="never",
                )
            )
            await runtime_context.services.session_service.submit_user_message(
                state.session_id,
                "Pick a colour.",
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/messages",
                    json={"text": "another message"},
                )

            assert response.status_code == 409
            assert "cannot accept input" in response.json()["detail"]
            assert repo.get_session_state(state.session_id) is not None
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_message_rejects_invalid_request_schema(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)

            repo = runtime_context.repositories.sessions
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/messages",
                    json={"prompt": "Inspect the repository"},
                )

            assert response.status_code == 422
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_answer_submits_answer_and_resumes_turn(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_ask_user_app(tmp_path, connection)
            state = await runtime_context.services.session_service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="never",
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                message_response = await client.post(
                    f"/sessions/{state.session_id}/messages",
                    json={"text": "Pick a colour."},
                )

                repo = runtime_context.repositories.sessions
                question = next(
                    event.payload
                    for event in repo.read_session_events(state.session_id)
                    if isinstance(event.payload, UserQuestionAsked)
                )

                answer_response = await client.post(
                    f"/sessions/{state.session_id}/questions/{question.question_id}",
                    json={"answer": "blue"},
                )

            final_state = repo.get_session_state(state.session_id)
            transcript = repo.list_transcript_messages(state.session_id)

            assert message_response.status_code == 200
            assert answer_response.status_code == 200
            assert answer_response.json() == {"status": "ok"}
            assert final_state is not None
            assert final_state.status == "running"
            assert final_state.pending_question_id is None
            assert transcript[-1].role == "assistant"
            assert transcript[-1].parts[0].text == "I will use: blue"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_answer_returns_404_for_unknown_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, _ = _make_app(tmp_path, connection)
            question_id = new_question_id()

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/00000000-0000-0000-0000-000000000099/questions/{question_id}",
                    json={"answer": "blue"},
                )

            assert response.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_answer_returns_409_for_unknown_question_id(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_ask_user_app(tmp_path, connection)
            state = await runtime_context.services.session_service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="never",
                )
            )
            await runtime_context.services.session_service.submit_user_message(
                state.session_id,
                "Pick a colour.",
            )
            unknown_question_id = new_question_id()

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/questions/{unknown_question_id}",
                    json={"answer": "blue"},
                )

            assert response.status_code == 409
            assert response.json()["detail"] == (
                f"unknown question_id: {unknown_question_id}"
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_answer_returns_409_when_session_not_awaiting_input(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)

            repo = runtime_context.repositories.sessions
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            question_id = new_question_id()

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/questions/{question_id}",
                    json={"answer": "blue"},
                )

            assert response.status_code == 409
            assert response.json()["detail"] == (
                f"session {state.session_id} is not awaiting user input"
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_answer_rejects_invalid_request_schema(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_ask_user_app(tmp_path, connection)
            state = await runtime_context.services.session_service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="never",
                )
            )
            await runtime_context.services.session_service.submit_user_message(
                state.session_id,
                "Pick a colour.",
            )
            question = next(
                event.payload
                for event in runtime_context.repositories.sessions.read_session_events(
                    state.session_id
                )
                if isinstance(event.payload, UserQuestionAsked)
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/questions/{question.question_id}",
                    json={"text": "blue"},
                )

            assert response.status_code == 422
        finally:
            connection.close()

    asyncio.run(scenario())
