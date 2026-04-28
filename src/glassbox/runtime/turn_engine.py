"""Turn engine for assistant responses with optional tool execution."""

from collections.abc import Awaitable
from collections.abc import Callable

from pydantic_ai.messages import ModelMessage

from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserMessageReceived
from glassbox.core.ids import MessageId
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_turn_id
from glassbox.core.models import SessionRecord
from glassbox.core.types import ApprovalDecision
from glassbox.llm import ModelAdapter
from glassbox.llm import ModelExecutor
from glassbox.llm import ModelToolCall
from glassbox.llm import PreparedModelTurn
from glassbox.runtime.cancellation import TurnCancellationController
from glassbox.runtime.cancellation import TurnCancellationRequested
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.logging import get_runtime_logger
from glassbox.runtime.logging import runtime_log_extra
from glassbox.runtime.model_loop import ModelConversationState
from glassbox.runtime.model_loop import ModelLoopRunner
from glassbox.runtime.model_loop import ModelLoopSuspension
from glassbox.runtime.replay_capture import ReplayArtifactRecorder
from glassbox.runtime.transport import RuntimeEventTransport
from glassbox.runtime.turn_event_recorder import TurnEventRecorder
from glassbox.runtime.turn_preparation import LiveTurnPreparation
from glassbox.runtime.turn_preparation import PreparedTurnRun
from glassbox.runtime.turn_resumption import SuspendedTurnResumption
from glassbox.runtime.turn_tool_executor import TurnToolExecutor
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.tools import ToolRuntime

ModelAdapterFactory = Callable[[SessionRecord], ModelAdapter]
ModelExecutorFactory = Callable[[SessionRecord], ModelExecutor]
ToolRuntimeFactory = Callable[[SessionRecord], ToolRuntime]
PreparedTurnHook = Callable[[PreparedTurnRun], Awaitable[None]]

logger = get_runtime_logger("turn_engine")


