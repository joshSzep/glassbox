"""Unit tests for the shared model-loop runner."""

import asyncio
from typing import cast

from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models import ModelRequestParameters

from glassbox.llm import ModelExecutionResult
from glassbox.llm import ModelProviderConfig
from glassbox.llm import ModelTextDelta
from glassbox.llm import ModelToolCall
from glassbox.llm import PreparedModelTurn
from glassbox.llm import PydanticAIModelAdapter
from glassbox.runtime.model_loop import ModelConversationState
from glassbox.runtime.model_loop import ModelLoopRunner


class _FakeExecutor:
    def __init__(self, results: list[ModelExecutionResult]) -> None:
        self._results = list(results)
        self.calls: list[PreparedModelTurn] = []

    async def execute(self, prepared_turn: PreparedModelTurn) -> ModelExecutionResult:
        return await self.execute_stream(
            prepared_turn,
            stream_translator=PydanticAIModelAdapter(
                ModelProviderConfig(provider="openai", model_name="gpt-5.4")
            ).new_stream_translator(),
            on_event=lambda _event: None,
        )

    async def execute_stream(
        self,
        prepared_turn: PreparedModelTurn,
        *,
        stream_translator,
        on_event,
    ) -> ModelExecutionResult:
        del stream_translator
        self.calls.append(prepared_turn)
        result = self._results.pop(0)
        for chunk in _text_chunks(result.assistant_text):
            on_event(ModelTextDelta(text=chunk))
        return result


def test_model_loop_runner_completes_text_only_response() -> None:
    async def scenario() -> None:
        runner = ModelLoopRunner()
        state = ModelConversationState.from_prepared_turn(_prepared_turn())
        adapter = PydanticAIModelAdapter(
            ModelProviderConfig(provider="openai", model_name="gpt-5.4")
        )
        executor = _FakeExecutor([_text_result("Repo inspection complete.")])
        events: list[tuple[str, object]] = []

        def on_model_call_completed(
            result: ModelExecutionResult,
            call_index: int,
            duration_ms: int,
        ) -> None:
            events.append(
                (
                    "complete",
                    (call_index, result.assistant_text, duration_ms >= 0),
                )
            )

        suspension = await runner.run(
            state=state,
            model_adapter=adapter,
            model_executor=executor,
            on_model_call_start=(
                lambda continuation_turn, call_index, assistant_started: events.append(
                    (
                        "start",
                        (call_index, assistant_started, continuation_turn.user_prompt),
                    )
                )
            ),
            on_record_model_call=(
                lambda continuation_turn, call_index: events.append(
                    (
                        "record",
                        (call_index, continuation_turn.user_prompt),
                    )
                )
            ),
            on_stream_event=lambda stream_event: events.append(
                ("stream", getattr(stream_event, "text", None))
            ),
            on_model_call_completed=on_model_call_completed,
            on_tool_calls=_unexpected_tool_calls,
            on_assistant_completed=lambda assistant_text: events.append(
                ("assistant", assistant_text)
            ),
        )

        assert suspension is None
        assert events[0] == ("start", (1, False, None))
        assert events[1] == ("record", (1, None))
        assert events[2] == ("stream", "Repo ")
        assert events[3] == ("stream", "inspection complete.")
        assert events[4][0] == "complete"
        completed_event = cast(tuple[int, str, bool], events[4][1])
        assert completed_event[0] == 1
        assert completed_event[1] == "Repo inspection complete."
        assert completed_event[2] is True
        assert events[5] == ("assistant", "Repo inspection complete.")

    asyncio.run(scenario())


