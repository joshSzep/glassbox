"""Live dashboard integration coverage for chat-owned sessions (GBX-174)."""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
from collections.abc import AsyncIterator
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast
from uuid import UUID

import httpx
import pytest
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.messages import UserPromptPart
from pydantic_ai.models.function import FunctionModel

from glassbox.cli.interactive_commands import _chat_command_async
from glassbox.core import EventEnvelope
from glassbox.core import SessionState
from glassbox.llm import ModelProviderConfig
from glassbox.llm import PydanticAIModelAdapter
from glassbox.llm import PydanticAIModelExecutor
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.context import RuntimeInfrastructure
from glassbox.runtime.context import RuntimeRepositories
from glassbox.runtime.context import RuntimeServices
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import ToolRuntime
from glassbox.tools import build_ask_user_tool_registry
from glassbox.tools import build_patch_tool_registry
from glassbox.tools import build_read_only_tool_registry
from glassbox.web import WebServerConfig
from glassbox.web import create_app
from glassbox.web.routes.events import stream_session_events

ModelFn = Callable[[list[Any], Any], ModelResponse]
ToolRegistryFactory = Callable[[Path], Any]


@dataclass(slots=True)
class _ChatOwnedDashboardServer:
    app: Any
    config: WebServerConfig
    started: asyncio.Event
    stopped: asyncio.Event

    @classmethod
    def create(
        cls,
        runtime_context: RuntimeContext,
        *,
        host: str,
        port: int,
    ) -> _ChatOwnedDashboardServer:
        return cls(
            app=create_app(runtime_context),
            config=WebServerConfig(host=host, port=port),
            started=asyncio.Event(),
            stopped=asyncio.Event(),
        )

    async def start(self) -> None:
        self.started.set()

    async def stop(self) -> None:
        self.stopped.set()


@dataclass(slots=True)
class _RunningChat:
    task: asyncio.Task[int]
    runtime_context: RuntimeContext
    server: _ChatOwnedDashboardServer
    session_id: UUID
    release_input: asyncio.Event


class _NeverDisconnectedRequest:
    async def is_disconnected(self) -> bool:
        return False


async def _wait_for_chat_condition(
    chat_task: asyncio.Task[int],
    condition: Callable[[], bool],
    *,
    timeout: float = 2.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not condition():
        if chat_task.done():
            await chat_task
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError("timed out waiting for chat condition")
        await asyncio.sleep(0.01)


def _chat_args(
    tmp_path: Path,
    *,
    prompt: str | None,
    approval_mode: str,
) -> argparse.Namespace:
    return argparse.Namespace(
        prompt=prompt,
        cwd=str(tmp_path),
        db_path=str(tmp_path / ".glassbox" / "glassbox.sqlite3"),
        model_name="openai:gpt-5.4",
        approval_mode=approval_mode,
        dashboard_host=None,
        dashboard_port=None,
        no_dashboard=False,
    )


def _parse_sse_frames(
    chunk: str | bytes | memoryview[int],
) -> list[dict[str, str]]:
    if isinstance(chunk, str):
        text = chunk
    else:
        text = bytes(chunk).decode()
    frames: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("data:"):
            current["data"] = line[len("data:") :].strip()
        elif line.startswith("event:"):
            current["event"] = line[len("event:") :].strip()
        elif line.startswith("id:"):
            current["id"] = line[len("id:") :].strip()
        elif line == "" and current:
            frames.append(current)
            current = {}
    if current:
        frames.append(current)
    return frames


async def _collect_sse_frames_until(
    body_iterator: AsyncIterator[str | bytes | memoryview[int]],
    *,
    expected_event_types: set[str],
    timeout: float = 2.0,
) -> list[dict[str, str]]:
    frames: list[dict[str, str]] = []
    seen_event_types: set[str] = set()
    while not expected_event_types.issubset(seen_event_types):
        chunk = await asyncio.wait_for(anext(body_iterator), timeout=timeout)
        for frame in _parse_sse_frames(chunk):
            frames.append(frame)
            event_type = frame.get("event")
            if event_type is not None:
                seen_event_types.add(event_type)
    return frames


async def _close_body_iterator(
    body_iterator: AsyncIterator[str | bytes | memoryview[int]],
) -> None:
    close = getattr(body_iterator, "aclose", None)
    if close is not None:
        await close()


def _session_state(repository, session_id: UUID) -> SessionState:
    state = repository.get_session_state(session_id)
    assert state is not None
    return state


def _text_only_response(messages: list[Any], _agent_info: Any) -> ModelResponse:
    prompt = ""
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, UserPromptPart):
                prompt = part.content

    return ModelResponse(parts=[TextPart(content=f"I received your request: {prompt}")])


