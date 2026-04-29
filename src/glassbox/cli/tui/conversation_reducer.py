"""Pure event reducer for terminal conversation state."""

from dataclasses import replace

from glassbox.cli.tui.conversation_models import AssistantMessageStatus
from glassbox.cli.tui.conversation_models import ConversationMessage
from glassbox.cli.tui.conversation_models import ConversationMessageKind
from glassbox.cli.tui.conversation_models import ConversationTurn
from glassbox.cli.tui.conversation_models import FailureState
from glassbox.cli.tui.conversation_models import PendingApprovalState
from glassbox.cli.tui.conversation_models import PendingQuestionState
from glassbox.cli.tui.conversation_models import TerminalConversationState
from glassbox.cli.tui.conversation_models import TerminalMode
from glassbox.cli.tui.conversation_models import TerminalStreamStatus
from glassbox.cli.tui.conversation_models import ToolActivity
from glassbox.cli.tui.conversation_models import ToolActivityStatus
from glassbox.cli.tui.conversation_selectors import mode_from_turn_status
from glassbox.cli.tui.conversation_selectors import text_from_parts
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import ErrorRecorded
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelCallCompleted
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionResumed
from glassbox.core.events import SessionStarted
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import ToolOutputChunk
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import TurnStatusChanged
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import MessageId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.types import SessionStatus
from glassbox.core.types import TurnStatus


def reduce_events(
    state: TerminalConversationState,
    events: list[EventEnvelope] | tuple[EventEnvelope, ...],
) -> TerminalConversationState:
    for event in sorted(events, key=lambda item: item.sequence):
        state = apply_event(state, event)
    return state


