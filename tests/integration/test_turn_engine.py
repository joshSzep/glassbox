"""Integration tests for the non-tool turn engine flow."""

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
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from glassbox.core import EventEnvelope, SessionConfig, SessionStatus
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


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def test_supervisor_drives_turn_engine_and_persists_assistant_response(
    tmp_path: Path,
) -> None:
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
                        function=_function_model_response,
                        stream_function=_stream_function_model_response,
                        model_name="openai:gpt-5.4",
                    )
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
            session_state = repository.get_session_state(started_state.session_id)
        finally:
            connection.close()

        assert [event.event_type for event in events] == [
            "UserMessageReceived",
            "TurnStarted",
            "TurnStatusChanged",
            "TurnStatusChanged",
            "ModelCallStarted",
            "AssistantMessageStarted",
            "AssistantMessageDelta",
            "AssistantMessageDelta",
            "ModelCallCompleted",
            "TurnStatusChanged",
            "AssistantMessageCompleted",
            "TurnStatusChanged",
            "TurnCompleted",
        ]
        assert [event.event_type for event in persisted_events] == [
            "SessionStarted",
            "UserMessageReceived",
            "TurnStarted",
            "TurnStatusChanged",
            "TurnStatusChanged",
            "ModelCallStarted",
            "AssistantMessageStarted",
            "AssistantMessageDelta",
            "AssistantMessageDelta",
            "ModelCallCompleted",
            "TurnStatusChanged",
            "AssistantMessageCompleted",
            "TurnStatusChanged",
            "TurnCompleted",
        ]
        assert transcript[0].role == "user"
        assert transcript[0].parts[0].text == "Inspect the repo"
        assert transcript[1].role == "assistant"
        assert transcript[1].parts[0].text == "Repo inspection complete."
        assert session_state is not None
        assert session_state.status == SessionStatus.RUNNING
        assert session_state.current_turn_id is None
        assert session_state.last_sequence == 14

    asyncio.run(scenario())


def test_turn_engine_emits_correlated_runtime_logs(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
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
                        function=_function_model_response,
                        stream_function=_stream_function_model_response,
                        model_name="openai:gpt-5.4",
                    )
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

    turn_started = next(
        record
        for record in caplog.records
        if record.__dict__.get("runtime_event") == "turn_started"
    )
    model_completed = next(
        record
        for record in caplog.records
        if record.__dict__.get("runtime_event") == "model_call_completed"
    )
    turn_completed = next(
        record
        for record in caplog.records
        if record.__dict__.get("runtime_event") == "turn_completed"
    )

    assert turn_started.__dict__["session_id"] == model_completed.__dict__["session_id"]
    assert turn_started.__dict__["turn_id"] == model_completed.__dict__["turn_id"]
    assert model_completed.__dict__["turn_id"] == turn_completed.__dict__["turn_id"]
    assert model_completed.__dict__["provider"] == "openai"
    assert model_completed.__dict__["model_name"] == "gpt-5.4"
    assert model_completed.__dict__["duration_ms"] >= 0
    assert turn_completed.__dict__["outcome"] == "completed"


def test_turn_engine_records_replay_manifests_for_text_only_turn(
    tmp_path: Path,
) -> None:
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
                    ModelProviderConfig(
                        provider="openai",
                        model_name="gpt-5.4",
                        model_settings={
                            "temperature": 0.2,
                            "api_key": "super-secret",
                        },
                    )
                ),
                lambda _session: PydanticAIModelExecutor(
                    FunctionModel(
                        function=_function_model_response,
                        stream_function=_stream_function_model_response,
                        model_name="openai:gpt-5.4",
                    )
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

            replay_events = [
                event.payload
                for event in repository.read_session_events(state.session_id)
                if isinstance(event.payload, ReplayArtifactRecorded)
            ]
            replay_artifacts = {
                payload.artifact_kind: json.loads(
                    artifact_repository.read_text_artifact(Path(payload.path))
                )
                for payload in replay_events
                if payload.path is not None
            }
        finally:
            connection.close()

        assert [payload.artifact_kind for payload in replay_events] == [
            "replay_model_call",
            "replay_turn_output",
        ]
        model_call_manifest = replay_artifacts["replay_model_call"]
        turn_output_manifest = replay_artifacts["replay_turn_output"]
        assert (
            model_call_manifest["runtime_config"]["model_settings"]["api_key"]
            == "[REDACTED]"
        )
        assert (
            model_call_manifest["runtime_config"]["model_settings"]["temperature"]
            == 0.2
        )
        assert model_call_manifest["prepared_turn"]["user_prompt"] is None
        assert (
            model_call_manifest["prepared_turn"]["message_history"][-1]["parts"][0][
                "content"
            ]
            == "Inspect the repo"
        )
        assert turn_output_manifest["outcome"] == "completed"
        assert turn_output_manifest["assistant_text"] == "Repo inspection complete."

    asyncio.run(scenario())


def _function_model_response(messages, _agent_info) -> ModelResponse:
    system_prompt_text = None
    user_prompt_text = None

    for message in messages:
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, SystemPromptPart):
                system_prompt_text = part.content
            if isinstance(part, UserPromptPart):
                user_prompt_text = part.content

    assert system_prompt_text is not None
    assert "You are Glassbox" in system_prompt_text
    assert "Approval policy:" in system_prompt_text
    assert user_prompt_text == "Inspect the repo"

    return ModelResponse(parts=[TextPart(content="Repo inspection complete.")])


async def _stream_function_model_response(messages, _agent_info):
    _ = _function_model_response(messages, _agent_info)
    yield "Repo inspection "
    yield "complete."