def _ask_user_then_text_response(
    messages: list[Any],
    _agent_info: Any,
) -> ModelResponse:
    saw_tool_return = False
    answer: str | None = None

    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name == "ask_user":
                saw_tool_return = True
                assert isinstance(part.content, dict)
                answer_payload = cast(dict[str, Any], part.content)
                answer = str(answer_payload["answer"])

    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="ask_user",
                    args={"question": "What colour should I use?"},
                    tool_call_id="provider-ask-live-dashboard-1",
                )
            ]
        )

    return ModelResponse(parts=[TextPart(content=f"I will use: {answer}")])


def _patch_then_text_response(
    messages: list[Any],
    _agent_info: Any,
) -> ModelResponse:
    saw_tool_return = False

    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name == "apply_patch":
                saw_tool_return = True

    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="apply_patch",
                    args={
                        "path": "hello.txt",
                        "old_text": "",
                        "new_text": "Hello from live dashboard chat.\n",
                    },
                    tool_call_id="provider-patch-live-dashboard-1",
                )
            ]
        )

    return ModelResponse(parts=[TextPart(content="Patch applied.")])


def _make_runtime_context(
    tmp_path: Path,
    *,
    model_fn: ModelFn,
    tool_registry_factory: ToolRegistryFactory,
    approval_mode: ApprovalMode,
) -> tuple[RuntimeContext, sqlite3.Connection]:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)

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
            FunctionModel(function=model_fn, model_name="openai:gpt-5.4")
        ),
        lambda session: ToolRuntime(
            tool_registry_factory(session.cwd),
            ToolPolicyEngine(),
            ToolPolicyContext(
                workspace_root=session.cwd,
                approval_mode=approval_mode,
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
    return runtime_context, connection


def _make_echo_runtime_context(
    tmp_path: Path,
) -> tuple[RuntimeContext, sqlite3.Connection]:
    return _make_runtime_context(
        tmp_path,
        model_fn=_text_only_response,
        tool_registry_factory=build_read_only_tool_registry,
        approval_mode=ApprovalMode.NEVER,
    )


def _make_ask_user_runtime_context(
    tmp_path: Path,
) -> tuple[RuntimeContext, sqlite3.Connection]:
    return _make_runtime_context(
        tmp_path,
        model_fn=_ask_user_then_text_response,
        tool_registry_factory=build_ask_user_tool_registry,
        approval_mode=ApprovalMode.NEVER,
    )


def _make_approval_runtime_context(
    tmp_path: Path,
) -> tuple[RuntimeContext, sqlite3.Connection]:
    return _make_runtime_context(
        tmp_path,
        model_fn=_patch_then_text_response,
        tool_registry_factory=build_patch_tool_registry,
        approval_mode=ApprovalMode.CONFIRM,
    )


async def _start_chat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runtime_context: RuntimeContext,
    *,
    prompt: str | None,
    approval_mode: str,
) -> _RunningChat:
    built_servers: list[_ChatOwnedDashboardServer] = []
    input_waiting = asyncio.Event()
    release_input = asyncio.Event()

    def fake_build_web_server(
        inner_runtime_context: RuntimeContext,
        *,
        host: str,
        port: int,
    ) -> _ChatOwnedDashboardServer:
        server = _ChatOwnedDashboardServer.create(
            inner_runtime_context,
            host=host,
            port=port,
        )
        built_servers.append(server)
        return server

    async def fake_read_interactive_input(_prompt: str) -> str:
        input_waiting.set()
        await release_input.wait()
        return "/exit"

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )
    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.build_web_server",
        fake_build_web_server,
    )
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input_async",
        fake_read_interactive_input,
    )

    chat_task = asyncio.create_task(
        _chat_command_async(
            _chat_args(
                tmp_path,
                prompt=prompt,
                approval_mode=approval_mode,
            )
        )
    )

    await _wait_for_chat_condition(chat_task, lambda: len(built_servers) == 1)
    server = built_servers[0]
    await server.started.wait()
    repository = runtime_context.repositories.sessions
    await _wait_for_chat_condition(
        chat_task, lambda: len(repository.list_sessions()) == 1
    )
    session_id = repository.list_sessions()[0].session_id
    await _wait_for_chat_condition(chat_task, input_waiting.is_set)

    return _RunningChat(
        task=chat_task,
        runtime_context=runtime_context,
        server=server,
        session_id=session_id,
        release_input=release_input,
    )


