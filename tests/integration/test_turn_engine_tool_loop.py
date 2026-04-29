"""Integration tests for the turn engine tool execution loop."""

import asyncio
import json
import logging
import sqlite3
import subprocess
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import SystemPromptPart
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.messages import UserPromptPart
from pydantic_ai.models.function import DeltaToolCall
from pydantic_ai.models.function import FunctionModel

from glassbox.core import ApprovalDecision
from glassbox.core import EventEnvelope
from glassbox.core import SessionConfig
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolExecutionCompleted
from glassbox.llm import ModelProviderConfig
from glassbox.llm import PydanticAIModelAdapter
from glassbox.llm import PydanticAIModelExecutor
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context_builder import PYTEST_FAILURE_DIGEST_ARTIFACT_KIND
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.runtime.turn_engine import TurnEngine
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.tools import DIFF_SUMMARY_ARTIFACT_KIND
from glassbox.tools import ApprovalMode
from glassbox.tools import ToolPolicyContext
from glassbox.tools import ToolPolicyEngine
from glassbox.tools import ToolRuntime
from glassbox.tools import build_command_tool_registry
from glassbox.tools import build_read_only_tool_registry
from glassbox.tools import build_workflow_tool_registry


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


def test_turn_engine_classifies_blocked_command_tool_request(tmp_path: Path) -> None:
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
                        function=_blocked_command_response,
                        model_name="openai:gpt-5.4",
                    )
                ),
                lambda session: ToolRuntime(
                    build_command_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.NEVER,
                    ),
                ),
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="never",
            )

            async with bus.subscribe() as subscription:
                started_state = await supervisor.start_session(config)
                await subscription.get()
                with pytest.raises(ValueError, match="blocked:|denied"):
                    await supervisor.submit_user_message(
                        started_state.session_id,
                        "Run the dangerous command",
                    )

                events: list[EventEnvelope] = []
                while not events or events[-1].event_type != "TurnFailed":
                    events.append(await subscription.get())
        finally:
            connection.close()

        tool_completed = next(
            event.payload
            for event in events
            if event.event_type == "ToolExecutionCompleted"
        )
        assert isinstance(tool_completed, ToolExecutionCompleted)
        assert tool_completed.success is False
        assert "blocked" in tool_completed.summary

    asyncio.run(scenario())


