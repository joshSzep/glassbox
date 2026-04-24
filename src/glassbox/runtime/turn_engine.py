"""Turn engine for assistant responses with optional tool execution."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import cast

from pydantic_ai.messages import (
    ModelMessage,
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
    ToolArtifactRecorded,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    ToolOutputChunk,
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
    new_message_id,
    new_turn_id,
)
from glassbox.core.models import MessagePart, SessionRecord
from glassbox.core.types import ApprovalDecision, TurnStatus
from glassbox.llm import (
    ModelAdapter,
    ModelExecutor,
    ModelTextDelta,
    ModelToolCall,
    ModelToolCallDelta,
    PreparedModelTurn,
)
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context_builder import (
    PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
    TurnContext,
    TurnContextBuilder,
    build_pytest_failure_digest_artifact,
)
from glassbox.runtime.errors import SessionRuntimeFailure
from glassbox.runtime.logging import get_runtime_logger, runtime_log_extra
from glassbox.runtime.model_loop import (
    ModelConversationState,
    ModelLoopRunner,
    ModelLoopSuspension,
)
from glassbox.runtime.replay_capture import ReplayArtifactRecorder
from glassbox.runtime.turn_preparation import LiveTurnPreparation
from glassbox.runtime.turn_resumption import SuspendedTurnResumption
from glassbox.runtime.turn_tool_executor import TurnToolExecutor, TurnToolExecutorHooks
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
    | ToolArtifactRecorded
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
        model_loop_runner: ModelLoopRunner | None = None,
    ) -> None:
        self._session_repository = session_repository
        self._event_bus = event_bus
        self._context_builder = context_builder
        self._model_adapter_factory = model_adapter_factory
        self._model_executor_factory = model_executor_factory
        self._tool_runtime_factory = tool_runtime_factory
        self._artifact_repository = artifact_repository
        self._model_loop_runner = model_loop_runner or ModelLoopRunner()
        self._replay_recorder = (
            ReplayArtifactRecorder(session_repository, artifact_repository)
            if artifact_repository is not None
            else None
        )
        self._turn_preparation = LiveTurnPreparation(
            session_repository,
            context_builder,
            model_adapter_factory,
            model_executor_factory,
            tool_runtime_factory,
            artifact_repository,
        )
        self._turn_resumption = SuspendedTurnResumption(session_repository)
        self._tool_executor = TurnToolExecutor(cast(TurnToolExecutorHooks, self))

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
            prepared_run = self._turn_preparation.prepare(event.session_id, session)
            assistant_message_id = new_message_id()

            await self._run_model_loop(
                event.session_id,
                turn_id=turn_id,
                turn_context=prepared_run.turn_context,
                prepared_turn=prepared_run.prepared_turn,
                conversation=prepared_run.conversation,
                model_adapter=prepared_run.model_adapter,
                model_executor=prepared_run.model_executor,
                tool_runtime=prepared_run.tool_runtime,
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

        resume_state = self._turn_resumption.prepare_user_answer(
            event.session_id,
            payload,
        )
        turn_id = resume_state.turn_id
        logger.info(
            "turn_resumed_from_user_answer",
            extra=runtime_log_extra(
                runtime_event="turn_resumed_from_user_answer",
                session_id=event.session_id,
                turn_id=turn_id,
                question_id=payload.question_id,
            ),
        )

        self._append_and_publish(
            event.session_id,
            [TurnStatusChanged(turn_id=turn_id, status=TurnStatus.BUILDING_CONTEXT)],
        )

        try:
            prepared_run = self._turn_preparation.prepare(event.session_id, session)
            resume_state.extend_conversation(prepared_run.conversation)

            await self._run_model_loop(
                event.session_id,
                turn_id=turn_id,
                turn_context=prepared_run.turn_context,
                prepared_turn=prepared_run.prepared_turn,
                conversation=prepared_run.conversation,
                model_adapter=prepared_run.model_adapter,
                model_executor=prepared_run.model_executor,
                tool_runtime=prepared_run.tool_runtime,
                assistant_message_id=resume_state.assistant_message_id,
                assistant_started=True,  # AssistantMessageStarted was emitted earlier
                starting_model_call_index=resume_state.starting_model_call_index,
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

        resume_state = self._turn_resumption.prepare_approval_resolution(
            event.session_id,
            payload,
        )
        if not resume_state.is_resumable:
            # Approval was created without turn metadata (e.g. legacy or external).
            # State transition is already persisted; the turn cannot be resumed.
            return

        turn_id = resume_state.turn_id
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

        self._append_and_publish(
            event.session_id,
            [TurnStatusChanged(turn_id=turn_id, status=TurnStatus.BUILDING_CONTEXT)],
        )

        try:
            prepared_run = self._turn_preparation.prepare(event.session_id, session)
            resume_state.extend_conversation(prepared_run.conversation)

            if payload.decision == ApprovalDecision.APPROVED:
                if prepared_run.tool_runtime is None:
                    raise ValueError(
                        "tool runtime is required to execute an approved tool call"
                    )
                execution_result = await self._tool_executor.execute_approved_tool_call(
                    event.session_id,
                    turn_id=turn_id,
                    tool_runtime=prepared_run.tool_runtime,
                    tool_call=resume_state.to_model_tool_call(),
                )
                prepared_run.conversation.append(execution_result.to_model_request())
            else:
                # DENIED — inject a denial message as the tool return.
                prepared_run.conversation.append(resume_state.make_denial_tool_return())

            await self._run_model_loop(
                event.session_id,
                turn_id=turn_id,
                turn_context=prepared_run.turn_context,
                prepared_turn=prepared_run.prepared_turn,
                conversation=prepared_run.conversation,
                model_adapter=prepared_run.model_adapter,
                model_executor=prepared_run.model_executor,
                tool_runtime=prepared_run.tool_runtime,
                assistant_message_id=resume_state.assistant_message_id,
                assistant_started=True,
                starting_model_call_index=resume_state.starting_model_call_index,
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
        state = ModelConversationState.from_prepared_turn(
            prepared_turn,
            conversation=conversation,
            assistant_started=assistant_started,
            starting_model_call_index=starting_model_call_index,
        )

        def on_model_call_start(
            continuation_turn: PreparedModelTurn,
            call_index: int,
            loop_assistant_started: bool,
        ) -> None:
            self._on_model_call_start(
                session_id,
                turn_id=turn_id,
                assistant_message_id=assistant_message_id,
                assistant_started=loop_assistant_started,
                continuation_turn=continuation_turn,
                call_index=call_index,
                turn_context=turn_context,
                model_adapter=model_adapter,
            )

        def on_record_model_call(
            continuation_turn: PreparedModelTurn,
            call_index: int,
        ) -> None:
            self._record_replay_model_call(
                session_id,
                turn_id=turn_id,
                turn_context=turn_context,
                prepared_turn=continuation_turn,
                call_index=call_index,
            )

        def on_stream_event(stream_event) -> None:
            self._handle_stream_event(
                session_id,
                assistant_message_id=assistant_message_id,
                stream_event=stream_event,
            )

        def on_model_call_completed(result, _call_index: int, duration_ms: int) -> None:
            self._on_model_call_completed(
                session_id,
                turn_id=turn_id,
                model_adapter=model_adapter,
                result=result,
                duration_ms=duration_ms,
            )

        async def on_tool_calls(
            tool_calls: tuple[ModelToolCall, ...],
            loop_state: ModelConversationState,
        ) -> ModelLoopSuspension | None:
            return await self._on_model_tool_calls(
                session_id,
                turn_id=turn_id,
                tool_runtime=tool_runtime,
                tool_calls=tool_calls,
                state=loop_state,
            )

        def on_assistant_completed(assistant_text: str) -> None:
            self._complete_assistant_response(
                session_id,
                turn_id=turn_id,
                assistant_message_id=assistant_message_id,
                assistant_text=assistant_text,
            )

        await self._model_loop_runner.run(
            state=state,
            model_adapter=model_adapter,
            model_executor=model_executor,
            on_model_call_start=on_model_call_start,
            on_record_model_call=on_record_model_call,
            on_stream_event=on_stream_event,
            on_model_call_completed=on_model_call_completed,
            on_tool_calls=on_tool_calls,
            on_assistant_completed=on_assistant_completed,
        )

    def _on_model_call_start(
        self,
        session_id,
        *,
        turn_id,
        assistant_message_id: MessageId,
        assistant_started: bool,
        continuation_turn: PreparedModelTurn,
        call_index: int,
        turn_context: TurnContext,
        model_adapter: ModelAdapter,
    ) -> None:
        del continuation_turn, call_index, turn_context
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
        self._append_and_publish(session_id, model_call_events)

    def _on_model_call_completed(
        self,
        session_id,
        *,
        turn_id,
        model_adapter: ModelAdapter,
        result,
        duration_ms: int,
    ) -> None:
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

    async def _on_model_tool_calls(
        self,
        session_id,
        *,
        turn_id,
        tool_runtime: ToolRuntime | None,
        tool_calls: tuple[ModelToolCall, ...],
        state: ModelConversationState,
    ) -> ModelLoopSuspension | None:
        if tool_runtime is None:
            raise ValueError("tool calls are not supported by the turn engine yet")
        return await self._tool_executor.execute_tool_calls(
            session_id,
            turn_id=turn_id,
            tool_runtime=tool_runtime,
            tool_calls=tool_calls,
            conversation=state.conversation,
        )

    def _complete_assistant_response(
        self,
        session_id,
        *,
        turn_id,
        assistant_message_id: MessageId,
        assistant_text: str,
    ) -> None:
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

    def _record_context_artifacts_for_tool_execution(
        self,
        session_id,
        *,
        turn_id,
        prepared_tool_call,
        execution_result,
    ) -> None:
        if self._artifact_repository is None:
            return
        if prepared_tool_call.tool_name != "run_tests":
            return

        pytest_failure_digest = build_pytest_failure_digest_artifact(
            prepared_tool_call.validated_arguments.model_dump(mode="json"),
            execution_result.output_payload,
        )
        if pytest_failure_digest is None:
            return

        _, stored_event = self._artifact_repository.record_text_artifact(
            session_id,
            turn_id,
            execution_result.event_tool_call_id,
            PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
            json.dumps(
                pytest_failure_digest.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            suffix="json",
        )
        self._event_bus.publish(stored_event)

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