async def _finish_chat(chat: _RunningChat) -> int:
    chat.release_input.set()
    exit_code = await asyncio.wait_for(chat.task, timeout=2.0)
    assert chat.server.stopped.is_set()
    return exit_code


def test_chat_owned_dashboard_snapshot_exposes_pending_question_and_allows_web_answer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
        try:
            chat = await _start_chat(
                tmp_path,
                monkeypatch,
                runtime_context,
                prompt="Pick a colour.",
                approval_mode="never",
            )

            repository = runtime_context.repositories.sessions
            await _wait_for_chat_condition(
                chat.task,
                lambda: (
                    _session_state(repository, chat.session_id).pending_question_id
                    is not None
                ),
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=chat.server.app),
                base_url="http://testserver",
            ) as client:
                snapshot = await client.get(f"/sessions/{chat.session_id}")

                assert snapshot.status_code == 200
                body = snapshot.json()
                assert body["status"] == "awaiting_user_input"
                assert body["dashboard_url"] == chat.server.config.dashboard_url
                assert body["pending_question_text"] == "What colour should I use?"
                assert body["pending_question_id"] is not None

                answer_response = await client.post(
                    f"/sessions/{chat.session_id}/questions/{body['pending_question_id']}",
                    json={"answer": "blue"},
                )

                assert answer_response.status_code == 200
                assert answer_response.json() == {"status": "ok"}

                await _wait_for_chat_condition(
                    chat.task,
                    lambda: (
                        _session_state(repository, chat.session_id).pending_question_id
                        is None
                        and repository.list_transcript_messages(chat.session_id)[-1]
                        .parts[0]
                        .text
                        == "I will use: blue"
                    ),
                )

                updated_snapshot = await client.get(f"/sessions/{chat.session_id}")
                assert updated_snapshot.status_code == 200
                updated_body = updated_snapshot.json()
                assert updated_body["status"] == "running"
                assert updated_body["pending_question_id"] is None
                assert (
                    updated_body["transcript"][-1]["parts"][0]["text"]
                    == "I will use: blue"
                )

            assert await _finish_chat(chat) == 0
        finally:
            connection.close()

    asyncio.run(scenario())