def test_turn_engine_records_failed_command_result_for_replay(tmp_path: Path) -> None:
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
                        function=_failing_command_then_text_response,
                        model_name="openai:gpt-5.4",
                    )
                ),
                lambda session: ToolRuntime(
                    build_command_tool_registry(session.cwd),
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

            async with bus.subscribe() as subscription:
                state = await supervisor.start_session(config)
                await subscription.get()

                await supervisor.submit_user_message(
                    state.session_id,
                    "Run the failing command",
                )
                first_turn_events: list[EventEnvelope] = []
                while (
                    not first_turn_events
                    or first_turn_events[-1].event_type != "TurnCompleted"
                ):
                    first_turn_events.append(await subscription.get())

                approval_payloads = [
                    event.payload
                    for event in repository.read_session_events(state.session_id)
                    if isinstance(event.payload, ApprovalRequested)
                ]
                assert len(approval_payloads) == 1

                await supervisor.resolve_approval(
                    state.session_id,
                    approval_payloads[0].approval_id,
                    ApprovalDecision.APPROVED,
                )

                resumed_events: list[EventEnvelope] = []
                while (
                    not resumed_events
                    or resumed_events[-1].event_type != "TurnCompleted"
                ):
                    resumed_events.append(await subscription.get())

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

        tool_completed = next(
            event.payload
            for event in resumed_events
            if event.event_type == "ToolExecutionCompleted"
        )
        assert isinstance(tool_completed, ToolExecutionCompleted)
        assert tool_completed.success is False
        assert tool_completed.exit_code == 7
        assert tool_completed.summary == "failed in ."

        tool_result_manifests = [
            artifact
            for artifact in replay_artifacts
            if artifact["artifact_kind"] == "replay_tool_result"
        ]
        assert len(tool_result_manifests) == 1
        assert tool_result_manifests[0]["success"] is False
        assert tool_result_manifests[0]["summary"] == "failed in ."
        assert tool_result_manifests[0]["error_message"] == "failed in . (exit code 7)"
        assert (
            tool_result_manifests[0]["output_payload"]["failure_category"]
            == "execution_error"
        )
        assert tool_result_manifests[0]["output_payload"]["exit_code"] == 7

    asyncio.run(scenario())


def test_turn_engine_records_pytest_failure_digest_for_later_turns(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_fail.py").write_text(
        "def test_failure():\n    assert False\n",
        encoding="utf-8",
    )

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
                        function=_run_tests_then_use_digest_response,
                        stream_function=_stream_run_tests_then_use_digest_response,
                        model_name="openai:gpt-5.4",
                    )
                ),
                lambda session: ToolRuntime(
                    build_workflow_tool_registry(session.cwd),
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

            async with bus.subscribe() as subscription:
                state = await supervisor.start_session(config)
                await subscription.get()

                await supervisor.submit_user_message(
                    state.session_id,
                    "Run the targeted tests",
                )
                first_turn_events: list[EventEnvelope] = []
                while (
                    not first_turn_events
                    or first_turn_events[-1].event_type != "TurnCompleted"
                ):
                    first_turn_events.append(await subscription.get())

                approval_payloads = [
                    event.payload
                    for event in repository.read_session_events(state.session_id)
                    if isinstance(event.payload, ApprovalRequested)
                ]
                assert len(approval_payloads) == 1

                await supervisor.resolve_approval(
                    state.session_id,
                    approval_payloads[0].approval_id,
                    ApprovalDecision.APPROVED,
                )

                resumed_events: list[EventEnvelope] = []
                while (
                    not resumed_events
                    or resumed_events[-1].event_type != "TurnCompleted"
                ):
                    resumed_events.append(await subscription.get())

                await supervisor.submit_user_message(
                    state.session_id,
                    "Summarize the latest failure",
                )
                second_turn_events: list[EventEnvelope] = []
                while (
                    not second_turn_events
                    or second_turn_events[-1].event_type != "TurnCompleted"
                ):
                    second_turn_events.append(await subscription.get())

            artifact_events = [
                event.payload
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, ToolArtifactRecorded)
                and event.payload.artifact_kind == PYTEST_FAILURE_DIGEST_ARTIFACT_KIND
            ]
            transcript = repository.list_transcript_messages(state.session_id)
            assert artifact_events[0].path is not None
            artifact_payload = json.loads(
                artifact_repository.read_text_artifact(Path(artifact_events[0].path))
            )
        finally:
            connection.close()

        assert len(artifact_events) == 1
        assert artifact_payload["failure_count"] == 1
        assert artifact_payload["failing_tests"] == ["test_fail.py::test_failure"]
        assert transcript[-1].parts[0].text == "Latest failure summarized."

    asyncio.run(scenario())


def test_turn_engine_records_large_diff_summary_artifact(
    tmp_path: Path,
) -> None:
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "README.md").write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    changes_dir = tmp_path / "changes"
    changes_dir.mkdir()
    for index in range(4):
        (changes_dir / f"file_{index}.py").write_text(
            f"value = {index}\n", encoding="utf-8"
        )

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
                        function=_diff_summary_then_text_response,
                        stream_function=_stream_diff_summary_then_text_response,
                        model_name="openai:gpt-5.4",
                    )
                ),
                lambda session: ToolRuntime(
                    build_workflow_tool_registry(session.cwd),
                    ToolPolicyEngine(),
                    ToolPolicyContext(
                        workspace_root=session.cwd,
                        approval_mode=ApprovalMode.NEVER,
                    ),
                ),
                artifact_repository=artifact_repository,
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="never",
            )

            async with bus.subscribe() as subscription:
                state = await supervisor.start_session(config)
                await subscription.get()

                await supervisor.submit_user_message(
                    state.session_id,
                    "Summarize the patch risk",
                )
                events: list[EventEnvelope] = []
                while not events or events[-1].event_type != "TurnCompleted":
                    events.append(await subscription.get())

            artifact_events = [
                event.payload
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, ToolArtifactRecorded)
                and event.payload.artifact_kind == DIFF_SUMMARY_ARTIFACT_KIND
            ]
            assert artifact_events[0].path is not None
            artifact_payload = json.loads(
                artifact_repository.read_text_artifact(Path(artifact_events[0].path))
            )
        finally:
            connection.close()

        assert len(artifact_events) == 1
        assert artifact_payload["artifact_kind"] == DIFF_SUMMARY_ARTIFACT_KIND
        assert artifact_payload["risk_summary"]["touched_files"] == 4
        assert len(artifact_payload["files"]) == 4

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


