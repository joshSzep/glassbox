"""Unit tests for the pydantic-ai adapter layer."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic_ai.messages import FinalResultEvent
from pydantic_ai.messages import PartDeltaEvent
from pydantic_ai.messages import PartEndEvent
from pydantic_ai.messages import PartStartEvent
from pydantic_ai.messages import SystemPromptPart
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.messages import ToolCallPartDelta
from pydantic_ai.messages import UserPromptPart

from glassbox.core.models import MessagePart
from glassbox.core.models import MessageRole
from glassbox.core.models import TranscriptMessage
from glassbox.core.types import SessionStatus
from glassbox.llm import ModelFinalResult
from glassbox.llm import ModelProviderConfig
from glassbox.llm import ModelTextDelta
from glassbox.llm import ModelToolCall
from glassbox.llm import ModelToolCallDelta
from glassbox.llm import PydanticAIModelAdapter
from glassbox.runtime.context_builder import PolicyContext
from glassbox.runtime.context_builder import ToolSchema
from glassbox.runtime.context_builder import TurnContext


def test_build_turn_request_splits_pending_user_prompt_from_history() -> None:
    adapter = PydanticAIModelAdapter(
        ModelProviderConfig(
            provider="openai",
            model_name="gpt-5.4",
            model_settings={"temperature": 0.2},
        )
    )
    turn_context = TurnContext(
        session_id=uuid4(),
        session_status=SessionStatus.RUNNING,
        current_turn_id=uuid4(),
        last_sequence=8,
        transcript=[
            _message("system", "Follow policy."),
            _message("user", "Summarize the repo."),
            _message("assistant", "The repo is event-sourced."),
            _message("user", "Now show the latest changes."),
        ],
        available_tools=[
            ToolSchema(
                name="shell",
                description="Run a shell command.",
                parameters_json_schema={
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                },
            ),
            ToolSchema(
                name="read_file",
                description="Read a file from disk.",
                parameters_json_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            ),
        ],
        policy=PolicyContext(approval_mode="on-request"),
    )

    prepared = adapter.build_turn_request(
        turn_context,
        system_prompt="You are Glassbox.",
    )

    assert prepared.model_name == "openai:gpt-5.4"
    assert prepared.user_prompt == "Now show the latest changes."
    assert prepared.model_settings == {"temperature": 0.2}
    assert len(prepared.message_history) == 4

    system_message = prepared.message_history[0]
    assert isinstance(system_message.parts[0], SystemPromptPart)
    assert system_message.parts[0].content == "You are Glassbox."

    prior_user_message = prepared.message_history[2]
    assert isinstance(prior_user_message.parts[0], UserPromptPart)
    assert prior_user_message.parts[0].content == "Summarize the repo."

    assistant_message = prepared.message_history[3]
    assert isinstance(assistant_message.parts[0], TextPart)
    assert assistant_message.parts[0].content == "The repo is event-sourced."

    tool_names = [tool.name for tool in prepared.request_parameters.function_tools]
    assert tool_names == ["shell", "read_file"]


def test_stream_translator_emits_text_deltas_and_final_result() -> None:
    translator = PydanticAIModelAdapter(
        ModelProviderConfig(model_name="openai:gpt-5.4")
    ).new_stream_translator()

    text_events = translator.translate(
        PartStartEvent(
            index=0,
            part=TextPart(content="Hello"),
            previous_part_kind=None,
        )
    )
    final_events = translator.translate(
        FinalResultEvent(tool_name=None, tool_call_id=None)
    )

    assert text_events == (ModelTextDelta(text="Hello"),)
    assert final_events == (ModelFinalResult(tool_name=None, tool_call_id=None),)


def test_stream_translator_reconstructs_structured_tool_calls() -> None:
    translator = PydanticAIModelAdapter(
        ModelProviderConfig(model_name="openai:gpt-5.4")
    ).new_stream_translator()

    start_events = translator.translate(
        PartStartEvent(
            index=1,
            part=ToolCallPart(
                tool_name="shell",
                args='{"command":"ls"',
                tool_call_id="call-1",
            ),
            previous_part_kind=None,
        )
    )
    delta_events = translator.translate(
        PartDeltaEvent(
            index=1,
            delta=ToolCallPartDelta(args_delta="}"),
        )
    )
    end_events = translator.translate(
        PartEndEvent(
            index=1,
            part=ToolCallPart(
                tool_name="shell",
                args='{"command":"ls"}',
                tool_call_id="call-1",
            ),
            next_part_kind=None,
        )
    )

    assert start_events == (
        ModelToolCallDelta(
            tool_name_delta="shell",
            arguments_delta='{"command":"ls"',
            tool_call_id="call-1",
        ),
    )
    assert delta_events == (
        ModelToolCallDelta(
            arguments_delta="}",
        ),
    )
    assert end_events == (
        ModelToolCall(
            tool_name="shell",
            arguments='{"command":"ls"}',
            tool_call_id="call-1",
        ),
    )


def test_stream_translator_rejects_mixed_tool_argument_representations() -> None:
    translator = PydanticAIModelAdapter(
        ModelProviderConfig(model_name="openai:gpt-5.4")
    ).new_stream_translator()

    translator.translate(
        PartStartEvent(
            index=2,
            part=ToolCallPart(
                tool_name="shell",
                args='{"command":"ls"',
                tool_call_id="call-2",
            ),
            previous_part_kind=None,
        )
    )

    with pytest.raises(ValueError, match="representation"):
        translator.translate(
            PartDeltaEvent(
                index=2,
                delta=ToolCallPartDelta(args_delta={"command": "pwd"}),
            )
        )


def _message(role: MessageRole, text: str) -> TranscriptMessage:
    return TranscriptMessage(
        message_id=uuid4(),
        role=role,
        parts=[MessagePart(kind="text", text=text)],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