def test_chat_owned_dashboard_sse_streams_live_events_during_multi_turn_chat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        runtime_context, connection = _make_echo_runtime_context(tmp_path)
        try:
            chat = await _start_chat(
                tmp_path,
                monkeypatch,
                runtime_context,
                prompt="Inspect the repository",
                approval_mode="never",
            )

            repository = runtime_context.repositories.sessions
            await _wait_for_chat_condition(
                chat.task,
                lambda: len(repository.list_transcript_messages(chat.session_id)) >= 2,
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=chat.server.app),
                base_url="http://testserver",
            ) as client:
                snapshot = await client.get(f"/sessions/{chat.session_id}")
                assert snapshot.status_code == 200
                snapshot_body = snapshot.json()
                assert (
                    snapshot_body["dashboard_url"] == chat.server.config.dashboard_url
                )
                assert (
                    snapshot_body["transcript"][0]["parts"][0]["text"]
                    == "Inspect the repository"
                )
                assert (
                    snapshot_body["transcript"][-1]["parts"][0]["text"]
                    == "I received your request: Inspect the repository"
                )

                last_sequence = repository.read_session_events(chat.session_id)[
                    -1
                ].sequence
                sse_response = await stream_session_events(
                    chat.session_id,
                    runtime_context,
                    cast(Any, _NeverDisconnectedRequest()),
                    after=last_sequence,
                )
                body_iterator = cast(
                    AsyncIterator[str | bytes | memoryview[int]],
                    sse_response.body_iterator,
                )
                collector = asyncio.create_task(
                    _collect_sse_frames_until(
                        body_iterator,
                        expected_event_types={
                            "UserMessageReceived",
                            "TurnStarted",
                            "ModelCallCompleted",
                        },
                    )
                )

                await _wait_for_chat_condition(
                    chat.task,
                    lambda: (
                        runtime_context.infrastructure.event_bus.stats().subscriber_count
                        >= 2
                    ),
                )

                message_response = await client.post(
                    f"/sessions/{chat.session_id}/messages",
                    json={"text": "Now summarize the tests."},
                )
                assert message_response.status_code == 200
                assert message_response.json() == {"status": "ok"}

                frames = await collector
                await _close_body_iterator(body_iterator)

                assert {frame["event"] for frame in frames} >= {
                    "UserMessageReceived",
                    "TurnStarted",
                    "ModelCallCompleted",
                }

                await _wait_for_chat_condition(
                    chat.task,
                    lambda: (
                        repository.list_transcript_messages(chat.session_id)[-1]
                        .parts[0]
                        .text
                        == "I received your request: Now summarize the tests."
                    ),
                )

            assert await _finish_chat(chat) == 0
        finally:
            connection.close()

    asyncio.run(scenario())


def test_chat_owned_dashboard_allows_web_approval_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        runtime_context, connection = _make_approval_runtime_context(tmp_path)
        try:
            chat = await _start_chat(
                tmp_path,
                monkeypatch,
                runtime_context,
                prompt="Apply the patch.",
                approval_mode="confirm",
            )

            repository = runtime_context.repositories.sessions
            await _wait_for_chat_condition(
                chat.task,
                lambda: (
                    _session_state(repository, chat.session_id).pending_approval_id
                    is not None
                ),
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=chat.server.app),
                base_url="http://testserver",
            ) as client:
                snapshot = await client.get(f"/sessions/{chat.session_id}")

                assert snapshot.status_code == 200
                body = snapshot.json()
                assert body["status"] == "awaiting_approval"
                assert body["dashboard_url"] == chat.server.config.dashboard_url
                assert body["pending_approval_id"] is not None
                assert len(body["pending_approvals"]) == 1

                approval_response = await client.post(
                    f"/sessions/{chat.session_id}/approvals/{body['pending_approval_id']}",
                    json={"decision": "approved"},
                )

                assert approval_response.status_code == 200
                assert approval_response.json() == {"status": "ok"}

                await _wait_for_chat_condition(
                    chat.task,
                    lambda: (
                        _session_state(repository, chat.session_id).pending_approval_id
                        is None
                        and repository.list_transcript_messages(chat.session_id)[-1]
                        .parts[0]
                        .text
                        == "Patch applied."
                    ),
                )

                updated_snapshot = await client.get(f"/sessions/{chat.session_id}")
                assert updated_snapshot.status_code == 200
                updated_body = updated_snapshot.json()
                assert updated_body["status"] == "running"
                assert updated_body["pending_approval_id"] is None
                assert (
                    updated_body["transcript"][-1]["parts"][0]["text"]
                    == "Patch applied."
                )

            assert await _finish_chat(chat) == 0
        finally:
            connection.close()

    asyncio.run(scenario())
