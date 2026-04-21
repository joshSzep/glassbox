"""Turn engine for assistant responses with optional tool execution."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from time import perf_counter
from typing import cast

from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart

from glassbox.core.events import (
    ApprovalRequested,
    AssistantMessageCompleted,
    AssistantMessageDelta,
    AssistantMessageStarted,
    EventEnvelope,
    ModelCallCompleted,
    ModelCallStarted,
    ModelToolCallRequested,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    ToolOutputChunk,
    ToolOutputStream,
    TurnCompleted,
    TurnFailed,
    TurnStarted,
    TurnStatusChanged,
    UserMessageReceived,
)
from glassbox.core.ids import ToolCallId, new_approval_id, new_message_id, new_turn_id
from glassbox.core.models import MessagePart, SessionRecord
from glassbox.core.types import TurnStatus
from glassbox.llm import (
    ModelAdapter,
    ModelExecutor,
    ModelTextDelta,
    ModelToolCall,
    ModelToolCallDelta,
    PreparedModelTurn,
    build_system_prompt,
)
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.services import SessionRepository
from glassbox.tools import ToolRuntime

ModelAdapterFactory = Callable[[SessionRecord], ModelAdapter]
ModelExecutorFactory = Callable[[SessionRecord], ModelExecutor]
ToolRuntimeFactory = Callable[[SessionRecord], ToolRuntime]
TurnEnginePayload = (
    TurnStarted
    | TurnStatusChanged
    | ModelCallStarted
    | ModelCallCompleted
    | AssistantMessageStarted
    | AssistantMessageDelta
    | AssistantMessageCompleted
    | ModelToolCallRequested
    | ToolExecutionStarted
    | ToolExecutionCompleted
    | ToolOutputChunk
    | ApprovalRequested
    | TurnCompleted
    | TurnFailed
)


class TurnEngine:
    """Run one model turn from a persisted user message event."""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_bus: EventBus[EventEnvelope],
        context_builder: TurnContextBuilder,
        model_adapter_factory: ModelAdapterFactory,
        model_executor_factory: ModelExecutorFactory,
        tool_runtime_factory: ToolRuntimeFactory | None = None,
    ) -> None:
        self._session_repository = session_repository
        self._event_bus = event_bus
        self._context_builder = context_builder
        self._model_adapter_factory = model_adapter_factory
        self._model_executor_factory = model_executor_factory
        self._tool_runtime_factory = tool_runtime_factory

    async def run_for_user_message(self, event: EventEnvelope) -> None:
        """Process one persisted user message through the turn execution flow."""

        payload = event.payload
        if not isinstance(payload, UserMessageReceived):
            raise TypeError("turn engine requires a UserMessageReceived event")

        session = self._session_repository.get_session(event.session_id)
        if session is None:
            raise ValueError(f"unknown session_id: {event.session_id}")

        turn_id = new_turn_id()
        self._append_and_publish(
            event.session_id,
            [
                TurnStarted(
                    turn_id=turn_id,
                    trigger_message_id=payload.message_id,
                ),
                TurnStatusChanged(
                    turn_id=turn_id,
                    status=TurnStatus.BUILDING_CONTEXT,
                ),
            ],
        )

        try:
            tool_runtime = (
                self._tool_runtime_factory(session)
                if self._tool_runtime_factory is not None
                else None
            )
            turn_context = self._context_builder.build(
                event.session_id,
                tool_registry=(
                    tool_runtime.tool_registry if tool_runtime is not None else None
                ),
            )
            system_prompt = build_system_prompt(turn_context)
            model_adapter = self._model_adapter_factory(session)
            model_executor = self._model_executor_factory(session)
            prepared_turn = model_adapter.build_turn_request(
                turn_context,
                system_prompt=system_prompt,
            )
            assistant_message_id = new_message_id()

            conversation = _request_messages(prepared_turn)
            continuation_turn = _continuation_turn(prepared_turn, conversation)
            assistant_started = False

            while True:
                model_call_events: list[TurnEnginePayload] = [
                    TurnStatusChanged(
                        turn_id=turn_id,
                        status=TurnStatus.CALLING_MODEL,
                    ),
                    ModelCallStarted(
                        turn_id=turn_id,
                        provider=model_adapter.config.provider or "local",
                        model_name=model_adapter.config.model_name,
                    ),
                ]
                if not assistant_started:
                    model_call_events.append(
                        AssistantMessageStarted(message_id=assistant_message_id)
                    )
                    assistant_started = True

                self._append_and_publish(event.session_id, model_call_events)

                start = perf_counter()
                result = await model_executor.execute_stream(
                    continuation_turn,
                    stream_translator=model_adapter.new_stream_translator(),
                    on_event=lambda stream_event: self._handle_stream_event(
                        event.session_id,
                        assistant_message_id=assistant_message_id,
                        stream_event=stream_event,
                    ),
                )
                duration_ms = max(0, int((perf_counter() - start) * 1000))
                self._append_and_publish(
                    event.session_id,
                    [
                        ModelCallCompleted(
                            turn_id=turn_id,
                            input_tokens=result.input_tokens,
                            output_tokens=result.output_tokens,
                            duration_ms=duration_ms,
                        )
                    ],
                )

                if result.tool_calls:
                    if tool_runtime is None:
                        raise ValueError(
                            "tool calls are not supported by the turn engine yet"
                        )

                    conversation.append(result.model_response)
                    tool_loop_outcome = await self._execute_tool_calls(
                        event.session_id,
                        turn_id=turn_id,
                        tool_runtime=tool_runtime,
                        tool_calls=result.tool_calls,
                        conversation=conversation,
                    )
                    if tool_loop_outcome == "awaiting_approval":
                        return

                    continuation_turn = _continuation_turn(prepared_turn, conversation)
                    continue

                assistant_text = result.assistant_text.strip()
                if assistant_text == "":
                    raise ValueError("assistant response must not be blank")

                self._append_and_publish(
                    event.session_id,
                    [
                        TurnStatusChanged(
                            turn_id=turn_id,
                            status=TurnStatus.ASSEMBLING_RESPONSE,
                        ),
                        AssistantMessageCompleted(
                            message_id=assistant_message_id,
                            parts=[MessagePart(kind="text", text=assistant_text)],
                        ),
                        TurnStatusChanged(
                            turn_id=turn_id,
                            status=TurnStatus.COMPLETED,
                        ),
                        TurnCompleted(turn_id=turn_id, outcome="completed"),
                    ],
                )
                return
        except Exception as exc:
            self._append_and_publish(
                event.session_id,
                [
                    TurnStatusChanged(
                        turn_id=turn_id,
                        status=TurnStatus.FAILED,
                    ),
                    TurnFailed(turn_id=turn_id, error_message=str(exc)),
                ],
            )
            raise

    def _append_and_publish(
        self,
        session_id,
        payloads: Sequence[TurnEnginePayload],
    ) -> list[EventEnvelope]:
        stored_events = self._session_repository.append_events(
            [
                EventEnvelope(session_id=session_id, sequence=0, payload=payload)
                for payload in payloads
            ]
        )
        for stored_event in stored_events:
            self._event_bus.publish(stored_event)
        return stored_events

    async def _execute_tool_calls(
        self,
        session_id,
        *,
        turn_id,
        tool_runtime: ToolRuntime,
        tool_calls: tuple[ModelToolCall, ...],
        conversation: list[ModelMessage],
    ) -> str | None:
        for tool_call in tool_calls:
            prepared_tool_call = tool_runtime.prepare_tool_call(tool_call)
            self._append_and_publish(
                session_id,
                [
                    ModelToolCallRequested(
                        turn_id=turn_id,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                        tool_name=prepared_tool_call.tool_name,
                        arguments_json=json.dumps(
                            prepared_tool_call.validated_arguments.model_dump(
                                mode="json"
                            ),
                            sort_keys=True,
                        ),
                    )
                ],
            )

            if prepared_tool_call.policy_decision.requires_approval:
                approval_id = new_approval_id()
                self._append_and_publish(
                    session_id,
                    [
                        TurnStatusChanged(
                            turn_id=turn_id,
                            status=TurnStatus.AWAITING_APPROVAL,
                        ),
                        ApprovalRequested(
                            approval_id=approval_id,
                            turn_id=turn_id,
                            reason=prepared_tool_call.policy_decision.reason,
                            subject=prepared_tool_call.tool_name,
                        ),
                        TurnCompleted(turn_id=turn_id, outcome="awaiting_approval"),
                    ],
                )
                return "awaiting_approval"

            if not prepared_tool_call.policy_decision.allowed:
                self._append_and_publish(
                    session_id,
                    [
                        ToolExecutionCompleted(
                            turn_id=turn_id,
                            tool_call_id=prepared_tool_call.event_tool_call_id,
                            success=False,
                            summary=prepared_tool_call.policy_decision.reason,
                        )
                    ],
                )
                raise ValueError(prepared_tool_call.policy_decision.reason)

            self._append_and_publish(
                session_id,
                [
                    TurnStatusChanged(
                        turn_id=turn_id,
                        status=TurnStatus.EXECUTING_TOOL,
                    ),
                    ToolExecutionStarted(
                        turn_id=turn_id,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                        tool_name=prepared_tool_call.tool_name,
                    ),
                ],
            )
            tool_call_id_for_chunk = prepared_tool_call.event_tool_call_id

            def _on_output_chunk(
                stream: str,
                chunk: str,
                *,
                _tool_call_id: ToolCallId = tool_call_id_for_chunk,
            ) -> None:
                self._append_and_publish(
                    session_id,
                    [
                        ToolOutputChunk(
                            turn_id=turn_id,
                            tool_call_id=_tool_call_id,
                            stream=cast(ToolOutputStream, stream),
                            chunk=chunk,
                        )
                    ],
                )

            execution_result = await tool_runtime.execute(
                prepared_tool_call, on_output_chunk=_on_output_chunk
            )
            self._append_and_publish(
                session_id,
                [
                    ToolExecutionCompleted(
                        turn_id=turn_id,
                        tool_call_id=execution_result.event_tool_call_id,
                        success=True,
                        summary=execution_result.summary,
                    )
                ],
            )
            conversation.append(execution_result.to_model_request())

        return None

    def _handle_stream_event(
        self,
        session_id,
        *,
        assistant_message_id,
        stream_event,
    ) -> None:
        if isinstance(stream_event, ModelTextDelta):
            self._append_and_publish(
                session_id,
                [
                    AssistantMessageDelta(
                        message_id=assistant_message_id,
                        delta=stream_event.text,
                    )
                ],
            )
            return

        if isinstance(stream_event, ModelToolCallDelta | ModelToolCall):
            return


def _request_messages(prepared_turn: PreparedModelTurn) -> list[ModelMessage]:
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


def _continuation_turn(
    prepared_turn: PreparedModelTurn,
    conversation: list[ModelMessage],
) -> PreparedModelTurn:
    return PreparedModelTurn(
        model_name=prepared_turn.model_name,
        message_history=tuple(conversation),
        user_prompt=None,
        request_parameters=prepared_turn.request_parameters,
        model_settings=prepared_turn.model_settings,
    )