def apply_event(
    state: TerminalConversationState,
    event: EventEnvelope,
) -> TerminalConversationState:
    payload = event.payload
    state = _with_last_sequence(state, event.sequence)

    if isinstance(payload, SessionStarted):
        return _with_header(
            state,
            status=SessionStatus.RUNNING,
            mode=TerminalMode.READY,
            model_name=payload.model_name,
            cwd=payload.cwd,
            approval_mode=payload.approval_mode,
            branch_label=payload.branch_label,
            dashboard_url=payload.dashboard_url,
        )

    if isinstance(payload, SessionResumed):
        return _append_message(
            state,
            ConversationMessage(
                kind=ConversationMessageKind.RUNTIME,
                text=f"Resumed from sequence {payload.from_sequence}",
                sequence=event.sequence,
            ),
        )

    if isinstance(payload, SessionCompleted):
        return _with_header(
            _mark_streaming_assistant_messages(
                state,
                (
                    AssistantMessageStatus.INTERRUPTED
                    if payload.reason in {"cancelled", "interrupted"}
                    else AssistantMessageStatus.COMPLETED
                ),
                event.sequence,
            ),
            status=SessionStatus.COMPLETED,
            mode=TerminalMode.HISTORICAL_ONLY,
            stream_status=TerminalStreamStatus.HISTORICAL_ONLY,
            current_turn_id=None,
        )

    if isinstance(payload, SessionFailed):
        return _with_failure(
            _with_header(
                _mark_streaming_assistant_messages(
                    state,
                    AssistantMessageStatus.FAILED,
                    event.sequence,
                ),
                status=SessionStatus.FAILED,
                mode=TerminalMode.FAILED,
                stream_status=TerminalStreamStatus.HISTORICAL_ONLY,
                current_turn_id=None,
            ),
            FailureState(
                message=payload.error_message,
                sequence=event.sequence,
                retryable=payload.retryable,
            ),
        )

    if isinstance(payload, UserMessageReceived):
        return _append_message(
            state,
            ConversationMessage(
                kind=ConversationMessageKind.USER,
                text=payload.text,
                sequence=event.sequence,
                message_id=payload.message_id,
            ),
        )

    if isinstance(payload, TranscriptMessageImported):
        imported_messages = tuple(
            ConversationMessage(
                kind=ConversationMessageKind(payload.role),
                text=text_from_parts(payload.parts),
                sequence=event.sequence,
                message_id=payload.message_id,
                turn_id=payload.source_turn_id,
                imported=True,
            )
            for _ in [payload]
        )
        for message in imported_messages:
            state = _append_message(state, message)
        return state

    if isinstance(payload, TurnStarted):
        turn = ConversationTurn(
            turn_id=payload.turn_id,
            trigger_message_id=payload.trigger_message_id,
            status=TurnStatus.PENDING,
            sequence=event.sequence,
        )
        state = _upsert_turn(state, turn)
        state = _attach_trigger_message_to_turn(
            state,
            payload.turn_id,
            payload.trigger_message_id,
            event.sequence,
        )
        return _with_header(
            state,
            status=SessionStatus.RUNNING,
            mode=TerminalMode.THINKING,
            current_turn_id=payload.turn_id,
        )

    if isinstance(payload, TurnStatusChanged):
        mode = mode_from_turn_status(payload.status)
        return _with_header(
            _update_turn(
                state,
                payload.turn_id,
                status=payload.status,
                sequence=event.sequence,
            ),
            mode=mode,
            current_turn_id=payload.turn_id,
        )

    if isinstance(payload, AssistantMessageStarted):
        message = ConversationMessage(
            kind=ConversationMessageKind.ASSISTANT,
            text="",
            sequence=event.sequence,
            message_id=payload.message_id,
            turn_id=state.header.current_turn_id,
            status=AssistantMessageStatus.STREAMING,
        )
        return _append_message(state, message)

    if isinstance(payload, AssistantMessageDelta):
        return _append_assistant_delta(
            state,
            payload.message_id,
            payload.delta,
            event.sequence,
        )

    if isinstance(payload, AssistantMessageCompleted):
        return _complete_assistant_message(
            state,
            payload.message_id,
            text_from_parts(payload.parts),
            event.sequence,
        )

    if isinstance(payload, ModelToolCallRequested):
        activity = ToolActivity(
            tool_call_id=payload.tool_call_id,
            turn_id=payload.turn_id,
            tool_name=payload.tool_name,
            status=ToolActivityStatus.REQUESTED,
            sequence=event.sequence,
            arguments_json=payload.arguments_json,
            policy_outcome=payload.policy_outcome,
            policy_risk_level=payload.policy_risk_level,
            policy_source_kind=payload.policy_source_kind,
            policy_source_label=payload.policy_source_label,
            policy_reason=payload.policy_reason,
        )
        return _with_header(
            _upsert_tool(state, activity),
            mode=TerminalMode.RUNNING_TOOL,
            current_turn_id=payload.turn_id,
        )

    if isinstance(payload, ToolExecutionStarted):
        activity = ToolActivity(
            tool_call_id=payload.tool_call_id,
            turn_id=payload.turn_id,
            tool_name=payload.tool_name,
            status=ToolActivityStatus.RUNNING,
            sequence=event.sequence,
            policy_outcome=payload.policy_outcome,
            policy_risk_level=payload.policy_risk_level,
            policy_source_kind=payload.policy_source_kind,
            policy_source_label=payload.policy_source_label,
            policy_reason=payload.policy_reason,
        )
        return _with_header(
            _upsert_tool(state, activity),
            mode=TerminalMode.RUNNING_TOOL,
            current_turn_id=payload.turn_id,
        )

    if isinstance(payload, ToolOutputChunk):
        return _append_tool_output(
            state,
            payload.tool_call_id,
            payload.chunk,
            event.sequence,
        )

    if isinstance(payload, ToolArtifactRecorded):
        return _append_tool_artifact(
            state,
            payload.tool_call_id,
            payload.path,
            event.sequence,
        )

    if isinstance(payload, ToolExecutionCompleted):
        return _complete_tool(
            state,
            payload.tool_call_id,
            success=payload.success,
            summary=payload.summary,
            exit_code=payload.exit_code,
            sequence=event.sequence,
        )

    if isinstance(payload, ModelCallCompleted):
        return _update_turn(
            state,
            payload.turn_id,
            sequence=event.sequence,
            model_duration_ms=payload.duration_ms,
            model_input_tokens=payload.input_tokens,
            model_output_tokens=payload.output_tokens,
        )

    if isinstance(payload, ApprovalRequested):
        approval = PendingApprovalState(
            approval_id=payload.approval_id,
            turn_id=payload.turn_id,
            subject=payload.subject,
            reason=payload.reason,
            sequence=event.sequence,
            tool_call_id=payload.tool_call_id,
            policy_outcome=payload.policy_outcome,
            policy_risk_level=payload.policy_risk_level,
            policy_source_kind=payload.policy_source_kind,
            policy_source_label=payload.policy_source_label,
        )
        return _with_header(
            _replace(state, pending_approval=approval),
            status=SessionStatus.AWAITING_APPROVAL,
            mode=TerminalMode.AWAITING_APPROVAL,
            current_turn_id=payload.turn_id,
        )

    if isinstance(payload, ApprovalResolved):
        if state.pending_approval is None:
            return state
        approval = _replace(
            state.pending_approval,
            decision=payload.decision,
            sequence=event.sequence,
        )
        return _with_header(
            _replace(state, pending_approval=approval),
            status=SessionStatus.RUNNING,
            mode=TerminalMode.THINKING,
        )

    if isinstance(payload, UserQuestionAsked):
        question = PendingQuestionState(
            question_id=payload.question_id,
            turn_id=payload.turn_id,
            tool_call_id=payload.tool_call_id,
            question=payload.question,
            sequence=event.sequence,
        )
        return _with_header(
            _replace(state, pending_question=question),
            status=SessionStatus.AWAITING_USER_INPUT,
            mode=TerminalMode.AWAITING_ANSWER,
            current_turn_id=payload.turn_id,
        )

    if isinstance(payload, UserAnswerProvided):
        if state.pending_question is None:
            return state
        question = _replace(
            state.pending_question,
            answer=payload.answer,
            sequence=event.sequence,
        )
        return _with_header(
            _replace(state, pending_question=question),
            status=SessionStatus.RUNNING,
            mode=TerminalMode.THINKING,
        )

    if isinstance(payload, TurnFailed):
        return _with_failure(
            _with_header(
                _mark_streaming_assistant_messages(
                    _update_turn(
                        state,
                        payload.turn_id,
                        status="failed",
                        sequence=event.sequence,
                        failure_message=payload.error_message,
                    ),
                    AssistantMessageStatus.FAILED,
                    event.sequence,
                    turn_id=payload.turn_id,
                ),
                status=SessionStatus.FAILED,
                mode=TerminalMode.FAILED,
                current_turn_id=payload.turn_id,
            ),
            FailureState(
                message=payload.error_message,
                sequence=event.sequence,
                turn_id=payload.turn_id,
            ),
        )

    if isinstance(payload, TurnCompleted):
        state = _update_turn(
            state,
            payload.turn_id,
            status="completed",
            sequence=event.sequence,
            completed_outcome=payload.outcome,
        )
        if payload.outcome == "failed":
            state = _mark_streaming_assistant_messages(
                state,
                AssistantMessageStatus.FAILED,
                event.sequence,
                turn_id=payload.turn_id,
            )
        return _with_header(
            state,
            status=SessionStatus.RUNNING,
            mode=TerminalMode.READY,
            current_turn_id=None,
        )

    if isinstance(payload, ErrorRecorded):
        return _with_failure(
            state,
            FailureState(message=payload.message, sequence=event.sequence),
        )

    return state