def _blocked_command_response(messages, _agent_info) -> ModelResponse:
    del messages, _agent_info
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="run_command",
                args={"command": "rm -rf /"},
                tool_call_id="provider-call-command-blocked-1",
            )
        ]
    )


def _failing_command_then_text_response(messages, _agent_info) -> ModelResponse:
    saw_tool_return = False
    tool_content = None
    user_prompt = None

    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    user_prompt = part.content
                if isinstance(part, ToolReturnPart) and part.tool_name == "run_command":
                    saw_tool_return = True
                    tool_content = part.content

    assert user_prompt == "Run the failing command"
    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="run_command",
                    args={"command": "exit 7"},
                    tool_call_id="provider-call-command-fail-1",
                )
            ]
        )

    assert isinstance(tool_content, dict)
    assert tool_content["failure_category"] == "execution_error"
    assert tool_content["exit_code"] == 7
    return ModelResponse(parts=[TextPart(content="Observed failing command.")])


def _run_tests_then_use_digest_response(messages, _agent_info) -> ModelResponse:
    saw_tool_return = False
    user_prompt = None
    system_prompt_text = None
    tool_content = None

    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, SystemPromptPart):
                    system_prompt_text = part.content
                if isinstance(part, UserPromptPart):
                    user_prompt = part.content
                if isinstance(part, ToolReturnPart) and part.tool_name == "run_tests":
                    saw_tool_return = True
                    tool_content = part.content

    assert user_prompt is not None
    if user_prompt == "Run the targeted tests":
        if not saw_tool_return:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="run_tests",
                        args={"paths": ["test_fail.py"]},
                        tool_call_id="provider-call-run-tests-1",
                    )
                ]
            )

        assert isinstance(tool_content, dict)
        assert tool_content["failed"] == 1
        return ModelResponse(parts=[TextPart(content="Captured failing test.")])

    assert user_prompt == "Summarize the latest failure"
    assert system_prompt_text is not None
    assert "Artifact-backed context:" in system_prompt_text
    assert "[pytest_failure_digest]" in system_prompt_text
    assert "test_fail.py::test_failure" in system_prompt_text
    return ModelResponse(parts=[TextPart(content="Latest failure summarized.")])


def _diff_summary_then_text_response(messages, _agent_info) -> ModelResponse:
    saw_tool_return = False
    tool_content = None

    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if (
                    isinstance(part, ToolReturnPart)
                    and part.tool_name == "workspace_diff_summary"
                ):
                    saw_tool_return = True
                    tool_content = part.content

    if not saw_tool_return:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="workspace_diff_summary",
                    args={"paths": ["changes"], "inline_file_limit": 2},
                    tool_call_id="provider-call-diff-summary-1",
                )
            ]
        )

    assert isinstance(tool_content, dict)
    assert tool_content["artifact_required"] is True
    assert tool_content["risk_summary"]["touched_files"] == 4
    return ModelResponse(parts=[TextPart(content="Patch risk summarized.")])


async def _stream_diff_summary_then_text_response(messages, agent_info):
    response = _diff_summary_then_text_response(messages, agent_info)
    first_part = response.parts[0]
    if isinstance(first_part, TextPart):
        yield first_part.content
        return

    assert isinstance(first_part, ToolCallPart)
    yield {
        0: DeltaToolCall(
            name=first_part.tool_name,
            json_args=json.dumps(first_part.args),
            tool_call_id=first_part.tool_call_id,
        )
    }


async def _stream_run_tests_then_use_digest_response(messages, agent_info):
    response = _run_tests_then_use_digest_response(messages, agent_info)
    first_part = response.parts[0]
    if isinstance(first_part, TextPart):
        yield first_part.content
        return

    assert isinstance(first_part, ToolCallPart)
    yield {
        0: DeltaToolCall(
            name=first_part.tool_name,
            json_args=json.dumps(first_part.args),
            tool_call_id=first_part.tool_call_id,
        )
    }
