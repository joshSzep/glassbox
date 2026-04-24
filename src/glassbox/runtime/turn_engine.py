"""Turn engine for assistant responses with optional tool execution."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from time import perf_counter
from typing import cast

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from glassbox.core.events import (
    ApprovalRequested,
    ApprovalResolved,
    AssistantMessageCompleted,
    AssistantMessageDelta,
    AssistantMessageStarted,
    EventEnvelope,
    ModelCallCompleted,
    ModelCallStarted,
    ModelToolCallRequested,
    ReplayArtifactRecorded,
    SessionFailed,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    ToolOutputChunk,
    ToolOutputStream,
    TurnCompleted,
    TurnFailed,
    TurnStarted,
    TurnStatusChanged,
    UserAnswerProvided,
    UserMessageReceived,
    UserQuestionAsked,
)
from glassbox.core.ids import (
    MessageId,
    ToolCallId,
    new_approval_id,
    new_message_id,
    new_question_id,
    new_turn_id,
)
from glassbox.core.models import MessagePart, RuntimeNoteRecord, SessionRecord
from glassbox.core.types import ApprovalDecision, TurnStatus
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
from glassbox.runtime.context_builder import (
    TurnContext,
    TurnContextBuilder,
    build_repository_context_snapshot,
    build_working_set_snapshot,
    format_repository_context_for_prompt,
)
from glassbox.runtime.errors import SessionRuntimeFailure
from glassbox.runtime.logging import get_runtime_logger, runtime_log_extra
from glassbox.runtime.replay_capture import ReplayArtifactRecorder
from glassbox.services import ArtifactRepository, SessionRepository
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
    | ReplayArtifactRecorded
    | SessionFailed
    | ToolExecutionStarted
    | ToolExecutionCompleted
    | ToolOutputChunk
    | ApprovalRequested
    | UserQuestionAsked
    | UserAnswerProvided
    | TurnCompleted
    | TurnFailed
)

logger = get_runtime_logger("turn_engine")


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
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._session_repository = session_repository
        self._event_bus = event_bus
        self._context_builder = context_builder
        self._model_adapter_factory = model_adapter_factory
        self._model_executor_factory = model_executor_factory
        self._tool_runtime_factory = tool_runtime_factory
        self._replay_recorder = (
            ReplayArtifactRecorder(session_repository, artifact_repository)
            if artifact_repository is not None
            else None
        )

    async def run_for_user_message(self, event: EventEnvelope) -> None:
        """Process one persisted user message through the turn execution flow."""

        payload = event.payload
        if not isinstance(payload, UserMessageReceived):
            raise TypeError("turn engine requires a UserMessageReceived event")

        session = self._session_repository.get_session(event.session_id)
        if session is None:
            raise ValueError(f"unknown session_id: {event.session_id}")

        turn_id = new_turn_id()
        logger.info(
            "turn_started",
            extra=runtime_log_extra(
                runtime_event="turn_started",
                session_id=event.session_id,
                turn_id=turn_id,
                trigger_message_id=payload.message_id,
                trigger="user_message",
            ),
        )
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
            turn_context = self._build_live_turn_context(
                event.session_id,
                session,
                tool_runtime=tool_runtime,
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

            await self._run_model_loop(
                event.session_id,
                turn_id=turn_id,
                turn_context=turn_context,
                prepared_turn=prepared_turn,
                conversation=conversation,
                model_adapter=model_adapter,
                model_executor=model_executor,
                tool_runtime=tool_runtime,
                assistant_message_id=assistant_message_id,
                assistant_started=False,
                starting_model_call_index=0,
            )
        except Exception as exc:
            self._record_failed_turn(
                event.session_id,
                turn_id=turn_id,
                error=exc,
                trigger="user_message",
            )
            raise

    async def run_for_user_answer(self, event: EventEnvelope) -> None:
        """Resume a suspended turn after the operator answers an ask_user question."""

        payload = event.payload
        if not isinstance(payload, UserAnswerProvided):
            raise TypeError("run_for_user_answer requires a UserAnswerProvided event")

        session = self._session_repository.get_session(event.session_id)
        if session is None:
            raise ValueError(f"unknown session_id: {event.session_id}")

        # Locate the matching UserQuestionAsked event for conversation reconstruction.
        question_payload: UserQuestionAsked | None = None
        for ev in self._session_repository.read_session_events(event.session_id):
            if (
                isinstance(ev.payload, UserQuestionAsked)
                and ev.payload.question_id == payload.question_id
            ):
                question_payload = ev.payload
                break

        if question_payload is None:
            raise ValueError(
                "no UserQuestionAsked event found for question_id "
                f"{payload.question_id}"
            )

        turn_id = question_payload.turn_id
        logger.info(
            "turn_resumed_from_user_answer",
            extra=runtime_log_extra(
                runtime_event="turn_resumed_from_user_answer",
                session_id=event.session_id,
                turn_id=turn_id,
                question_id=payload.question_id,
            ),
        )

        # Find the AssistantMessageStarted event so we can reuse the same message_id.
        assistant_message_id: MessageId | None = None
        for ev in self._session_repository.read_events_by_correlation_id(
            event.session_id, turn_id=turn_id
        ):
            if isinstance(ev.payload, AssistantMessageStarted):
                assistant_message_id = ev.payload.message_id
                break

        if assistant_message_id is None:
            assistant_message_id = new_message_id()

        self._append_and_publish(
            event.session_id,
            [TurnStatusChanged(turn_id=turn_id, status=TurnStatus.BUILDING_CONTEXT)],
        )

        try:
            tool_runtime = (
                self._tool_runtime_factory(session)
                if self._tool_runtime_factory is not None
                else None
            )
            turn_context = self._build_live_turn_context(
                event.session_id,
                session,
                tool_runtime=tool_runtime,
            )
            system_prompt = build_system_prompt(turn_context)
            model_adapter = self._model_adapter_factory(session)
            model_executor = self._model_executor_factory(session)
            prepared_turn = model_adapter.build_turn_request(
                turn_context,
                system_prompt=system_prompt,
            )

            # Reconstruct the conversation up to (and including) the answer.
            conversation = _request_messages(prepared_turn)
            conversation.append(_make_ask_user_model_response(question_payload))
            conversation.append(
                _make_ask_user_tool_return(question_payload, payload.answer)
            )

            await self._run_model_loop(
                event.session_id,
                turn_id=turn_id,
                turn_context=turn_context,
                prepared_turn=prepared_turn,
                conversation=conversation,
                model_adapter=model_adapter,
                model_executor=model_executor,
                tool_runtime=tool_runtime,
                assistant_message_id=assistant_message_id,
                assistant_started=True,  # AssistantMessageStarted was emitted earlier
                starting_model_call_index=self._count_model_calls(
                    event.session_id,
                    turn_id=turn_id,
                ),
            )
        except Exception as exc:
            self._record_failed_turn(
                event.session_id,
                turn_id=turn_id,
                error=exc,
                trigger="user_answer",
                question_id=payload.question_id,
            )
            raise

    async def run_for_approval_resolution(self, event: EventEnvelope) -> None:
        """Resume a suspended turn after an operator approves or denies a tool call."""

        payload = event.payload
        if not isinstance(payload, ApprovalResolved):
            raise TypeError(
                "run_for_approval_resolution requires an ApprovalResolved event"
            )

        session = self._session_repository.get_session(event.session_id)
        if session is None:
            raise ValueError(f"unknown session_id: {event.session_id}")

        # Locate the matching ApprovalRequested event.
        approval_events = self._session_repository.read_events_by_correlation_id(
            event.session_id,
            approval_id=payload.approval_id,
        )
        approval_requested: ApprovalRequested | None = None
        for ev in approval_events:
            if isinstance(ev.payload, ApprovalRequested):
                approval_requested = ev.payload
                break

        if approval_requested is None:
            raise ValueError(
                "no ApprovalRequested event found for approval_id "
                f"{payload.approval_id}"
            )
        if (
            approval_requested.tool_call_id is None
            or approval_requested.provider_tool_call_id is None
        ):
            # Approval was created without turn metadata (e.g. legacy or external).
            # State transition is already persisted; the turn cannot be resumed.
            return

        turn_id = approval_requested.turn_id
        logger.info(
            "turn_resumed_from_approval",
            extra=runtime_log_extra(
                runtime_event="turn_resumed_from_approval",
                session_id=event.session_id,
                turn_id=turn_id,
                approval_id=payload.approval_id,
                decision=payload.decision,
            ),
        )

        # Find the AssistantMessageStarted event for this turn.
        turn_events = self._session_repository.read_events_by_correlation_id(
            event.session_id,
            turn_id=turn_id,
        )
        assistant_message_id: MessageId | None = None
        for ev in turn_events:
            if isinstance(ev.payload, AssistantMessageStarted):
                assistant_message_id = ev.payload.message_id
                break
        if assistant_message_id is None:
            assistant_message_id = new_message_id()

        self._append_and_publish(
            event.session_id,
            [TurnStatusChanged(turn_id=turn_id, status=TurnStatus.BUILDING_CONTEXT)],
        )

        try:
            tool_runtime = (
                self._tool_runtime_factory(session)
                if self._tool_runtime_factory is not None
                else None
            )
            turn_context = self._build_live_turn_context(
                event.session_id,
                session,
                tool_runtime=tool_runtime,
            )
            system_prompt = build_system_prompt(turn_context)
            model_adapter = self._model_adapter_factory(session)
            model_executor = self._model_executor_factory(session)
            prepared_turn = model_adapter.build_turn_request(
                turn_context,
                system_prompt=system_prompt,
            )

            # Reconstruct conversation: history + the model's ToolCallPart.
            conversation = _request_messages(prepared_turn)
            # Read the original tool arguments before branching on the decision so
            # they are available both for _make_approval_model_response and for
            # actually executing the approved call.
            original_tool_arguments = _find_tool_arguments(
                turn_events, approval_requested.tool_call_id
            )
            conversation.append(
                _make_approval_model_response(
                    approval_requested, original_tool_arguments
                )
            )

            if payload.decision == ApprovalDecision.APPROVED:
                if tool_runtime is None:
                    raise ValueError(
                        "tool runtime is required to execute an approved tool call"
                    )

                # Re-prepare the tool call (validates args, evaluates policy).
                tool_call = ModelToolCall(
                    tool_name=approval_requested.subject,
                    arguments=original_tool_arguments,
                    tool_call_id=approval_requested.provider_tool_call_id,
                )
                prepared_tool_call = tool_runtime.prepare_tool_call(tool_call)

                self._append_and_publish(
                    event.session_id,
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
                        event.session_id,
                        [
                            ToolOutputChunk(
                                turn_id=turn_id,
                                tool_call_id=_tool_call_id,
                                stream=cast(ToolOutputStream, stream),
                                chunk=chunk,
                            )
                        ],
                    )

                try:
                    execution_result = await tool_runtime.execute_approved(
                        prepared_tool_call, on_output_chunk=_on_output_chunk
                    )
                except Exception as exc:
                    self._append_and_publish(
                        event.session_id,
                        [
                            ToolExecutionCompleted(
                                turn_id=turn_id,
                                tool_call_id=prepared_tool_call.event_tool_call_id,
                                success=False,
                                summary=str(exc),
                            )
                        ],
                    )
                    logger.warning(
                        "tool_execution_completed",
                        extra=runtime_log_extra(
                            runtime_event="tool_execution_completed",
                            session_id=event.session_id,
                            turn_id=turn_id,
                            tool_call_id=prepared_tool_call.event_tool_call_id,
                            tool_name=prepared_tool_call.tool_name,
                            success=False,
                        ),
                    )
                    self._record_replay_tool_result(
                        event.session_id,
                        turn_id=turn_id,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                        provider_tool_call_id=prepared_tool_call.provider_tool_call_id,
                        tool_name=prepared_tool_call.tool_name,
                        success=False,
                        summary=str(exc),
                        error_message=str(exc),
                    )
                    raise
                self._append_and_publish(
                    event.session_id,
                    [
                        ToolExecutionCompleted(
                            turn_id=turn_id,
                            tool_call_id=execution_result.event_tool_call_id,
                            success=True,
                            summary=execution_result.summary,
                        )
                    ],
                )
                self._record_replay_tool_execution_result(
                    event.session_id,
                    turn_id=turn_id,
                    execution_result=execution_result,
                )
                conversation.append(execution_result.to_model_request())
            else:
                # DENIED — inject a denial message as the tool return.
                conversation.append(_make_denial_tool_return(approval_requested))

            await self._run_model_loop(
                event.session_id,
                turn_id=turn_id,
                turn_context=turn_context,
                prepared_turn=prepared_turn,
                conversation=conversation,
                model_adapter=model_adapter,
                model_executor=model_executor,
                tool_runtime=tool_runtime,
                assistant_message_id=assistant_message_id,
                assistant_started=True,
                starting_model_call_index=self._count_model_calls(
                    event.session_id,
                    turn_id=turn_id,
                ),
            )
        except Exception as exc:
            self._record_failed_turn(
                event.session_id,
                turn_id=turn_id,
                error=exc,
                trigger="approval_resolution",
                approval_id=payload.approval_id,
            )
            raise

    def _build_live_turn_context(
        self,
        session_id,
        session: SessionRecord,
        *,
        tool_runtime: ToolRuntime | None,
    ) -> TurnContext:
        repository_context = format_repository_context_for_prompt(
            build_repository_context_snapshot(session.cwd)
        )
        runtime_notes = self._session_repository.list_runtime_notes(session_id)
        return self._context_builder.build(
            session_id,
            tool_registry=(
                tool_runtime.tool_registry if tool_runtime is not None else None
            ),
            repo_context=repository_context,
            memory_notes=[
                _format_runtime_note_for_prompt(note) for note in runtime_notes
            ],
            working_set=build_working_set_snapshot(
                self._session_repository,
                session_id,
            ),
        )

    def _record_failed_turn(
        self,
        session_id,
        *,
        turn_id,
        error: Exception,
        trigger: str,
        approval_id=None,
        question_id=None,
    ) -> None:
        runtime_event = (
            "session_failed"
            if isinstance(error, SessionRuntimeFailure)
            else "turn_failed"
        )
        logger.exception(
            runtime_event,
            extra=runtime_log_extra(
                runtime_event=runtime_event,
                session_id=session_id,
                turn_id=turn_id,
                approval_id=approval_id,
                question_id=question_id,
                error_message=str(error),
                trigger=trigger,
            ),
        )
        failure_events: list[TurnEnginePayload] = [
            TurnStatusChanged(
                turn_id=turn_id,
                status=TurnStatus.FAILED,
            ),
            TurnFailed(turn_id=turn_id, error_message=str(error)),
        ]
        if isinstance(error, SessionRuntimeFailure):
            failure_events.append(
                SessionFailed(
                    error_message=str(error),
                    retryable=error.retryable,
                )
            )
        self._append_and_publish(session_id, failure_events)
        self._record_replay_turn_output(
            session_id,
            turn_id=turn_id,
            outcome="failed",
            details={
                "error_message": str(error),
                "trigger": trigger,
                "approval_id": str(approval_id) if approval_id is not None else None,
                "question_id": str(question_id) if question_id is not None else None,
            },
        )

    async def _run_model_loop(
        self,
        session_id,
        *,
        turn_id,
        turn_context,
        prepared_turn: PreparedModelTurn,
        conversation: list[ModelMessage],
        model_adapter: ModelAdapter,
        model_executor: ModelExecutor,
        tool_runtime: ToolRuntime | None,
        assistant_message_id: MessageId,
        assistant_started: bool,
        starting_model_call_index: int,
    ) -> None:
        """Run the model call + tool execution loop to completion or suspension."""

        continuation_turn = _continuation_turn(prepared_turn, conversation)
        model_call_index = starting_model_call_index

        while True:
            model_call_index += 1
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

            self._append_and_publish(session_id, model_call_events)
            self._record_replay_model_call(
                session_id,
                turn_id=turn_id,
                turn_context=turn_context,
                prepared_turn=continuation_turn,
                call_index=model_call_index,
            )

            start = perf_counter()
            result = await model_executor.execute_stream(
                continuation_turn,
                stream_translator=model_adapter.new_stream_translator(),
                on_event=lambda stream_event: self._handle_stream_event(
                    session_id,
                    assistant_message_id=assistant_message_id,
                    stream_event=stream_event,
                ),
            )
            duration_ms = max(0, int((perf_counter() - start) * 1000))
            self._append_and_publish(
                session_id,
                [
                    ModelCallCompleted(
                        turn_id=turn_id,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        duration_ms=duration_ms,
                    )
                ],
            )
            logger.info(
                "model_call_completed",
                extra=runtime_log_extra(
                    runtime_event="model_call_completed",
                    session_id=session_id,
                    turn_id=turn_id,
                    provider=model_adapter.config.provider or "local",
                    model_name=model_adapter.config.model_name,
                    duration_ms=duration_ms,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                ),
            )

            if result.tool_calls:
                if tool_runtime is None:
                    raise ValueError(
                        "tool calls are not supported by the turn engine yet"
                    )

                conversation.append(result.model_response)
                tool_loop_outcome = await self._execute_tool_calls(
                    session_id,
                    turn_id=turn_id,
                    tool_runtime=tool_runtime,
                    tool_calls=result.tool_calls,
                    conversation=conversation,
                )
                if tool_loop_outcome is not None:
                    return

                continuation_turn = _continuation_turn(prepared_turn, conversation)
                continue

            assistant_text = result.assistant_text.strip()
            if assistant_text == "":
                raise ValueError("assistant response must not be blank")

            self._append_and_publish(
                session_id,
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
            logger.info(
                "turn_completed",
                extra=runtime_log_extra(
                    runtime_event="turn_completed",
                    session_id=session_id,
                    turn_id=turn_id,
                    outcome="completed",
                ),
            )
            self._record_replay_turn_output(
                session_id,
                turn_id=turn_id,
                outcome="completed",
                assistant_text=assistant_text,
            )
            return

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
            self._record_replay_tool_request(
                session_id,
                turn_id=turn_id,
                prepared_tool_call=prepared_tool_call,
            )

            if prepared_tool_call.policy_decision.requires_approval:
                approval_id = new_approval_id()
                logger.info(
                    "approval_requested",
                    extra=runtime_log_extra(
                        runtime_event="approval_requested",
                        session_id=session_id,
                        turn_id=turn_id,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                        approval_id=approval_id,
                        tool_name=prepared_tool_call.tool_name,
                    ),
                )
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
                            tool_call_id=prepared_tool_call.event_tool_call_id,
                            provider_tool_call_id=prepared_tool_call.provider_tool_call_id,
                        ),
                        TurnCompleted(turn_id=turn_id, outcome="awaiting_approval"),
                    ],
                )
                self._record_replay_turn_output(
                    session_id,
                    turn_id=turn_id,
                    outcome="awaiting_approval",
                    details={
                        "approval_id": str(approval_id),
                        "tool_call_id": str(prepared_tool_call.event_tool_call_id),
                        "tool_name": prepared_tool_call.tool_name,
                        "reason": prepared_tool_call.policy_decision.reason,
                    },
                )
                return "awaiting_approval"

            if not prepared_tool_call.policy_decision.allowed:
                logger.warning(
                    "tool_execution_blocked",
                    extra=runtime_log_extra(
                        runtime_event="tool_execution_blocked",
                        session_id=session_id,
                        turn_id=turn_id,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                        tool_name=prepared_tool_call.tool_name,
                        reason=prepared_tool_call.policy_decision.reason,
                    ),
                )
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
                self._record_replay_tool_result(
                    session_id,
                    turn_id=turn_id,
                    tool_call_id=prepared_tool_call.event_tool_call_id,
                    provider_tool_call_id=prepared_tool_call.provider_tool_call_id,
                    tool_name=prepared_tool_call.tool_name,
                    success=False,
                    summary=prepared_tool_call.policy_decision.reason,
                    error_message=prepared_tool_call.policy_decision.reason,
                )
                raise ValueError(prepared_tool_call.policy_decision.reason)

            # Intercept ask_user: suspend the turn and wait for operator input.
            if prepared_tool_call.tool_name == "ask_user":
                question_id = new_question_id()
                question_text = str(
                    prepared_tool_call.validated_arguments.model_dump().get(
                        "question", ""
                    )
                )
                logger.info(
                    "user_question_asked",
                    extra=runtime_log_extra(
                        runtime_event="user_question_asked",
                        session_id=session_id,
                        turn_id=turn_id,
                        question_id=question_id,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                    ),
                )
                self._append_and_publish(
                    session_id,
                    [
                        TurnStatusChanged(
                            turn_id=turn_id,
                            status=TurnStatus.AWAITING_USER_INPUT,
                        ),
                        UserQuestionAsked(
                            question_id=question_id,
                            turn_id=turn_id,
                            tool_call_id=prepared_tool_call.event_tool_call_id,
                            provider_tool_call_id=prepared_tool_call.provider_tool_call_id,
                            question=question_text,
                        ),
                        TurnCompleted(turn_id=turn_id, outcome="awaiting_user_input"),
                    ],
                )
                self._record_replay_turn_output(
                    session_id,
                    turn_id=turn_id,
                    outcome="awaiting_user_input",
                    details={
                        "question_id": str(question_id),
                        "tool_call_id": str(prepared_tool_call.event_tool_call_id),
                        "question": question_text,
                    },
                )
                return "awaiting_user_input"

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

            try:
                execution_result = await tool_runtime.execute(
                    prepared_tool_call, on_output_chunk=_on_output_chunk
                )
            except Exception as exc:
                self._append_and_publish(
                    session_id,
                    [
                        ToolExecutionCompleted(
                            turn_id=turn_id,
                            tool_call_id=prepared_tool_call.event_tool_call_id,
                            success=False,
                            summary=str(exc),
                        )
                    ],
                )
                logger.warning(
                    "tool_execution_completed",
                    extra=runtime_log_extra(
                        runtime_event="tool_execution_completed",
                        session_id=session_id,
                        turn_id=turn_id,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                        tool_name=prepared_tool_call.tool_name,
                        success=False,
                    ),
                )
                self._record_replay_tool_result(
                    session_id,
                    turn_id=turn_id,
                    tool_call_id=prepared_tool_call.event_tool_call_id,
                    provider_tool_call_id=prepared_tool_call.provider_tool_call_id,
                    tool_name=prepared_tool_call.tool_name,
                    success=False,
                    summary=str(exc),
                    error_message=str(exc),
                )
                raise
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
            self._record_replay_tool_execution_result(
                session_id,
                turn_id=turn_id,
                execution_result=execution_result,
            )
            logger.info(
                "tool_execution_completed",
                extra=runtime_log_extra(
                    runtime_event="tool_execution_completed",
                    session_id=session_id,
                    turn_id=turn_id,
                    tool_call_id=execution_result.event_tool_call_id,
                    tool_name=prepared_tool_call.tool_name,
                    success=True,
                ),
            )
            conversation.append(execution_result.to_model_request())

        return None

    def _count_model_calls(self, session_id, *, turn_id) -> int:
        return sum(
            1
            for event in self._session_repository.read_events_by_correlation_id(
                session_id,
                turn_id=turn_id,
            )
            if isinstance(event.payload, ModelCallStarted)
        )

    def _record_replay_model_call(
        self,
        session_id,
        *,
        turn_id,
        turn_context,
        prepared_turn: PreparedModelTurn,
        call_index: int,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_model_call(
            session_id,
            turn_id,
            call_index=call_index,
            turn_context=turn_context,
            prepared_turn=prepared_turn,
        )

    def _record_replay_tool_request(
        self,
        session_id,
        *,
        turn_id,
        prepared_tool_call,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_tool_request(
            session_id,
            turn_id,
            prepared_tool_call,
        )

    def _record_replay_tool_execution_result(
        self,
        session_id,
        *,
        turn_id,
        execution_result,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_tool_execution_result(
            session_id,
            turn_id,
            execution_result,
        )

    def _record_replay_tool_result(
        self,
        session_id,
        *,
        turn_id,
        tool_call_id,
        provider_tool_call_id: str,
        tool_name: str,
        success: bool,
        summary: str,
        error_message: str | None = None,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_tool_result(
            session_id,
            turn_id,
            tool_call_id=tool_call_id,
            provider_tool_call_id=provider_tool_call_id,
            tool_name=tool_name,
            success=success,
            summary=summary,
            error_message=error_message,
        )

    def _record_replay_turn_output(
        self,
        session_id,
        *,
        turn_id,
        outcome,
        assistant_text: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        if self._replay_recorder is None:
            return
        self._replay_recorder.record_turn_output(
            session_id,
            turn_id,
            outcome=outcome,
            assistant_text=assistant_text,
            details=details,
        )

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


def _format_runtime_note_for_prompt(note: RuntimeNoteRecord) -> str:
    if note.inherited:
        return f"[inherited {note.category}] {note.message}"
    return f"[{note.category}] {note.message}"


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
        turn_context_payload=prepared_turn.turn_context_payload,
    )


def _make_ask_user_model_response(question_payload: UserQuestionAsked) -> ModelResponse:
    """Reconstruct the model's side of an ask_user call as a ModelResponse."""

    timestamp = datetime.now(tz=UTC)
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="ask_user",
                tool_call_id=question_payload.provider_tool_call_id,
                args={"question": question_payload.question},
            )
        ],
        timestamp=timestamp,
    )