def _with_last_sequence(
    state: TerminalConversationState,
    sequence: int,
) -> TerminalConversationState:
    if sequence <= state.header.last_sequence:
        return state
    return _with_header(state, last_sequence=sequence)


def _with_header(
    state: TerminalConversationState, **changes
) -> TerminalConversationState:
    return _replace(state, header=_replace(state.header, **changes))


def _with_failure(
    state: TerminalConversationState,
    failure: FailureState,
) -> TerminalConversationState:
    return _replace(state, failure=failure)


def _append_message(
    state: TerminalConversationState,
    message: ConversationMessage,
) -> TerminalConversationState:
    state = _replace(state, messages=(*state.messages, message))
    if message.turn_id is None:
        return state
    return _append_turn_message(state, message.turn_id, message)


def _append_assistant_delta(
    state: TerminalConversationState,
    message_id: MessageId,
    delta: str,
    sequence: int,
) -> TerminalConversationState:
    messages = []
    updated_message: ConversationMessage | None = None
    for message in state.messages:
        if message.message_id == message_id:
            if message.status == AssistantMessageStatus.STREAMING:
                updated_message = _replace(
                    message,
                    text=f"{message.text}{delta}",
                    sequence=sequence,
                )
                messages.append(updated_message)
            else:
                messages.append(message)
        else:
            messages.append(message)
    state = _replace(state, messages=tuple(messages))
    if updated_message is None or updated_message.turn_id is None:
        return state
    return _replace_turn_message(state, updated_message)


