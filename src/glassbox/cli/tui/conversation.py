"""Pure terminal conversation state reducer for the TUI."""

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from enum import StrEnum
from pathlib import PurePath
from uuid import UUID

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
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
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import MessageId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolCallId
from glassbox.core.ids import TurnId
from glassbox.core.models import MessagePart
from glassbox.core.models import PolicyDecisionOutcome
from glassbox.core.models import PolicyDecisionSourceKind
from glassbox.core.models import PolicyRiskLevel
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus
from glassbox.core.types import TurnStatus

TOOL_OUTPUT_PREVIEW_CHARS = 160


class TerminalStreamStatus(StrEnum):
    LIVE = "live"
    RECONNECTING = "reconnecting"
    UNAVAILABLE = "unavailable"
    HISTORICAL_ONLY = "historical_only"


class TerminalMode(StrEnum):
    STARTING = "starting"
    READY = "ready"
    THINKING = "thinking"
    RUNNING_TOOL = "running_tool"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_ANSWER = "awaiting_answer"
    FAILED = "failed"
    HISTORICAL_ONLY = "historical_only"


MODE_LABELS: dict[TerminalMode, str] = {
    TerminalMode.STARTING: "starting",
    TerminalMode.READY: "ready",
    TerminalMode.THINKING: "thinking",
    TerminalMode.RUNNING_TOOL: "running tool",
    TerminalMode.AWAITING_APPROVAL: "awaiting approval",
    TerminalMode.AWAITING_ANSWER: "awaiting answer",
    TerminalMode.FAILED: "failed",
    TerminalMode.HISTORICAL_ONLY: "historical",
}

STREAM_LABELS: dict[TerminalStreamStatus, str] = {
    TerminalStreamStatus.LIVE: "live",
    TerminalStreamStatus.RECONNECTING: "reconnecting",
    TerminalStreamStatus.UNAVAILABLE: "unavailable",
    TerminalStreamStatus.HISTORICAL_ONLY: "historical",
}


