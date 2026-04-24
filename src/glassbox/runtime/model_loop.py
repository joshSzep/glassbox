"""Shared model-loop control flow for live turns and replay-backed execution."""

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from time import perf_counter
from typing import Literal

from pydantic_ai.messages import ModelMessage
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import UserPromptPart

from glassbox.llm import ModelAdapter
from glassbox.llm import ModelAdapterStreamEvent
from glassbox.llm import ModelExecutionResult
from glassbox.llm import ModelExecutor
from glassbox.llm import ModelToolCall
from glassbox.llm import PreparedModelTurn

type ModelLoopSuspension = Literal["awaiting_approval", "awaiting_user_input"]

type ModelCallStartHandler = Callable[[PreparedModelTurn, int, bool], None]
type ModelCallRecordHandler = Callable[[PreparedModelTurn, int], None]
type ModelCallCompleteHandler = Callable[[ModelExecutionResult, int, int], None]
type StreamEventHandler = Callable[[ModelAdapterStreamEvent], None]
type ToolCallHandler = Callable[
    [tuple[ModelToolCall, ...], "ModelConversationState"],
    Awaitable[ModelLoopSuspension | None],
]
type AssistantCompleteHandler = Callable[[str], None]


@dataclass(slots=True)
class ModelConversationState:
    """Mutable conversation state for one model-loop execution path."""

    prepared_turn: PreparedModelTurn
    conversation: list[ModelMessage] = field(default_factory=list)
    assistant_started: bool = False
    model_call_index: int = 0

    @classmethod
    def from_prepared_turn(
        cls,
        prepared_turn: PreparedModelTurn,
        *,
        conversation: list[ModelMessage] | None = None,
        assistant_started: bool = False,
        starting_model_call_index: int = 0,
    ) -> ModelConversationState:
        return cls(
            prepared_turn=prepared_turn,
            conversation=(
                list(conversation)
                if conversation is not None
                else initial_model_messages(prepared_turn)
            ),
            assistant_started=assistant_started,
            model_call_index=starting_model_call_index,
        )

    def next_model_call_index(self) -> int:
        self.model_call_index += 1
        return self.model_call_index

    def continuation_turn(self) -> PreparedModelTurn:
        return PreparedModelTurn(
            model_name=self.prepared_turn.model_name,
            message_history=tuple(self.conversation),
            user_prompt=None,
            request_parameters=self.prepared_turn.request_parameters,
            model_settings=self.prepared_turn.model_settings,
            turn_context_payload=self.prepared_turn.turn_context_payload,
        )

    def append_message(self, message: ModelMessage) -> None:
        self.conversation.append(message)


class ModelLoopRunner:
    """Run the shared model-call and continuation loop to completion."""

    async def run(
        self,
        *,
        state: ModelConversationState,
        model_adapter: ModelAdapter,
        model_executor: ModelExecutor,
        on_model_call_start: ModelCallStartHandler,
        on_record_model_call: ModelCallRecordHandler,
        on_stream_event: StreamEventHandler,
        on_model_call_completed: ModelCallCompleteHandler,
        on_tool_calls: ToolCallHandler,
        on_assistant_completed: AssistantCompleteHandler,
    ) -> ModelLoopSuspension | None:
        while True:
            call_index = state.next_model_call_index()
            continuation_turn = state.continuation_turn()
            on_model_call_start(
                continuation_turn,
                call_index,
                state.assistant_started,
            )
            state.assistant_started = True
            on_record_model_call(continuation_turn, call_index)

            start = perf_counter()
            result = await model_executor.execute_stream(
                continuation_turn,
                stream_translator=model_adapter.new_stream_translator(),
                on_event=on_stream_event,
            )
            duration_ms = max(0, int((perf_counter() - start) * 1000))
            on_model_call_completed(result, call_index, duration_ms)

            if result.tool_calls:
                state.append_message(result.model_response)
                tool_loop_outcome = await on_tool_calls(result.tool_calls, state)
                if tool_loop_outcome is not None:
                    return tool_loop_outcome
                continue

            assistant_text = result.assistant_text.strip()
            if assistant_text == "":
                raise ValueError("assistant response must not be blank")

            on_assistant_completed(assistant_text)
            return None


def initial_model_messages(prepared_turn: PreparedModelTurn) -> list[ModelMessage]:
    """Build the initial request message list for a prepared turn."""

    messages = list(prepared_turn.message_history)
    if prepared_turn.user_prompt is None:
        return messages

    timestamp = datetime.now(tz=UTC)
    messages.append(
        ModelRequest(
            parts=[
                UserPromptPart(
                    content=prepared_turn.user_prompt,
                    timestamp=timestamp,
                )
            ],
            timestamp=timestamp,
        )
    )
    return messages