def _complete_assistant_message(
    state: TerminalConversationState,
    message_id: MessageId,
    text: str,
    sequence: int,
) -> TerminalConversationState:
    messages = []
    updated_message: ConversationMessage | None = None
    for message in state.messages:
        if message.message_id == message_id:
            if message.status in {
                AssistantMessageStatus.COMPLETED,
                AssistantMessageStatus.FAILED,
                AssistantMessageStatus.INTERRUPTED,
            }:
                updated_message = message
            else:
                updated_message = _replace(
                    message,
                    text=text or message.text,
                    sequence=sequence,
                    status=AssistantMessageStatus.COMPLETED,
                )
            messages.append(updated_message)
        else:
            messages.append(message)
    if updated_message is None:
        updated_message = ConversationMessage(
            kind=ConversationMessageKind.ASSISTANT,
            text=text,
            sequence=sequence,
            message_id=message_id,
            turn_id=state.header.current_turn_id,
            status=AssistantMessageStatus.COMPLETED,
        )
        messages.append(updated_message)
    state = _replace(state, messages=tuple(messages))
    if updated_message.turn_id is None:
        return state
    if any(turn.turn_id == updated_message.turn_id for turn in state.turns):
        return _replace_turn_message(state, updated_message)
    return _append_turn_message(state, updated_message.turn_id, updated_message)


def _mark_streaming_assistant_messages(
    state: TerminalConversationState,
    status: AssistantMessageStatus,
    sequence: int,
    *,
    turn_id: TurnId | None = None,
) -> TerminalConversationState:
    messages: list[ConversationMessage] = []
    updated_messages: list[ConversationMessage] = []
    for message in state.messages:
        should_update = (
            message.kind == ConversationMessageKind.ASSISTANT
            and message.status == AssistantMessageStatus.STREAMING
            and (turn_id is None or message.turn_id == turn_id)
        )
        if should_update:
            updated_message = _replace(message, status=status, sequence=sequence)
            messages.append(updated_message)
            updated_messages.append(updated_message)
        else:
            messages.append(message)
    state = _replace(state, messages=tuple(messages))
    for message in updated_messages:
        if message.turn_id is not None:
            state = _replace_turn_message(state, message)
    return state


def _upsert_turn(
    state: TerminalConversationState,
    turn: ConversationTurn,
) -> TerminalConversationState:
    turns = []
    replaced = False
    for existing in state.turns:
        if existing.turn_id == turn.turn_id:
            turns.append(turn)
            replaced = True
        else:
            turns.append(existing)
    if not replaced:
        turns.append(turn)
    return _replace(state, turns=tuple(turns))


def _update_turn(
    state: TerminalConversationState,
    turn_id: TurnId,
    **changes,
) -> TerminalConversationState:
    turns = []
    found = False
    for turn in state.turns:
        if turn.turn_id == turn_id:
            turns.append(_replace(turn, **changes))
            found = True
        else:
            turns.append(turn)
    if not found:
        turns.append(
            ConversationTurn(
                turn_id=turn_id,
                trigger_message_id=None,
                status=changes.get("status", "unknown"),
                sequence=changes.get("sequence", state.header.last_sequence),
                completed_outcome=changes.get("completed_outcome"),
                model_duration_ms=changes.get("model_duration_ms"),
                model_input_tokens=changes.get("model_input_tokens"),
                model_output_tokens=changes.get("model_output_tokens"),
                failure_message=changes.get("failure_message"),
            )
        )
    return _replace(state, turns=tuple(turns))


def _append_turn_message(
    state: TerminalConversationState,
    turn_id: TurnId,
    message: ConversationMessage,
) -> TerminalConversationState:
    state = _ensure_turn(state, turn_id, message.sequence)
    return _update_turn_collection(
        state,
        turn_id,
        lambda turn: _replace(turn, messages=(*turn.messages, message)),
    )


def _attach_trigger_message_to_turn(
    state: TerminalConversationState,
    turn_id: TurnId,
    message_id: MessageId,
    sequence: int,
) -> TerminalConversationState:
    messages = []
    attached_message: ConversationMessage | None = None
    for message in state.messages:
        if message.message_id == message_id:
            attached_message = _replace(
                message,
                turn_id=turn_id,
                sequence=max(message.sequence, sequence),
            )
            messages.append(attached_message)
        else:
            messages.append(message)
    state = _replace(state, messages=tuple(messages))
    if attached_message is None:
        return state
    return _append_turn_message(state, turn_id, attached_message)