class ConversationMessageKind(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    RUNTIME = "runtime"


class AssistantMessageStatus(StrEnum):
    STREAMING = "streaming"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


class ToolActivityStatus(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TerminalActionKind(StrEnum):
    PROMPT = "prompt"
    PENDING_APPROVAL = "pending_approval"
    PENDING_QUESTION = "pending_question"
    ACTIVE_TURN_WAIT = "active_turn_wait"
    FAILED = "failed"
    HISTORICAL_ONLY = "historical_only"
    UNAVAILABLE_PROMPT = "unavailable_prompt"


@dataclass(frozen=True, slots=True)
class TerminalHeaderState:
    session_id: SessionId
    status: SessionStatus
    mode: TerminalMode
    stream_status: TerminalStreamStatus = TerminalStreamStatus.LIVE
    model_name: str | None = None
    cwd: str | None = None
    approval_mode: str | None = None
    branch_label: str | None = None
    runtime_owner: str | None = None
    dashboard_url: str | None = None
    current_turn_id: TurnId | None = None
    last_sequence: int = 0
    stream_detail: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalHeaderDisplayState:
    session_label: str
    mode_label: str
    stream_label: str
    model_label: str
    cwd_label: str
    branch_label: str | None
    runtime_label: str
    dashboard_label: str
    last_update_label: str
    dashboard_url: str | None


@dataclass(frozen=True, slots=True)
class ComposerDraftState:
    text: str = ""
    question_id: QuestionId | None = None


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    kind: ConversationMessageKind
    text: str
    sequence: int
    message_id: MessageId | None = None
    turn_id: TurnId | None = None
    status: AssistantMessageStatus | None = None
    imported: bool = False


@dataclass(frozen=True, slots=True)
class ToolActivity:
    tool_call_id: ToolCallId
    turn_id: TurnId
    tool_name: str
    status: ToolActivityStatus
    sequence: int
    arguments_json: str | None = None
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None
    policy_reason: str | None = None
    output: tuple[str, ...] = ()
    summary: str | None = None
    exit_code: int | None = None
    artifact_paths: tuple[str, ...] = ()

    @property
    def output_text(self) -> str:
        return "".join(self.output)

    @property
    def output_preview(self) -> str:
        output_text = self.output_text
        if len(output_text) <= TOOL_OUTPUT_PREVIEW_CHARS:
            return output_text
        return f"{output_text[:TOOL_OUTPUT_PREVIEW_CHARS]}..."

    @property
    def output_truncated(self) -> bool:
        return len(self.output_text) > TOOL_OUTPUT_PREVIEW_CHARS


@dataclass(frozen=True, slots=True)
class PendingApprovalState:
    approval_id: ApprovalId
    turn_id: TurnId
    subject: str
    reason: str
    sequence: int
    tool_call_id: ToolCallId | None = None
    decision: ApprovalDecision | None = None
    policy_outcome: PolicyDecisionOutcome | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalActionState:
    kind: TerminalActionKind
    title: str
    description: str
    turn_id: TurnId | None = None
    approval_id: ApprovalId | None = None
    question_id: QuestionId | None = None
    tool_call_id: ToolCallId | None = None
    related_tool_name: str | None = None
    subject: str | None = None
    reason: str | None = None
    policy_risk_level: PolicyRiskLevel | None = None
    policy_source_kind: PolicyDecisionSourceKind | None = None
    policy_source_label: str | None = None
    allowed_decisions: tuple[ApprovalDecision, ...] = ()
    answer_draft: str | None = None
    debug_id: str | None = None


@dataclass(frozen=True, slots=True)
class PendingQuestionState:
    question_id: QuestionId
    turn_id: TurnId
    tool_call_id: ToolCallId
    question: str
    sequence: int
    answer: str | None = None


@dataclass(frozen=True, slots=True)
class FailureState:
    message: str
    sequence: int
    turn_id: TurnId | None = None
    retryable: bool | None = None


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    turn_id: TurnId
    trigger_message_id: MessageId | None
    status: TurnStatus | str
    sequence: int
    messages: tuple[ConversationMessage, ...] = ()
    tools: tuple[ToolActivity, ...] = ()
    completed_outcome: str | None = None
    model_duration_ms: int | None = None
    model_input_tokens: int | None = None
    model_output_tokens: int | None = None
    failure_message: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalConversationState:
    header: TerminalHeaderState
    composer: ComposerDraftState = field(default_factory=ComposerDraftState)
    messages: tuple[ConversationMessage, ...] = ()
    turns: tuple[ConversationTurn, ...] = ()
    pending_approval: PendingApprovalState | None = None
    pending_question: PendingQuestionState | None = None
    failure: FailureState | None = None
    expanded_tool_ids: frozenset[ToolCallId] = frozenset()

    def with_dashboard_url(
        self,
        dashboard_url: str | None,
    ) -> TerminalConversationState:
        return replace(
            self,
            header=replace(self.header, dashboard_url=dashboard_url),
        )


def conversation_state_from_snapshot(
    snapshot: InteractiveSessionSnapshot,
) -> TerminalConversationState:
    status = snapshot.state.status
    stream_status = _stream_status_from_session_status(status)
    mode = _mode_from_session_status(status)
    if status == SessionStatus.RUNNING and snapshot.state.current_turn_id is not None:
        mode = TerminalMode.THINKING
    return TerminalConversationState(
        header=TerminalHeaderState(
            session_id=snapshot.session_id,
            status=status,
            mode=mode,
            stream_status=stream_status,
            model_name=snapshot.model_name,
            cwd=snapshot.cwd,
            approval_mode=snapshot.approval_mode,
            dashboard_url=snapshot.dashboard_url,
            current_turn_id=snapshot.state.current_turn_id,
            last_sequence=snapshot.last_sequence,
        ),
        pending_question=(
            PendingQuestionState(
                question_id=snapshot.state.pending_question_id,
                turn_id=snapshot.state.current_turn_id or UUID(int=0),
                tool_call_id=UUID(int=0),
                question=snapshot.pending_question_text or "",
                sequence=snapshot.last_sequence,
            )
            if snapshot.state.pending_question_id is not None
            else None
        ),
    )


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
                text=_text_from_parts(payload.parts),
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
        mode = _mode_from_turn_status(payload.status)
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
            _text_from_parts(payload.parts),
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


def with_composer_draft(
    state: TerminalConversationState,
    text: str,
    *,
    question_id: QuestionId | None = None,
) -> TerminalConversationState:
    return _replace(
        state,
        composer=ComposerDraftState(text=text, question_id=question_id),
    )


def with_stream_status(
    state: TerminalConversationState,
    stream_status: TerminalStreamStatus,
    *,
    detail: str | None = None,
) -> TerminalConversationState:
    mode = state.header.mode
    if stream_status == TerminalStreamStatus.HISTORICAL_ONLY:
        mode = TerminalMode.HISTORICAL_ONLY
    return _with_header(
        state,
        stream_status=stream_status,
        stream_detail=detail,
        mode=mode,
    )


def with_runtime_owner(
    state: TerminalConversationState,
    runtime_owner: str | None,
) -> TerminalConversationState:
    return _with_header(state, runtime_owner=runtime_owner)


def header_display_from_state(
    state: TerminalConversationState,
    *,
    width: int,
) -> TerminalHeaderDisplayState:
    header = state.header
    compact = width < 80
    model_width = 14 if compact else 32
    cwd_width = 18 if compact else 44
    branch_width = 10 if compact else 24
    runtime_width = 12 if compact else 24

    return TerminalHeaderDisplayState(
        session_label=str(header.session_id)[:8],
        mode_label=_mode_label(header),
        stream_label=_stream_label(header),
        model_label=_truncate_middle(header.model_name or "model unknown", model_width),
        cwd_label=_truncate_path(header.cwd or "workspace unknown", cwd_width),
        branch_label=(
            _truncate_middle(header.branch_label, branch_width)
            if header.branch_label is not None
            else None
        ),
        runtime_label=_truncate_middle(header.runtime_owner or "local", runtime_width),
        dashboard_label="dashboard"
        if header.dashboard_url is not None
        else "no dashboard",
        dashboard_url=header.dashboard_url,
        last_update_label=f"seq {header.last_sequence}",
    )


def with_tool_expanded(
    state: TerminalConversationState,
    tool_call_id: ToolCallId,
    *,
    expanded: bool,
) -> TerminalConversationState:
    expanded_tool_ids = set(state.expanded_tool_ids)
    if expanded:
        expanded_tool_ids.add(tool_call_id)
    else:
        expanded_tool_ids.discard(tool_call_id)
    return _replace(state, expanded_tool_ids=frozenset(expanded_tool_ids))


def latest_artifact_path_from_state(
    state: TerminalConversationState,
) -> str | None:
    for turn in reversed(state.turns):
        for tool in reversed(turn.tools):
            if tool.artifact_paths:
                return tool.artifact_paths[-1]
    return None


def terminal_action_from_state(
    state: TerminalConversationState,
) -> TerminalActionState:
    approval = state.pending_approval
    if approval is not None and approval.decision is None:
        related_tool = _find_tool(
            state,
            tool_call_id=approval.tool_call_id,
            turn_id=approval.turn_id,
        )
        return TerminalActionState(
            kind=TerminalActionKind.PENDING_APPROVAL,
            title="Approval required",
            description=approval.subject,
            turn_id=approval.turn_id,
            approval_id=approval.approval_id,
            tool_call_id=approval.tool_call_id,
            related_tool_name=related_tool.tool_name if related_tool else None,
            subject=approval.subject,
            reason=approval.reason,
            policy_risk_level=approval.policy_risk_level,
            policy_source_kind=approval.policy_source_kind,
            policy_source_label=approval.policy_source_label,
            allowed_decisions=(ApprovalDecision.APPROVED, ApprovalDecision.DENIED),
            debug_id=str(approval.approval_id),
        )

    question = state.pending_question
    if question is not None and question.answer is None:
        related_tool = _find_tool(
            state,
            tool_call_id=question.tool_call_id,
            turn_id=question.turn_id,
        )
        answer_draft = None
        if state.composer.question_id == question.question_id:
            answer_draft = state.composer.text
        return TerminalActionState(
            kind=TerminalActionKind.PENDING_QUESTION,
            title="Answer required",
            description=question.question,
            turn_id=question.turn_id,
            question_id=question.question_id,
            tool_call_id=question.tool_call_id,
            related_tool_name=related_tool.tool_name if related_tool else None,
            answer_draft=answer_draft,
            debug_id=str(question.question_id),
        )

    if state.failure is not None or state.header.mode == TerminalMode.FAILED:
        message = (
            state.failure.message if state.failure is not None else "Session failed"
        )
        return TerminalActionState(
            kind=TerminalActionKind.FAILED,
            title="Session failed",
            description=message,
            turn_id=state.failure.turn_id if state.failure is not None else None,
        )

    if state.header.stream_status == TerminalStreamStatus.HISTORICAL_ONLY:
        return TerminalActionState(
            kind=TerminalActionKind.HISTORICAL_ONLY,
            title="Historical session",
            description="This session can be inspected but not continued live.",
        )

    if state.header.stream_status == TerminalStreamStatus.UNAVAILABLE:
        return TerminalActionState(
            kind=TerminalActionKind.UNAVAILABLE_PROMPT,
            title="Runtime unavailable",
            description=state.header.stream_detail or "Live runtime is unavailable.",
        )

    if state.header.current_turn_id is not None or state.header.mode in {
        TerminalMode.THINKING,
        TerminalMode.RUNNING_TOOL,
    }:
        return TerminalActionState(
            kind=TerminalActionKind.ACTIVE_TURN_WAIT,
            title="Working",
            description="The assistant is still working on the current turn.",
            turn_id=state.header.current_turn_id,
        )

    return TerminalActionState(
        kind=TerminalActionKind.PROMPT,
        title="Ready",
        description="Type the next prompt.",
    )


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


def _find_tool(
    state: TerminalConversationState,
    *,
    tool_call_id: ToolCallId | None,
    turn_id: TurnId | None,
) -> ToolActivity | None:
    for turn in state.turns:
        if turn_id is not None and turn.turn_id != turn_id:
            continue
        for tool in turn.tools:
            if tool_call_id is None or tool.tool_call_id == tool_call_id:
                return tool
    return None


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


def _mode_from_session_status(status: SessionStatus) -> TerminalMode:
    if status == SessionStatus.AWAITING_APPROVAL:
        return TerminalMode.AWAITING_APPROVAL
    if status == SessionStatus.AWAITING_USER_INPUT:
        return TerminalMode.AWAITING_ANSWER
    if status in {SessionStatus.IDLE, SessionStatus.RUNNING}:
        return TerminalMode.READY
    if status == SessionStatus.FAILED:
        return TerminalMode.FAILED
    if status in {
        SessionStatus.COMPLETED,
        SessionStatus.CANCELLED,
    }:
        return TerminalMode.HISTORICAL_ONLY
    return TerminalMode.STARTING


def _mode_label(header: TerminalHeaderState) -> str:
    if header.stream_status == TerminalStreamStatus.RECONNECTING:
        return MODE_LABELS[header.mode]
    if header.stream_status == TerminalStreamStatus.UNAVAILABLE:
        return "unavailable"
    return MODE_LABELS[header.mode]


def _stream_label(header: TerminalHeaderState) -> str:
    label = STREAM_LABELS[header.stream_status]
    if header.stream_detail is None:
        return label
    return f"{label}: {header.stream_detail}"


def _stream_status_from_session_status(status: SessionStatus) -> TerminalStreamStatus:
    if status in {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.CANCELLED,
    }:
        return TerminalStreamStatus.HISTORICAL_ONLY
    return TerminalStreamStatus.LIVE


def _mode_from_turn_status(status: TurnStatus) -> TerminalMode:
    if status == TurnStatus.EXECUTING_TOOL:
        return TerminalMode.RUNNING_TOOL
    if status == TurnStatus.AWAITING_APPROVAL:
        return TerminalMode.AWAITING_APPROVAL
    if status == TurnStatus.AWAITING_USER_INPUT:
        return TerminalMode.AWAITING_ANSWER
    if status == TurnStatus.FAILED:
        return TerminalMode.FAILED
    return TerminalMode.THINKING


def _text_from_parts(parts: list[MessagePart]) -> str:
    return "".join(part.text for part in parts if part.kind == "text")


def _truncate_middle(value: str, max_length: int) -> str:
    if max_length < 4:
        return value[:max_length]
    if len(value) <= max_length:
        return value
    head_length = (max_length - 3) // 2
    tail_length = max_length - 3 - head_length
    return f"{value[:head_length]}...{value[-tail_length:]}"


def _truncate_path(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    path = PurePath(value)
    name = path.name
    if name and len(name) + 4 <= max_length:
        prefix_length = max_length - len(name) - 4
        parent = str(path.parent)
        return f"{_truncate_middle(parent, prefix_length)}.../{name}"
    return _truncate_middle(value, max_length)


def _replace(obj, **changes):
    return replace(obj, **changes)
