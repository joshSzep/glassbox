"""Event side effects for turn execution."""

from collections.abc import Sequence
from typing import Any
from typing import cast

from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import CancellationAcknowledged
from glassbox.core.events import CancellationFailed
from glassbox.core.events import CancellationRequested
from glassbox.core.events import CancellationStage
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelCallCompleted
from glassbox.core.events import ModelCallStarted
from glassbox.core.events import ProviderRecoveryRecorded
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import SessionFailed
from glassbox.core.events import TurnCancelled
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import TurnStatusChanged
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import MessageId
from glassbox.core.ids import new_recovery_decision_id
from glassbox.core.models import MessagePart
from glassbox.core.types import RecoveryDecision
from glassbox.core.types import TurnStatus
from glassbox.llm import ModelAdapter
from glassbox.llm import ModelTextDelta
from glassbox.llm import ModelToolCall
from glassbox.llm import ModelToolCallDelta
from glassbox.llm import PreparedModelTurn
from glassbox.runtime.context_builder import TurnContext
from glassbox.runtime.errors import SessionRuntimeFailure
from glassbox.runtime.logging import get_runtime_logger
from glassbox.runtime.logging import runtime_log_extra
from glassbox.runtime.replay_capture import ReplayArtifactRecorder
from glassbox.runtime.task_plan_capture import CapturedTaskPlanEvents
from glassbox.runtime.transport import RuntimeEventTransport
from glassbox.runtime.turn_artifacts import record_context_artifacts_for_tool_execution
from glassbox.runtime.turn_artifacts import (
    record_tool_output_artifact_for_tool_execution,
)
from glassbox.runtime.turn_artifacts import tool_output_artifact_content
from glassbox.runtime.turn_artifacts import tool_output_artifact_kind
from glassbox.runtime.turn_replay_hooks import TurnReplayHooks
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository

logger = get_runtime_logger("turn_engine")


