"""Integration tests for the ask_user tool: suspension and resume cycle."""

import asyncio
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from glassbox.core import EventEnvelope, SessionConfig
from glassbox.core.events import TurnCompleted, UserQuestionAsked
from glassbox.core.types import SessionStatus
from glassbox.llm import (
    ModelProviderConfig,
    PydanticAIModelAdapter,
    PydanticAIModelExecutor,
)
from glassbox.runtime import EventBus, SessionSupervisor, TurnContextBuilder, TurnEngine
from glassbox.store import SQLiteSessionRepository, initialize_database, open_database
from glassbox.tools import (
    ApprovalMode,
    AskUserArgs,
    AskUserTool,
    ToolPolicyContext,
    ToolPolicyEngine,
    ToolRuntime,
    build_ask_user_tool_registry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _make_turn_engine(
    tmp_path: Path,
    repository: SQLiteSessionRepository,
    bus: EventBus[EventEnvelope],
    model_fn: Any,
) -> TurnEngine:
    return TurnEngine(
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
            build_ask_user_tool_registry(session.cwd),
            ToolPolicyEngine(),
            ToolPolicyContext(
                workspace_root=session.cwd,
                approval_mode=ApprovalMode.NEVER,
            ),
        ),
    )


# ---------------------------------------------------------------------------
# FunctionModel responses
# ---------------------------------------------------------------------------


def _ask_user_then_text_response(messages: list, _agent_info: Any) -> ModelResponse:
    """First turn: emit ask_user call; second turn: emit final text using the answer."""
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


def _plain_text_response(messages: list, _agent_info: Any) -> ModelResponse:
    """Always returns a simple text response without any tool calls."""
    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    return ModelResponse(parts=[TextPart(content="Done.")])
    return ModelResponse(parts=[TextPart(content="Done.")])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ask_user_tool_suspends_turn(tmp_path: Path) -> None:
    """Model calls ask_user → turn suspends with outcome 'awaiting_user_input'."""

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _make_turn_engine(
                tmp_path, repository, bus, _ask_user_then_text_response
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="never",
            )

            async with bus.subscribe() as subscription:
                state = await supervisor.start_session(config)
                await subscription.get()  # SessionStarted
                await supervisor.submit_user_message(state.session_id, "Pick a colour.")

                events = []
                while not events or events[-1].event_type != "TurnCompleted":
                    events.append(await subscription.get())

            persisted = repository.read_session_events(state.session_id)
            session_state = repository.get_session_state(state.session_id)
        finally:
            connection.close()

        # Turn outcome must be 'awaiting_user_input'
        turn_completed_payloads = [
            ev.payload for ev in persisted if isinstance(ev.payload, TurnCompleted)
        ]
        assert len(turn_completed_payloads) == 1
        assert turn_completed_payloads[0].outcome == "awaiting_user_input"

        # A UserQuestionAsked event must have been persisted
        question_payloads = [
            ev.payload for ev in persisted if isinstance(ev.payload, UserQuestionAsked)
        ]
        assert len(question_payloads) == 1
        assert question_payloads[0].question == "What colour should I use?"

        # Session must be in AWAITING_USER_INPUT status
        assert session_state is not None
        assert session_state.status == SessionStatus.AWAITING_USER_INPUT
        assert session_state.pending_question_id == question_payloads[0].question_id

    asyncio.run(scenario())


def test_provide_user_answer_resumes_turn(tmp_path: Path) -> None:
    """Full pause/resume cycle: ask_user → provide answer → model finishes."""

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _make_turn_engine(
                tmp_path, repository, bus, _ask_user_then_text_response
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="never",
            )

            async with bus.subscribe() as subscription:
                state = await supervisor.start_session(config)
                await subscription.get()  # SessionStarted

                await supervisor.submit_user_message(state.session_id, "Pick a colour.")

                # Wait for turn to suspend
                events: list[EventEnvelope] = []
                while not events or events[-1].event_type != "TurnCompleted":
                    events.append(await subscription.get())

                # Locate the question_id from the UserQuestionAsked event
                persisted = repository.read_session_events(state.session_id)
                question_payload = next(
                    ev.payload
                    for ev in persisted
                    if isinstance(ev.payload, UserQuestionAsked)
                )

                # Provide the answer — this resumes and finishes the turn
                await supervisor.provide_user_answer(
                    state.session_id,
                    question_payload.question_id,
                    "blue",
                )

                # Wait for the resumed turn to complete
                resume_events: list[EventEnvelope] = []
                while (
                    not resume_events or resume_events[-1].event_type != "TurnCompleted"
                ):
                    resume_events.append(await subscription.get())

            final_state = repository.get_session_state(state.session_id)
            transcript = repository.list_transcript_messages(state.session_id)
            all_persisted = repository.read_session_events(state.session_id)
        finally:
            connection.close()

        # Session must be back in RUNNING (idle) state
        assert final_state is not None
        assert final_state.status == SessionStatus.RUNNING
        assert final_state.pending_question_id is None

        # The final turn must have completed normally — check final session state
        final_turn_outcomes = [
            ev.payload.outcome
            for ev in all_persisted
            if isinstance(ev.payload, TurnCompleted)
        ]
        assert "completed" in final_turn_outcomes

        # Assistant message must mention the answer
        assert transcript[-1].role == "assistant"
        assert "blue" in transcript[-1].parts[0].text

    asyncio.run(scenario())


def test_session_status_awaiting_user_input_blocks_new_messages(tmp_path: Path) -> None:
    """Cannot submit_user_message while a session is AWAITING_USER_INPUT."""

    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = EventBus()
            turn_engine = _make_turn_engine(
                tmp_path, repository, bus, _ask_user_then_text_response
            )
            supervisor = SessionSupervisor(repository, bus, turn_engine=turn_engine)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="never",
            )

            async with bus.subscribe() as subscription:
                state = await supervisor.start_session(config)
                await subscription.get()  # SessionStarted

                await supervisor.submit_user_message(state.session_id, "Pick a colour.")

                # Drain until suspended
                events: list[EventEnvelope] = []
                while not events or events[-1].event_type != "TurnCompleted":
                    events.append(await subscription.get())

            with pytest.raises(ValueError, match="cannot accept input"):
                await supervisor.submit_user_message(
                    state.session_id, "another message"
                )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_build_ask_user_registry_includes_all_tools(tmp_path: Path) -> None:
    """build_ask_user_tool_registry must expose 8 tools total."""

    registry = build_ask_user_tool_registry(tmp_path)
    tool_names = {tool.spec.name for tool in registry.list_tools()}

    expected = {
        "list_dir",
        "read_file",
        "search_files",
        "run_command",
        "git_status",
        "run_tests",
        "apply_patch",
        "ask_user",
    }
    assert tool_names == expected


def test_ask_user_is_read_only_policy(tmp_path: Path) -> None:
    """ask_user must have READ_ONLY risk level so it never requires approval."""

    from glassbox.tools import ToolRiskLevel

    tool = AskUserTool(tmp_path)
    assert tool.spec.risk_level == ToolRiskLevel.READ_ONLY


def test_ask_user_execute_raises_not_implemented(tmp_path: Path) -> None:
    """execute() must raise NotImplementedError as a safeguard."""

    async def scenario() -> None:
        tool = AskUserTool(tmp_path)
        with pytest.raises(NotImplementedError):
            await tool.execute(AskUserArgs(question="hello?"))

    asyncio.run(scenario())