def test_model_loop_runner_continues_after_tool_result() -> None:
    async def scenario() -> None:
        runner = ModelLoopRunner()
        state = ModelConversationState.from_prepared_turn(_prepared_turn())
        adapter = PydanticAIModelAdapter(
            ModelProviderConfig(provider="openai", model_name="gpt-5.4")
        )
        executor = _FakeExecutor(
            [
                _tool_result("read_file", {"path": "README.md"}, "provider-read-1"),
                _text_result("README says: Glassbox tool loop"),
            ]
        )
        seen_tool_calls: list[tuple[str, tuple[str, ...], int]] = []
        completed: list[str] = []

        async def on_tool_calls(tool_calls, current_state) -> None:
            seen_tool_calls.append(
                (
                    tool_calls[0].tool_name,
                    tuple(
                        type(message).__name__ for message in current_state.conversation
                    ),
                    current_state.model_call_index,
                )
            )
            current_state.append_message(
                ModelRequest(
                    parts=[],
                )
            )
            return None

        suspension = await runner.run(
            state=state,
            model_adapter=adapter,
            model_executor=executor,
            on_model_call_start=lambda *_args: None,
            on_record_model_call=lambda *_args: None,
            on_stream_event=lambda _event: None,
            on_model_call_completed=lambda *_args: None,
            on_tool_calls=on_tool_calls,
            on_assistant_completed=lambda assistant_text: completed.append(
                assistant_text
            ),
        )

        assert suspension is None
        assert seen_tool_calls == [("read_file", ("ModelRequest", "ModelResponse"), 1)]
        assert completed == ["README says: Glassbox tool loop"]
        assert len(executor.calls) == 2
        assert executor.calls[0].user_prompt is None
        assert len(executor.calls[1].message_history) == 3

    asyncio.run(scenario())


def test_model_loop_runner_returns_typed_suspension() -> None:
    async def scenario() -> None:
        runner = ModelLoopRunner()
        state = ModelConversationState.from_prepared_turn(_prepared_turn())
        adapter = PydanticAIModelAdapter(
            ModelProviderConfig(provider="openai", model_name="gpt-5.4")
        )
        executor = _FakeExecutor(
            [_tool_result("ask_user", {"question": "Continue?"}, "provider-ask-1")]
        )
        completed: list[str] = []

        async def on_tool_calls(tool_calls, current_state):
            assert tool_calls[0].tool_name == "ask_user"
            assert len(current_state.conversation) == 2
            return "awaiting_user_input"

        suspension = await runner.run(
            state=state,
            model_adapter=adapter,
            model_executor=executor,
            on_model_call_start=lambda *_args: None,
            on_record_model_call=lambda *_args: None,
            on_stream_event=lambda _event: None,
            on_model_call_completed=lambda *_args: None,
            on_tool_calls=on_tool_calls,
            on_assistant_completed=lambda assistant_text: completed.append(
                assistant_text
            ),
        )

        assert suspension == "awaiting_user_input"
        assert completed == []

    asyncio.run(scenario())


async def _unexpected_tool_calls(tool_calls, state):
    del tool_calls, state
    raise AssertionError("tool calls were not expected in this scenario")


def _prepared_turn() -> PreparedModelTurn:
    return PreparedModelTurn(
        model_name="openai:gpt-5.4",
        message_history=(),
        user_prompt="Inspect the repo",
        request_parameters=ModelRequestParameters(function_tools=[]),
        model_settings={},
        turn_context_payload=None,
    )


def _text_result(assistant_text: str) -> ModelExecutionResult:
    return ModelExecutionResult(
        assistant_text=assistant_text,
        tool_calls=(),
        model_response=ModelResponse(parts=[TextPart(content=assistant_text)]),
    )


def _tool_result(
    tool_name: str,
    arguments: dict[str, object],
    tool_call_id: str,
) -> ModelExecutionResult:
    return ModelExecutionResult(
        assistant_text="",
        tool_calls=(
            ModelToolCall(
                tool_name=tool_name,
                arguments=arguments,
                tool_call_id=tool_call_id,
            ),
        ),
        model_response=ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=tool_name,
                    args=arguments,
                    tool_call_id=tool_call_id,
                )
            ]
        ),
    )


def _text_chunks(text: str) -> tuple[str, ...]:
    words = text.split()
    if len(words) < 2:
        return (text,) if text else ()

    midpoint = max(1, len(words) // 2)
    leading = " ".join(words[:midpoint]).strip()
    trailing = " ".join(words[midpoint:]).strip()
    if not trailing:
        return (leading,)
    return (f"{leading} ", trailing)
