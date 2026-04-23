"""Integration tests for the turn engine tool execution loop."""

import asyncio
import json
import logging
import sqlite3
from pathlib import Path

import pytest
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from glassbox.core import EventEnvelope, SessionConfig
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.llm import (
    ModelProviderConfig,
    PydanticAIModelAdapter,
    PydanticAIModelExecutor,
)
from glassbox.runtime import EventBus, SessionSupervisor, TurnContextBuilder, TurnEngine
from glassbox.store import (
    FilesystemArtifactRepository,
    SQLiteSessionRepository,
    initialize_database,
    open_database,
)
from glassbox.tools import (
    ApprovalMode,
    ToolPolicyContext,
    ToolPolicyEngine,
    ToolRuntime,
    build_read_only_tool_registry,
)


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def test_turn_engine_executes_read_only_tool_and_completes_response(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("Glassbox tool loop\n", encoding="utf-8")

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
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
                        function=_tool_then_text_response,
                        model_name="openai:gpt-5.4",
                    )
                ),
                lambda session: ToolRuntime(
                    build_read_only_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            async with bus.subscribe() as subscription:
                started_state = await supervisor.start_session(config)
                await subscription.get()
                await supervisor.submit_user_message(
                    started_state.session_id,
                    "Inspect the repo",
                )

                events = []
                while not events or events[-1].event_type != "TurnCompleted":
                    events.append(await subscription.get())

            persisted_events = repository.read_session_events(started_state.session_id)
            transcript = repository.list_transcript_messages(started_state.session_id)
        finally:
            connection.close()

        assert [event.event_type for event in events] == [
            "UserMessageReceived",
            "TurnStarted",
            "TurnStatusChanged",
            "TurnStatusChanged",
            "ModelCallStarted",
            "AssistantMessageStarted",
            "ModelCallCompleted",
            "ModelToolCallRequested",
            "TurnStatusChanged",
            "ToolExecutionStarted",
            "ToolExecutionCompleted",
            "TurnStatusChanged",
            "ModelCallStarted",
            "ModelCallCompleted",
            "TurnStatusChanged",
            "AssistantMessageCompleted",
            "TurnStatusChanged",
            "TurnCompleted",
        ]
        assert any(
            event.event_type == "ToolExecutionCompleted" for event in persisted_events
        )
        assert transcript[-1].role == "assistant"
        assert transcript[-1].parts[0].text == "README says: Glassbox tool loop"

    asyncio.run(scenario())


def test_turn_engine_logs_tool_execution_with_correlation(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (tmp_path / "README.md").write_text("Glassbox tool loop\n", encoding="utf-8")

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
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
                        function=_tool_then_text_response,
                        model_name="openai:gpt-5.4",
                    )
                ),
                lambda session: ToolRuntime(
                    build_read_only_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            with caplog.at_level(logging.INFO, logger="glassbox.runtime"):
                started_state = await supervisor.start_session(config)
                await supervisor.submit_user_message(
                    started_state.session_id,
                    "Inspect the repo",
                )
        finally:
            connection.close()

    asyncio.run(scenario())

    tool_completed = next(
        record
        for record in caplog.records
        if record.__dict__.get("runtime_event") == "tool_execution_completed"
    )

    assert tool_completed.__dict__["session_id"]
    assert tool_completed.__dict__["turn_id"]
    assert tool_completed.__dict__["tool_call_id"]
    assert tool_completed.__dict__["tool_name"] == "read_file"
    assert tool_completed.__dict__["success"] is True


def test_turn_engine_fails_when_tool_request_is_blocked(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
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
                        function=_blocked_tool_response,
                        model_name="openai:gpt-5.4",
                    )
                ),
                lambda session: ToolRuntime(
                    build_read_only_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            async with bus.subscribe() as subscription:
                started_state = await supervisor.start_session(config)
                await subscription.get()
                with pytest.raises(ValueError, match="outside workspace"):
                    await supervisor.submit_user_message(
                        started_state.session_id,
                        "Inspect the repo",
                    )

                events = []
                while not events or events[-1].event_type != "TurnFailed":
                    events.append(await subscription.get())
        finally:
            connection.close()

        assert [event.event_type for event in events] == [
            "UserMessageReceived",
            "TurnStarted",
            "TurnStatusChanged",
            "TurnStatusChanged",
            "ModelCallStarted",
            "AssistantMessageStarted",
            "ModelCallCompleted",
            "ModelToolCallRequested",
            "ToolExecutionCompleted",
            "TurnStatusChanged",
            "TurnFailed",
        ]

    asyncio.run(scenario())


def test_turn_engine_records_replay_tool_request_and_result_artifacts(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("Glassbox tool loop\n", encoding="utf-8")

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
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
                        function=_tool_then_text_response,
                        model_name="openai:gpt-5.4",
                    )
                ),
                lambda session: ToolRuntime(
                    build_read_only_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.CONFIRM,
                    ),
                ),
                artifact_repository=artifact_repository,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            state = await supervisor.start_session(config)
            await supervisor.submit_user_message(state.session_id, "Inspect the repo")

            replay_artifacts = [
                json.loads(
                    artifact_repository.read_text_artifact(Path(event.payload.path))
                )
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, ReplayArtifactRecorded)
                and event.payload.path is not None
            ]
        finally:
            connection.close()

        model_call_manifests = [
            artifact
            for artifact in replay_artifacts
            if artifact["artifact_kind"] == "replay_model_call"
        ]
        tool_request_manifests = [
            artifact
            for artifact in replay_artifacts
            if artifact["artifact_kind"] == "replay_tool_request"
        ]
        tool_result_manifests = [
            artifact
            for artifact in replay_artifacts
            if artifact["artifact_kind"] == "replay_tool_result"
        ]
        turn_output_manifests = [
            artifact
            for artifact in replay_artifacts
            if artifact["artifact_kind"] == "replay_turn_output"
        ]

        assert len(model_call_manifests) == 2
        assert len(tool_request_manifests) == 1
        assert len(tool_result_manifests) == 1
        assert len(turn_output_manifests) == 1
        assert tool_request_manifests[0]["tool_name"] == "read_file"
        assert tool_request_manifests[0]["policy_decision"]["allowed"] is True
        assert tool_result_manifests[0]["success"] is True
        assert (
            tool_result_manifests[0]["output_payload"]["content"]
            == "Glassbox tool loop"
        )
        assert (
            turn_output_manifests[0]["assistant_text"]
            == "README says: Glassbox tool loop"
        )

    asyncio.run(scenario())


def _tool_then_text_response(messages, _agent_info) -> ModelResponse:
    saw_tool_return = False
    tool_content = None
    user_prompt = None

    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    user_prompt = part.content
                if isinstance(part, ToolReturnPart):
                    saw_tool_return = True
                    tool_content = part.content
        elif isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    assert part.tool_name == "read_file"

    assert user_prompt == "Inspect the repo"
    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="read_file",
                    args={"path": "README.md", "start_line": 1, "end_line": 1},
                    tool_call_id="provider-call-1",
                )
            ]
        )

    assert isinstance(tool_content, dict)
    assert tool_content["content"] == "Glassbox tool loop"
    return ModelResponse(parts=[TextPart(content="README says: Glassbox tool loop")])


def _blocked_tool_response(messages, _agent_info) -> ModelResponse:
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, SystemPromptPart):
                assert "You are Glassbox" in part.content

    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="read_file",
                args={"path": "../secret.txt"},
                tool_call_id="provider-call-2",
            )
        ]
    )