def _replace_turn_message(
    state: TerminalConversationState,
    message: ConversationMessage,
) -> TerminalConversationState:
    if message.turn_id is None:
        return state
    return _update_turn_collection(
        state,
        message.turn_id,
        lambda turn: _replace(
            turn,
            messages=tuple(
                message if item.message_id == message.message_id else item
                for item in turn.messages
            ),
        ),
    )


def _upsert_tool(
    state: TerminalConversationState,
    activity: ToolActivity,
) -> TerminalConversationState:
    state = _ensure_turn(state, activity.turn_id, activity.sequence)
    return _update_turn_collection(
        state,
        activity.turn_id,
        lambda turn: _replace(
            turn,
            tools=_upsert_tool_tuple(turn.tools, activity),
        ),
    )


def _append_tool_output(
    state: TerminalConversationState,
    tool_call_id: ToolCallId,
    output: str,
    sequence: int,
) -> TerminalConversationState:
    return _map_tool(
        state,
        tool_call_id,
        lambda tool: _replace(
            tool,
            output=(*tool.output, output),
            sequence=sequence,
        ),
    )


def _append_tool_artifact(
    state: TerminalConversationState,
    tool_call_id: ToolCallId,
    path: str | None,
    sequence: int,
) -> TerminalConversationState:
    if path is None:
        return state
    return _map_tool(
        state,
        tool_call_id,
        lambda tool: _replace(
            tool,
            artifact_paths=(*tool.artifact_paths, path),
            sequence=sequence,
        ),
    )


def _complete_tool(
    state: TerminalConversationState,
    tool_call_id: ToolCallId,
    *,
    success: bool,
    summary: str,
    exit_code: int | None,
    sequence: int,
) -> TerminalConversationState:
    return _map_tool(
        state,
        tool_call_id,
        lambda tool: _replace(
            tool,
            status=(
                ToolActivityStatus.SUCCEEDED if success else ToolActivityStatus.FAILED
            ),
            summary=summary,
            exit_code=exit_code,
            sequence=sequence,
        ),
    )


def _map_tool(
    state: TerminalConversationState,
    tool_call_id: ToolCallId,
    update,
) -> TerminalConversationState:
    return _replace(
        state,
        turns=tuple(
            _replace(
                turn,
                tools=tuple(
                    update(tool) if tool.tool_call_id == tool_call_id else tool
                    for tool in turn.tools
                ),
            )
            for turn in state.turns
        ),
    )


def _ensure_turn(
    state: TerminalConversationState,
    turn_id: TurnId,
    sequence: int,
) -> TerminalConversationState:
    if any(turn.turn_id == turn_id for turn in state.turns):
        return state
    return _replace(
        state,
        turns=(
            *state.turns,
            ConversationTurn(
                turn_id=turn_id,
                trigger_message_id=None,
                status="unknown",
                sequence=sequence,
            ),
        ),
    )


def _update_turn_collection(
    state: TerminalConversationState,
    turn_id: TurnId,
    update,
) -> TerminalConversationState:
    return _replace(
        state,
        turns=tuple(
            update(turn) if turn.turn_id == turn_id else turn for turn in state.turns
        ),
    )


def _upsert_tool_tuple(
    tools: tuple[ToolActivity, ...],
    activity: ToolActivity,
) -> tuple[ToolActivity, ...]:
    updated = []
    replaced = False
    for tool in tools:
        if tool.tool_call_id == activity.tool_call_id:
            updated.append(
                _replace(
                    activity,
                    output=tool.output,
                    artifact_paths=tool.artifact_paths,
                    summary=activity.summary or tool.summary,
                    exit_code=(
                        activity.exit_code
                        if activity.exit_code is not None
                        else tool.exit_code
                    ),
                    arguments_json=activity.arguments_json or tool.arguments_json,
                    policy_outcome=activity.policy_outcome or tool.policy_outcome,
                    policy_risk_level=activity.policy_risk_level
                    or tool.policy_risk_level,
                    policy_source_kind=activity.policy_source_kind
                    or tool.policy_source_kind,
                    policy_source_label=activity.policy_source_label
                    or tool.policy_source_label,
                    policy_reason=activity.policy_reason or tool.policy_reason,
                )
            )
            replaced = True
        else:
            updated.append(tool)
    if not replaced:
        updated.append(activity)
    return tuple(updated)


def _replace(obj, **changes):
    return replace(obj, **changes)