def _make_ask_user_tool_return(
    question_payload: UserQuestionAsked,
    answer: str,
) -> ModelRequest:
    """Reconstruct the tool-return message for an ask_user call."""

    timestamp = datetime.now(tz=UTC)
    return ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name="ask_user",
                tool_call_id=question_payload.provider_tool_call_id,
                content={"answer": answer},
                timestamp=timestamp,
            )
        ],
        timestamp=timestamp,
    )


def _make_approval_model_response(
    approval_requested: ApprovalRequested,
    arguments: dict[str, object] | None = None,
) -> ModelResponse:
    """Reconstruct the model's ToolCallPart for the approved/denied tool call."""

    assert approval_requested.provider_tool_call_id is not None
    timestamp = datetime.now(tz=UTC)
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name=approval_requested.subject,
                tool_call_id=approval_requested.provider_tool_call_id,
                args=arguments or {},
            )
        ],
        timestamp=timestamp,
    )


def _make_denial_tool_return(approval_requested: ApprovalRequested) -> ModelRequest:
    """Construct a tool-return message communicating that the action was denied."""

    assert approval_requested.provider_tool_call_id is not None
    timestamp = datetime.now(tz=UTC)
    return ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name=approval_requested.subject,
                tool_call_id=approval_requested.provider_tool_call_id,
                content={
                    "error": f"Action denied by operator: {approval_requested.reason}"
                },
                timestamp=timestamp,
            )
        ],
        timestamp=timestamp,
    )


def _find_tool_arguments(
    turn_events: list[EventEnvelope],
    tool_call_id: ToolCallId,
) -> dict[str, object]:
    """Extract the original arguments for a tool call from persisted turn events."""

    for ev in turn_events:
        if (
            isinstance(ev.payload, ModelToolCallRequested)
            and ev.payload.tool_call_id == tool_call_id
        ):
            raw: object = json.loads(ev.payload.arguments_json)
            if isinstance(raw, dict):
                return {str(k): v for k, v in raw.items()}
    return {}