class TurnEngine:
    """Run one model turn from a persisted user message event."""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_bus: RuntimeEventTransport[EventEnvelope],
        context_builder: TurnContextBuilder,
        model_adapter_factory: ModelAdapterFactory,
        model_executor_factory: ModelExecutorFactory,
        tool_runtime_factory: ToolRuntimeFactory | None = None,
        artifact_repository: ArtifactRepository | None = None,
        model_loop_runner: ModelLoopRunner | None = None,
    ) -> None:
        replay_recorder = (
            ReplayArtifactRecorder(session_repository, artifact_repository)
            if artifact_repository is not None
            else None
        )
        self._session_repository = session_repository
        self._model_adapter_factory = model_adapter_factory
        self._model_executor_factory = model_executor_factory
        self._tool_runtime_factory = tool_runtime_factory
        self._artifact_repository = artifact_repository
        self._model_loop_runner = model_loop_runner or ModelLoopRunner()
        self._event_recorder = TurnEventRecorder(
            session_repository,
            event_bus,
            replay_recorder=replay_recorder,
            artifact_repository=artifact_repository,
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
        self._tool_executor = TurnToolExecutor(self._event_recorder)
        self._active_cancellations: dict[object, TurnCancellationController] = {}

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
        self._event_recorder.record_turn_started(
            event.session_id,
            turn_id=turn_id,
            trigger_message_id=payload.message_id,
        )

        await self._run_prepared_turn(
            event.session_id,
            session=session,
            turn_id=turn_id,
            assistant_message_id=new_message_id(),
            assistant_started=False,
            starting_model_call_index=0,
            trigger="user_message",
        )

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
        self._event_recorder.record_turn_building_context(
            event.session_id,
            turn_id=turn_id,
        )

        async def continue_with_user_answer(prepared_run: PreparedTurnRun) -> None:
            resume_state.extend_conversation(prepared_run.conversation)

        await self._run_prepared_turn(
            event.session_id,
            session=session,
            turn_id=turn_id,
            assistant_message_id=resume_state.assistant_message_id,
            assistant_started=True,
            starting_model_call_index=resume_state.starting_model_call_index,
            trigger="user_answer",
            question_id=payload.question_id,
            before_model_loop=continue_with_user_answer,
        )

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
        self._event_recorder.record_turn_building_context(
            event.session_id,
            turn_id=turn_id,
        )

        async def continue_with_approval_resolution(
            prepared_run: PreparedTurnRun,
        ) -> None:
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
                    cancellation_controller=None,
                )
                prepared_run.conversation.append(execution_result.to_model_request())
                return

            prepared_run.conversation.append(resume_state.make_denial_tool_return())

        await self._run_prepared_turn(
            event.session_id,
            session=session,
            turn_id=turn_id,
            assistant_message_id=resume_state.assistant_message_id,
            assistant_started=True,
            starting_model_call_index=resume_state.starting_model_call_index,
            trigger="approval_resolution",
            approval_id=payload.approval_id,
            before_model_loop=continue_with_approval_resolution,
        )

    async def _run_prepared_turn(
        self,
        session_id,
        *,
        session: SessionRecord,
        turn_id,
        assistant_message_id: MessageId,
        assistant_started: bool,
        starting_model_call_index: int,
        trigger: str,
        approval_id=None,
        question_id=None,
        before_model_loop: PreparedTurnHook | None = None,
    ) -> None:
        try:
            cancellation_controller = TurnCancellationController(turn_id)
            self._active_cancellations[session_id] = cancellation_controller
            prepared_run = self._turn_preparation.prepare(session_id, session)
            cancellation_controller.raise_if_requested("preparation")
            if before_model_loop is not None:
                await before_model_loop(prepared_run)
                cancellation_controller.raise_if_requested("resumption")

            await self._run_model_loop(
                session_id,
                turn_id=turn_id,
                turn_context=prepared_run.turn_context,
                prepared_turn=prepared_run.prepared_turn,
                conversation=prepared_run.conversation,
                model_adapter=prepared_run.model_adapter,
                model_executor=prepared_run.model_executor,
                tool_runtime=prepared_run.tool_runtime,
                assistant_message_id=assistant_message_id,
                assistant_started=assistant_started,
                starting_model_call_index=starting_model_call_index,
                cancellation_controller=cancellation_controller,
            )
        except TurnCancellationRequested as exc:
            self._event_recorder.record_cancelled_turn(
                session_id,
                turn_id=turn_id,
                reason=exc.reason,
                stage=exc.stage,
            )
        except Exception as exc:
            self._event_recorder.record_failed_turn(
                session_id,
                turn_id=turn_id,
                error=exc,
                trigger=trigger,
                approval_id=approval_id,
                question_id=question_id,
            )
            raise
        finally:
            active_controller = self._active_cancellations.get(session_id)
            if active_controller is not None and active_controller.turn_id == turn_id:
                self._active_cancellations.pop(session_id, None)

    def request_turn_cancellation(
        self,
        session_id,
        *,
        turn_id=None,
        requested_by: str = "operator",
        reason: str | None = None,
    ) -> bool:
        controller = self._active_cancellations.get(session_id)
        if controller is None:
            return False
        if turn_id is not None and controller.turn_id != turn_id:
            return False

        repeated = controller.request(reason)
        self._event_recorder.record_cancellation_requested(
            session_id,
            turn_id=controller.turn_id,
            requested_by=requested_by,
            reason=reason,
            repeated=repeated,
        )
        return True

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
        cancellation_controller: TurnCancellationController | None,
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
            del continuation_turn, call_index
            self._event_recorder.record_model_call_start(
                session_id,
                turn_id=turn_id,
                assistant_message_id=assistant_message_id,
                assistant_started=loop_assistant_started,
                model_adapter=model_adapter,
            )

        def on_record_model_call(
            continuation_turn: PreparedModelTurn,
            call_index: int,
        ) -> None:
            self._event_recorder._record_replay_model_call(
                session_id,
                turn_id=turn_id,
                turn_context=turn_context,
                prepared_turn=continuation_turn,
                call_index=call_index,
            )

        def on_stream_event(stream_event) -> None:
            self._event_recorder.record_stream_event(
                session_id,
                assistant_message_id=assistant_message_id,
                stream_event=stream_event,
            )

        def on_model_call_completed(result, _call_index: int, duration_ms: int) -> None:
            self._event_recorder.record_model_call_completed(
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
                cancellation_controller=cancellation_controller,
            )

        def on_assistant_completed(assistant_text: str) -> None:
            self._event_recorder.record_assistant_completed(
                session_id,
                turn_id=turn_id,
                assistant_message_id=assistant_message_id,
                assistant_text=assistant_text,
            )

        await self._model_loop_runner.run(
            state=state,
            model_adapter=model_adapter,
            model_executor=model_executor,
            cancellation_controller=cancellation_controller,
            on_model_call_start=on_model_call_start,
            on_record_model_call=on_record_model_call,
            on_stream_event=on_stream_event,
            on_model_call_completed=on_model_call_completed,
            on_tool_calls=on_tool_calls,
            on_assistant_completed=on_assistant_completed,
        )

    async def _on_model_tool_calls(
        self,
        session_id,
        *,
        turn_id,
        tool_runtime: ToolRuntime | None,
        tool_calls: tuple[ModelToolCall, ...],
        state: ModelConversationState,
        cancellation_controller: TurnCancellationController | None = None,
    ) -> ModelLoopSuspension | None:
        if tool_runtime is None:
            raise ValueError("tool calls are not supported by the turn engine yet")
        return await self._tool_executor.execute_tool_calls(
            session_id,
            turn_id=turn_id,
            tool_runtime=tool_runtime,
            tool_calls=tool_calls,
            conversation=state.conversation,
            cancellation_controller=cancellation_controller,
        )
