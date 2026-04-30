"""Tool execution helpers for the turn engine model loop."""

import json
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Protocol
from typing import cast

from pydantic_ai.messages import ModelMessage

from glassbox.core.events import ApprovalRequested
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.events import ToolExecutionCancelled
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import ToolOutputChunk
from glassbox.core.events import ToolOutputStream
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnStatusChanged
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_tool_attempt_id
from glassbox.core.models import PolicyDecisionTrace
from glassbox.core.types import ToolAttemptStatus
from glassbox.core.types import TurnStatus
from glassbox.llm import ModelToolCall
from glassbox.runtime.cancellation import TurnCancellationController
from glassbox.runtime.cancellation import TurnCancellationRequested
from glassbox.runtime.logging import get_runtime_logger
from glassbox.runtime.logging import runtime_log_extra
from glassbox.runtime.model_loop import ModelLoopSuspension
from glassbox.tools import PreparedToolExecution
from glassbox.tools import ToolExecutionResult
from glassbox.tools import ToolRuntime

logger = get_runtime_logger("turn_tools")


class TurnToolExecutorHooks(Protocol):
    """Minimal turn-engine hook surface needed by the tool executor."""

    def _append_and_publish(
        self,
        session_id,
        payloads: Sequence[object],
    ) -> list[EventEnvelope]: ...

    def _record_replay_tool_request(
        self,
        session_id,
        *,
        turn_id,
        prepared_tool_call,
    ) -> None: ...

    def _record_replay_tool_execution_result(
        self,
        session_id,
        *,
        turn_id,
        execution_result,
    ) -> None: ...

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
    ) -> None: ...

    def _record_replay_turn_output(
        self,
        session_id,
        *,
        turn_id,
        outcome,
        assistant_text: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None: ...

    def _record_context_artifacts_for_tool_execution(
        self,
        session_id,
        *,
        turn_id,
        prepared_tool_call,
        execution_result,
    ) -> None: ...

    def _record_tool_output_artifact_for_tool_execution(
        self,
        session_id,
        *,
        turn_id,
        prepared_tool_call,
        execution_result,
    ) -> ArtifactId | None: ...


class TurnToolExecutor:
    """Execute model-requested tools while preserving turn-engine side effects."""

    def __init__(self, hooks: TurnToolExecutorHooks) -> None:
        self._hooks = hooks

    async def execute_tool_calls(
        self,
        session_id,
        *,
        turn_id,
        tool_runtime: ToolRuntime,
        tool_calls: tuple[ModelToolCall, ...],
        conversation: list[ModelMessage],
        cancellation_controller: TurnCancellationController | None = None,
    ) -> ModelLoopSuspension | None:
        for tool_call in tool_calls:
            prepared_tool_call = tool_runtime.prepare_tool_call(tool_call)
            policy_trace = PolicyDecisionTrace.from_decision(
                prepared_tool_call.policy_decision
            )
            self._hooks._append_and_publish(
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
                        policy_outcome=prepared_tool_call.policy_decision.outcome,
                        policy_risk_level=prepared_tool_call.policy_decision.risk_level,
                        policy_source_kind=(
                            prepared_tool_call.policy_decision.source_kind
                        ),
                        policy_source_label=(
                            prepared_tool_call.policy_decision.source_label
                        ),
                        policy_reason=prepared_tool_call.policy_decision.reason,
                        policy_trace=policy_trace,
                    )
                ],
            )
            self._hooks._record_replay_tool_request(
                session_id,
                turn_id=turn_id,
                prepared_tool_call=prepared_tool_call,
            )

            suspension = self._maybe_suspend_before_execution(
                session_id,
                turn_id=turn_id,
                prepared_tool_call=prepared_tool_call,
            )
            if suspension is not None:
                return suspension

            execution_result = await self._execute_prepared_tool_call(
                session_id,
                turn_id=turn_id,
                tool_runtime=tool_runtime,
                prepared_tool_call=prepared_tool_call,
                approved=False,
                cancellation_controller=cancellation_controller,
            )
            conversation.append(execution_result.to_model_request())

        return None

    async def execute_approved_tool_call(
        self,
        session_id,
        *,
        turn_id,
        tool_runtime: ToolRuntime,
        tool_call: ModelToolCall,
        cancellation_controller: TurnCancellationController | None = None,
    ) -> ToolExecutionResult:
        prepared_tool_call = tool_runtime.prepare_tool_call(tool_call)
        return await self._execute_prepared_tool_call(
            session_id,
            turn_id=turn_id,
            tool_runtime=tool_runtime,
            prepared_tool_call=prepared_tool_call,
            approved=True,
            cancellation_controller=cancellation_controller,
        )

    def _maybe_suspend_before_execution(
        self,
        session_id,
        *,
        turn_id,
        prepared_tool_call: PreparedToolExecution,
    ) -> ModelLoopSuspension | None:
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
            policy_trace = PolicyDecisionTrace.from_decision(
                prepared_tool_call.policy_decision
            )
            self._hooks._append_and_publish(
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
                        policy_outcome=prepared_tool_call.policy_decision.outcome,
                        policy_risk_level=prepared_tool_call.policy_decision.risk_level,
                        policy_source_kind=(
                            prepared_tool_call.policy_decision.source_kind
                        ),
                        policy_source_label=(
                            prepared_tool_call.policy_decision.source_label
                        ),
                        policy_trace=policy_trace,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                        provider_tool_call_id=prepared_tool_call.provider_tool_call_id,
                    ),
                    TurnCompleted(turn_id=turn_id, outcome="awaiting_approval"),
                ],
            )
            self._hooks._record_replay_turn_output(
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
            self._hooks._append_and_publish(
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
            self._hooks._record_replay_tool_result(
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

        if prepared_tool_call.tool_name == "ask_user":
            question_id = new_question_id()
            question_text = str(
                prepared_tool_call.validated_arguments.model_dump().get("question", "")
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
            self._hooks._append_and_publish(
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
            self._hooks._record_replay_turn_output(
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

        return None

    async def _execute_prepared_tool_call(
        self,
        session_id,
        *,
        turn_id,
        tool_runtime: ToolRuntime,
        prepared_tool_call: PreparedToolExecution,
        approved: bool,
        cancellation_controller: TurnCancellationController | None = None,
    ) -> ToolExecutionResult:
        policy_trace = PolicyDecisionTrace.from_decision(
            prepared_tool_call.policy_decision
        )
        tool_attempt_id = new_tool_attempt_id()
        self._hooks._append_and_publish(
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
                    policy_outcome=prepared_tool_call.policy_decision.outcome,
                    policy_risk_level=prepared_tool_call.policy_decision.risk_level,
                    policy_source_kind=prepared_tool_call.policy_decision.source_kind,
                    policy_source_label=prepared_tool_call.policy_decision.source_label,
                    policy_reason=prepared_tool_call.policy_decision.reason,
                    policy_trace=policy_trace,
                ),
                ToolAttemptHeartbeat(
                    tool_attempt_id=tool_attempt_id,
                    status=ToolAttemptStatus.STARTED,
                    turn_id=turn_id,
                    tool_call_id=prepared_tool_call.event_tool_call_id,
                    tool_name=prepared_tool_call.tool_name,
                    message="Tool attempt started.",
                ),
                ToolAttemptHeartbeat(
                    tool_attempt_id=tool_attempt_id,
                    status=ToolAttemptStatus.RUNNING,
                    turn_id=turn_id,
                    tool_call_id=prepared_tool_call.event_tool_call_id,
                    tool_name=prepared_tool_call.tool_name,
                    message="Tool execution is running.",
                    heartbeat_expires_at=_tool_attempt_heartbeat_expiry(
                        prepared_tool_call
                    ),
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
            self._hooks._append_and_publish(
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
            if approved:
                execution_result = await tool_runtime.execute_approved(
                    prepared_tool_call,
                    on_output_chunk=_on_output_chunk,
                    cancellation_controller=cancellation_controller,
                )
            else:
                execution_result = await tool_runtime.execute(
                    prepared_tool_call,
                    on_output_chunk=_on_output_chunk,
                    cancellation_controller=cancellation_controller,
                )
        except Exception as exc:
            self._hooks._append_and_publish(
                session_id,
                [
                    ToolAttemptHeartbeat(
                        tool_attempt_id=tool_attempt_id,
                        status=ToolAttemptStatus.FAILED,
                        turn_id=turn_id,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                        tool_name=prepared_tool_call.tool_name,
                        message=str(exc),
                    ),
                    ToolExecutionCompleted(
                        turn_id=turn_id,
                        tool_call_id=prepared_tool_call.event_tool_call_id,
                        success=False,
                        summary=str(exc),
                    ),
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
            self._hooks._record_replay_tool_result(
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

        cancellation_summary = _tool_cancellation_summary(execution_result)
        if cancellation_summary is not None:
            self._hooks._append_and_publish(
                session_id,
                [
                    ToolExecutionCancelled(
                        turn_id=turn_id,
                        tool_call_id=execution_result.event_tool_call_id,
                        summary=cancellation_summary,
                        exit_code=execution_result.exit_code,
                    )
                ],
            )

        output_artifact_id = (
            self._hooks._record_tool_output_artifact_for_tool_execution(
                session_id,
                turn_id=turn_id,
                prepared_tool_call=prepared_tool_call,
                execution_result=execution_result,
            )
        )
        self._hooks._append_and_publish(
            session_id,
            [
                ToolAttemptHeartbeat(
                    tool_attempt_id=tool_attempt_id,
                    status=(
                        ToolAttemptStatus.CANCELLED
                        if cancellation_summary is not None
                        else (
                            ToolAttemptStatus.SUCCEEDED
                            if execution_result.success
                            else ToolAttemptStatus.FAILED
                        )
                    ),
                    turn_id=turn_id,
                    tool_call_id=execution_result.event_tool_call_id,
                    tool_name=prepared_tool_call.tool_name,
                    message=cancellation_summary or execution_result.summary,
                    output_artifact_id=output_artifact_id,
                    safe_to_retry=(
                        False
                        if execution_result.success or cancellation_summary is not None
                        else None
                    ),
                ),
                ToolExecutionCompleted(
                    turn_id=turn_id,
                    tool_call_id=execution_result.event_tool_call_id,
                    success=execution_result.success,
                    exit_code=execution_result.exit_code,
                    summary=execution_result.summary,
                ),
            ],
        )
        self._hooks._record_context_artifacts_for_tool_execution(
            session_id,
            turn_id=turn_id,
            prepared_tool_call=prepared_tool_call,
            execution_result=execution_result,
        )
        self._hooks._record_replay_tool_execution_result(
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
                success=execution_result.success,
            ),
        )
        if cancellation_summary is not None:
            raise TurnCancellationRequested(
                stage="tool_execution",
                reason=cancellation_summary,
            )
        return execution_result


def _tool_cancellation_summary(execution_result: ToolExecutionResult) -> str | None:
    failure_category = execution_result.output_payload.get("failure_category")
    if failure_category == "cancelled":
        return execution_result.summary
    return None


def _tool_attempt_heartbeat_expiry(
    prepared_tool_call: PreparedToolExecution,
) -> datetime | None:
    arguments = prepared_tool_call.validated_arguments.model_dump()
    timeout = arguments.get("timeout")
    if not isinstance(timeout, int):
        return None
    return datetime.now(tz=UTC) + timedelta(seconds=timeout + 5)
