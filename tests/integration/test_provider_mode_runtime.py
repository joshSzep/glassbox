"""Integration tests for provider-mode runtime execution without network access."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextContent,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from glassbox.core import SessionConfig
from glassbox.core.events import (
    AssistantMessageCompleted,
    AssistantMessageDelta,
    ModelCallStarted,
)
from glassbox.llm import PydanticAIModelExecutor
from glassbox.runtime import bootstrap as runtime_bootstrap
from glassbox.store import initialize_database, open_database


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def test_provider_mode_streaming_turn_executes_without_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        (tmp_path / ".env").write_text("OPENAI_API_KEY=dotenv-openai\n")

        def fake_build_openai_model_executor(
            model_name: str,
            *,
            api_key: str | None = None,
            base_url: str | None = None,
        ) -> PydanticAIModelExecutor:
            assert model_name == "gpt-5.4"
            assert api_key == "dotenv-openai"
            assert base_url is None
            return PydanticAIModelExecutor(
                FunctionModel(
                    function=_provider_function_model_response,
                    stream_function=_provider_stream_function_model_response,
                    model_name=f"openai:{model_name}",
                )
            )

        monkeypatch.setattr(
            runtime_bootstrap,
            "build_openai_model_executor",
            fake_build_openai_model_executor,
        )

        try:
            runtime_context = runtime_bootstrap._build_runtime_context(
                connection,
                tmp_path,
            )
            service = runtime_context.services.session_service
            repository = runtime_context.repositories.sessions
            state = await service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await service.submit_user_message(state.session_id, "Inspect the repo")

            events = repository.read_session_events(state.session_id)
            transcript = repository.list_transcript_messages(state.session_id)
        finally:
            connection.close()

        model_started = [
            event.payload
            for event in events
            if isinstance(event.payload, ModelCallStarted)
        ]
        deltas = [
            event.payload
            for event in events
            if isinstance(event.payload, AssistantMessageDelta)
        ]
        completed = [
            event.payload
            for event in events
            if isinstance(event.payload, AssistantMessageCompleted)
        ]

        assert model_started[-1].provider == "openai"
        assert model_started[-1].model_name == "gpt-5.4"
        assert [delta.delta for delta in deltas] == ["Provider stream ", "complete."]
        assert completed[-1].parts[0].text == "Provider stream complete."
        assert transcript[-1].parts[0].text == "Provider stream complete."

    asyncio.run(scenario())


def test_provider_mode_non_streaming_turn_falls_back_without_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        (tmp_path / ".env").write_text("OPENAI_API_KEY=dotenv-openai\n")

        def fake_build_openai_model_executor(
            model_name: str,
            *,
            api_key: str | None = None,
            base_url: str | None = None,
        ) -> PydanticAIModelExecutor:
            assert model_name == "gpt-5.4"
            assert api_key == "dotenv-openai"
            assert base_url is None
            return PydanticAIModelExecutor(
                FunctionModel(
                    function=_provider_non_streaming_model_response,
                    model_name=f"openai:{model_name}",
                )
            )

        monkeypatch.setattr(
            runtime_bootstrap,
            "build_openai_model_executor",
            fake_build_openai_model_executor,
        )

        try:
            runtime_context = runtime_bootstrap._build_runtime_context(
                connection,
                tmp_path,
            )
            service = runtime_context.services.session_service
            repository = runtime_context.repositories.sessions
            state = await service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await service.submit_user_message(state.session_id, "Inspect the repo")

            events = repository.read_session_events(state.session_id)
            transcript = repository.list_transcript_messages(state.session_id)
        finally:
            connection.close()

        model_started = [
            event.payload
            for event in events
            if isinstance(event.payload, ModelCallStarted)
        ]
        deltas = [
            event.payload
            for event in events
            if isinstance(event.payload, AssistantMessageDelta)
        ]
        completed = [
            event.payload
            for event in events
            if isinstance(event.payload, AssistantMessageCompleted)
        ]

        assert model_started[-1].provider == "openai"
        assert model_started[-1].model_name == "gpt-5.4"
        assert deltas == []
        assert completed[-1].parts[0].text == "Provider fallback complete."
        assert transcript[-1].parts[0].text == "Provider fallback complete."

    asyncio.run(scenario())


def _provider_function_model_response(messages, _agent_info) -> ModelResponse:
    user_prompt_text = _latest_user_prompt(messages)
    assert user_prompt_text == "Inspect the repo"
    return ModelResponse(parts=[TextPart(content="Provider stream complete.")])


async def _provider_stream_function_model_response(messages, _agent_info):
    _ = _provider_function_model_response(messages, _agent_info)
    yield "Provider stream "
    yield "complete."


def _provider_non_streaming_model_response(messages, _agent_info) -> ModelResponse:
    user_prompt_text = _latest_user_prompt(messages)
    assert user_prompt_text == "Inspect the repo"
    return ModelResponse(parts=[TextPart(content="Provider fallback complete.")])


def _latest_user_prompt(messages) -> str | None:
    for message in reversed(messages):
        if not isinstance(message, ModelRequest):
            continue
        for part in reversed(message.parts):
            if isinstance(part, UserPromptPart):
                if isinstance(part.content, str):
                    return part.content
                return "".join(
                    content.content
                    for content in part.content
                    if isinstance(content, TextContent)
                )
    return None