class TurnEventRecorder:
    """Own turn-engine event construction, publishing, and artifact side effects."""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_bus: RuntimeEventTransport[EventEnvelope],
        *,
        replay_recorder: ReplayArtifactRecorder | None = None,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._session_repository = session_repository
        self._event_bus = event_bus
        self._replay_hooks = TurnReplayHooks(replay_recorder)
        self._artifact_repository = artifact_repository

    def record_turn_started(
        self,
        session_id,
        *,
        turn_id,
        trigger_message_id,
    ) -> None:
        self._append_and_publish(
            session_id,
            [
                TurnStarted(
                    turn_id=turn_id,
                    trigger_message_id=trigger_message_id,
                ),
                TurnStatusChanged(
                    turn_id=turn_id,
                    status=TurnStatus.BUILDING_CONTEXT,
                ),
            ],
        )

    def record_turn_building_context(self, session_id, *, turn_id) -> None:
        self._append_and_publish(
            session_id,
            [TurnStatusChanged(turn_id=turn_id, status=TurnStatus.BUILDING_CONTEXT)],
        )

    def record_model_call_start(
        self,
        session_id,
        *,
        turn_id,
        assistant_message_id: MessageId,
        assistant_started: bool,
        model_adapter: ModelAdapter,
    ) -> None:
        model_call_events: list[object] = [
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

    def record_model_call_completed(
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

    def record_stream_event(
        self,
        session_id,
        *,
        assistant_message_id: MessageId,
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

    def record_assistant_completed(
        self,
        session_id,
        *,
        turn_id,
        assistant_message_id: MessageId,
        assistant_text: str,
        task_plan_capture: CapturedTaskPlanEvents | None = None,
    ) -> None:
        completion_payloads: list[object] = [
            TurnStatusChanged(
                turn_id=turn_id,
                status=TurnStatus.ASSEMBLING_RESPONSE,
            ),
            AssistantMessageCompleted(
                message_id=assistant_message_id,
                parts=[MessagePart(kind="text", text=assistant_text)],
            ),
        ]
        if task_plan_capture is not None:
            completion_payloads.extend(task_plan_capture.payloads)
        completion_payloads.extend(
            [
                TurnStatusChanged(
                    turn_id=turn_id,
                    status=TurnStatus.COMPLETED,
                ),
                TurnCompleted(turn_id=turn_id, outcome="completed"),
            ]
        )
        self._append_and_publish(
            session_id,
            completion_payloads,
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
            details=(
                task_plan_capture.replay_details()
                if task_plan_capture is not None
                else None
            ),
        )

    def record_failed_turn(
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
        failure_events: list[object] = [
            TurnStatusChanged(
                turn_id=turn_id,
                status=TurnStatus.FAILED,
            ),
            TurnFailed(turn_id=turn_id, error_message=str(error)),
            RecoveryDecisionRecorded(
                recovery_decision_id=new_recovery_decision_id(),
                decision=RecoveryDecision.NON_RESUMABLE,
                reason=(
                    "turn failed during live execution; provider streams and "
                    "tool loops cannot be resumed exactly after interruption"
                ),
                safe_to_resume=False,
                next_action=(
                    "Review the failure, then retry with a new prompt or fork "
                    "from a completed turn"
                ),
                turn_id=turn_id,
                decided_by="runtime",
            ),
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

    def record_provider_recovery(
        self,
        session_id,
        *,
        recovery: ProviderRecoveryRecorded,
    ) -> None:
        self._append_and_publish(session_id, [recovery])

    def record_cancellation_requested(
        self,
        session_id,
        *,
        turn_id,
        requested_by: str,
        reason: str | None,
        repeated: bool,
    ) -> None:
        self._append_and_publish(
            session_id,
            [
                CancellationRequested(
                    turn_id=turn_id,
                    requested_by=requested_by,
                    reason=reason,
                ),
                CancellationAcknowledged(
                    turn_id=turn_id,
                    repeated=repeated,
                ),
                TurnStatusChanged(
                    turn_id=turn_id,
                    status=TurnStatus.CANCELLING,
                ),
            ],
        )

    def record_cancelled_turn(
        self,
        session_id,
        *,
        turn_id,
        reason: str,
        stage: CancellationStage,
    ) -> None:
        logger.info(
            "turn_cancelled",
            extra=runtime_log_extra(
                runtime_event="turn_cancelled",
                session_id=session_id,
                turn_id=turn_id,
                stage=stage,
                reason=reason,
            ),
        )
        self._append_and_publish(
            session_id,
            [
                TurnStatusChanged(
                    turn_id=turn_id,
                    status=TurnStatus.CANCELLED,
                ),
                TurnCancelled(turn_id=turn_id, reason=reason, stage=stage),
                TurnCompleted(turn_id=turn_id, outcome="cancelled"),
            ],
        )
        self._record_replay_turn_output(
            session_id,
            turn_id=turn_id,
            outcome="cancelled",
            details={"reason": reason, "stage": stage},
        )

    def record_cancellation_failed(
        self,
        session_id,
        *,
        turn_id,
        reason: str,
        retryable: bool = False,
    ) -> None:
        self._append_and_publish(
            session_id,
            [
                CancellationFailed(
                    turn_id=turn_id,
                    reason=reason,
                    retryable=retryable,
                )
            ],
        )

    def _append_and_publish(
        self,
        session_id,
        payloads: Sequence[object],
    ) -> list[EventEnvelope]:
        stored_events = self._session_repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=cast(Any, payload),
                )
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
        turn_context: TurnContext,
        prepared_turn: PreparedModelTurn,
        call_index: int,
    ) -> None:
        self._replay_hooks.record_model_call(
            session_id,
            turn_id=turn_id,
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
        self._replay_hooks.record_tool_request(
            session_id,
            turn_id=turn_id,
            prepared_tool_call=prepared_tool_call,
        )

    def _record_replay_tool_execution_result(
        self,
        session_id,
        *,
        turn_id,
        execution_result,
    ) -> None:
        self._replay_hooks.record_tool_execution_result(
            session_id,
            turn_id=turn_id,
            execution_result=execution_result,
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
        self._replay_hooks.record_tool_result(
            session_id,
            turn_id=turn_id,
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
        record_context_artifacts_for_tool_execution(
            self._artifact_repository,
            self._event_bus,
            session_id,
            turn_id=turn_id,
            prepared_tool_call=prepared_tool_call,
            execution_result=execution_result,
        )

    def _record_tool_output_artifact_for_tool_execution(
        self,
        session_id,
        *,
        turn_id,
        prepared_tool_call,
        execution_result,
    ) -> ArtifactId | None:
        return record_tool_output_artifact_for_tool_execution(
            self._artifact_repository,
            self._event_bus,
            session_id,
            turn_id=turn_id,
            prepared_tool_call=prepared_tool_call,
            execution_result=execution_result,
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
        self._replay_hooks.record_turn_output(
            session_id,
            turn_id=turn_id,
            outcome=outcome,
            assistant_text=assistant_text,
            details=details,
        )


def _tool_output_artifact_content(
    tool_name: str,
    output_payload: dict[str, object],
) -> dict[str, object] | None:
    """Compatibility wrapper for older focused tests and internal imports."""

    return tool_output_artifact_content(tool_name, output_payload)


def _tool_output_artifact_kind(artifact_content: dict[str, object]) -> str:
    """Compatibility wrapper for older focused tests and internal imports."""

    return tool_output_artifact_kind(artifact_content)
