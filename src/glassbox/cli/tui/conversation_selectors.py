"""Selectors and display derivation for terminal conversation state."""

from dataclasses import replace
from pathlib import PurePath

from glassbox.cli.tui.conversation_models import ComposerDraftState
from glassbox.cli.tui.conversation_models import TerminalActionKind
from glassbox.cli.tui.conversation_models import TerminalActionState
from glassbox.cli.tui.conversation_models import TerminalConversationState
from glassbox.cli.tui.conversation_models import TerminalHeaderDisplayState
from glassbox.cli.tui.conversation_models import TerminalHeaderState
from glassbox.cli.tui.conversation_models import TerminalMode
from glassbox.cli.tui.conversation_models import TerminalStreamStatus
from glassbox.cli.tui.conversation_models import ToolActivity
from glassbox.core.ids import QuestionId
from glassbox.core.ids import ToolCallId
from glassbox.core.models import MessagePart
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus
from glassbox.core.types import TurnStatus

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
            policy_outcome=approval.policy_outcome,
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


def mode_from_session_status(status: SessionStatus) -> TerminalMode:
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


def stream_status_from_session_status(status: SessionStatus) -> TerminalStreamStatus:
    if status in {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.CANCELLED,
    }:
        return TerminalStreamStatus.HISTORICAL_ONLY
    return TerminalStreamStatus.LIVE


def mode_from_turn_status(status: TurnStatus) -> TerminalMode:
    if status == TurnStatus.EXECUTING_TOOL:
        return TerminalMode.RUNNING_TOOL
    if status == TurnStatus.AWAITING_APPROVAL:
        return TerminalMode.AWAITING_APPROVAL
    if status == TurnStatus.AWAITING_USER_INPUT:
        return TerminalMode.AWAITING_ANSWER
    if status == TurnStatus.FAILED:
        return TerminalMode.FAILED
    return TerminalMode.THINKING


def text_from_parts(parts: list[MessagePart]) -> str:
    return "".join(part.text for part in parts if part.kind == "text")


def _with_header(
    state: TerminalConversationState, **changes
) -> TerminalConversationState:
    return _replace(state, header=_replace(state.header, **changes))


def _find_tool(
    state: TerminalConversationState,
    *,
    tool_call_id: ToolCallId | None,
    turn_id,
) -> ToolActivity | None:
    for turn in state.turns:
        if turn_id is not None and turn.turn_id != turn_id:
            continue
        for tool in turn.tools:
            if tool_call_id is None or tool.tool_call_id == tool_call_id:
                return tool
    return None


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
