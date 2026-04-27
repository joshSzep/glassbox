"""Textual widgets for the Glassbox terminal app shell."""

from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath
from textwrap import wrap
from typing import Any
from typing import ClassVar
from typing import cast

from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input
from textual.widgets import Static
from textual.widgets import TextArea

from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.commands import TerminalCommandItem
from glassbox.cli.tui.commands import command_items_for_state
from glassbox.cli.tui.commands import filter_command_items
from glassbox.cli.tui.conversation import AssistantMessageStatus
from glassbox.cli.tui.conversation import ConversationMessageKind
from glassbox.cli.tui.conversation import TerminalActionKind
from glassbox.cli.tui.conversation import TerminalActionState
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import ToolActivity
from glassbox.cli.tui.conversation import ToolActivityStatus
from glassbox.cli.tui.conversation import header_display_from_state
from glassbox.cli.tui.conversation import terminal_action_from_state

TRANSCRIPT_MIN_WIDTH = 36


@dataclass(frozen=True, slots=True)
class ComposerAvailability:
    can_edit: bool
    can_submit: bool
    placeholder: str
    disabled_reason: str | None = None


class ComposerSubmissionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    UNAVAILABLE_RUNTIME = "unavailable_runtime"
    RETRYABLE_FAILURE = "retryable_failure"


@dataclass(frozen=True, slots=True)
class ComposerSubmissionFeedback:
    status: ComposerSubmissionStatus
    message: str
    retryable: bool = False


class ActionFeedbackStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    UNAVAILABLE_RUNTIME = "unavailable_runtime"
    RETRYABLE_FAILURE = "retryable_failure"
    ALREADY_RESOLVED = "already_resolved"


@dataclass(frozen=True, slots=True)
class ActionFeedback:
    status: ActionFeedbackStatus
    message: str
    retryable: bool = False


class SessionHeader(Static):
    def __init__(self, state: TerminalConversationState) -> None:
        self._state = state
        super().__init__(render_session_header(state), id="session-header")

    def on_mount(self) -> None:
        self.update_state(self._state)

    def on_resize(self) -> None:
        self.update_state(self._state)

    def update_state(self, state: TerminalConversationState) -> None:
        self._state = state
        self.update(render_session_header(state, width=self._render_width()))

    def _render_width(self) -> int:
        if not self.is_mounted:
            return 80
        return max(self.size.width, 36)


class ConversationPane(Static):
    can_focus: ClassVar[bool] = True

    def __init__(self, state: TerminalConversationState) -> None:
        self._state = state
        self._follow_latest = True
        super().__init__(render_transcript(state), id="conversation-pane")

    def on_mount(self) -> None:
        self.update_state(self._state)

    def on_resize(self) -> None:
        self.update_state(self._state)

    def update_state(self, state: TerminalConversationState) -> None:
        self._follow_latest = self._follow_latest and self._is_at_latest()
        self._state = state
        self.update(render_transcript(state, width=self._render_width()))
        if self._follow_latest:
            self.call_after_refresh(self.jump_to_latest)

    def jump_to_latest(self) -> None:
        self._follow_latest = True
        with suppress(Exception):
            self.scroll_end(animate=False)

    def _render_width(self) -> int:
        if not self.is_mounted:
            return 80
        return max(self.size.width, TRANSCRIPT_MIN_WIDTH)

    def _is_at_latest(self) -> bool:
        if not self.is_mounted:
            return True
        return self.scroll_y >= max(self.max_scroll_y - 1, 0)


class ActionStripPlaceholder(Static):
    can_focus: ClassVar[bool] = True

    def __init__(
        self,
        state: TerminalConversationState,
        feedback: ActionFeedback | None = None,
    ) -> None:
        super().__init__(render_action_strip(state, feedback), id="action-strip")

    def update_state(
        self,
        state: TerminalConversationState,
        feedback: ActionFeedback | None = None,
    ) -> None:
        self.update(render_action_strip(state, feedback))


class ComposerWidget(TextArea):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+enter", "submit_prompt", "Send", show=False),
        Binding("ctrl+s", "submit_prompt", "Send", show=False),
        Binding("ctrl+up", "prompt_history_previous", "Previous prompt", show=False),
        Binding("ctrl+down", "prompt_history_next", "Next prompt", show=False),
    ]

    def __init__(
        self,
        state: TerminalConversationState,
        launch_options: InteractiveLaunchOptions,
    ) -> None:
        self._state = state
        self._launch_options = launch_options
        self._syncing_state = False
        availability = composer_availability(state)
        super().__init__(
            text=state.composer.text,
            id="composer",
            placeholder=availability.placeholder,
            soft_wrap=True,
            show_line_numbers=False,
        )
        self.update_state(state, launch_options)

    @property
    def is_syncing_state(self) -> bool:
        return self._syncing_state

    @property
    def can_submit(self) -> bool:
        return composer_availability(self._state).can_submit

    def update_state(
        self,
        state: TerminalConversationState,
        launch_options: InteractiveLaunchOptions,
    ) -> None:
        self._state = state
        self._launch_options = launch_options
        availability = composer_availability(state)
        self.read_only = not availability.can_edit
        self.placeholder = availability.placeholder
        self.tooltip = availability.disabled_reason
        if self.text != state.composer.text:
            self._syncing_state = True
            try:
                self.text = state.composer.text
            finally:
                self._syncing_state = False

    def show_submit_blocked(self) -> None:
        self.placeholder = composer_availability(self._state).placeholder

    async def action_submit_prompt(self) -> None:
        await cast(Any, self.app).action_submit_prompt()

    def action_prompt_history_previous(self) -> None:
        cast(Any, self.app).action_prompt_history_previous()

    def action_prompt_history_next(self) -> None:
        cast(Any, self.app).action_prompt_history_next()


class ComposerFeedbackLine(Static):
    def __init__(self, feedback: ComposerSubmissionFeedback | None = None) -> None:
        self._feedback = feedback
        super().__init__(render_composer_feedback(feedback), id="composer-feedback")

    def update_feedback(self, feedback: ComposerSubmissionFeedback | None) -> None:
        self._feedback = feedback
        self.update(render_composer_feedback(feedback))


class FooterHelp(Static):
    def __init__(self) -> None:
        super().__init__(render_footer_help(), id="footer")

    def on_mount(self) -> None:
        self.update(render_footer_help(width=self._render_width()))

    def on_resize(self) -> None:
        self.update(render_footer_help(width=self._render_width()))

    def _render_width(self) -> int:
        if not self.is_mounted:
            return 80
        return max(self.size.width, 24)


class CommandPaletteWidget(Vertical):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close_palette", "Close", show=False),
        Binding("enter", "execute_selected_command", "Run", show=False),
        Binding("down", "command_next", "Next", show=False),
        Binding("up", "command_previous", "Previous", show=False),
    ]

    def __init__(self, state: TerminalConversationState) -> None:
        self._state = state
        self._items = command_items_for_state(state)
        self._filtered_items = self._items
        self._selected_index = 0
        super().__init__(id="command-palette")
        self.display = False

    def compose(self):
        yield Input(placeholder="Search commands", id="command-filter")
        yield Static(self._render_items(), id="command-list")

    def open(self) -> None:
        self.display = True
        self.query_one(Input).value = ""
        self._refresh_filter("")
        self.query_one(Input).focus()

    def close(self) -> None:
        self.display = False

    def update_state(self, state: TerminalConversationState) -> None:
        self._state = state
        self._items = command_items_for_state(state)
        query = self.query_one(Input).value if self.is_mounted else ""
        self._refresh_filter(query)

    @property
    def selected_item(self) -> TerminalCommandItem | None:
        if not self._filtered_items:
            return None
        return self._filtered_items[self._selected_index]

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "command-filter":
            self._refresh_filter(event.value)

    def action_close_palette(self) -> None:
        cast(Any, self.app).close_command_palette(restore_focus=True)

    def action_execute_selected_command(self) -> None:
        item = self.selected_item
        if item is None:
            return
        cast(Any, self.app).execute_terminal_command(item.spec.command_id)

    def action_command_next(self) -> None:
        if self._filtered_items:
            self._selected_index = min(
                self._selected_index + 1,
                len(self._filtered_items) - 1,
            )
            self._render_list()

    def action_command_previous(self) -> None:
        if self._filtered_items:
            self._selected_index = max(self._selected_index - 1, 0)
            self._render_list()

    def _refresh_filter(self, query: str) -> None:
        self._filtered_items = filter_command_items(self._items, query)
        self._selected_index = min(self._selected_index, len(self._filtered_items) - 1)
        self._selected_index = max(self._selected_index, 0)
        self._render_list()

    def _render_list(self) -> None:
        if self.is_mounted:
            self.query_one("#command-list", Static).update(self._render_items())

    def _render_items(self) -> str:
        if not self._filtered_items:
            return "No matching commands"
        lines: list[str] = []
        for index, item in enumerate(self._filtered_items[:8]):
            marker = ">" if index == self._selected_index else " "
            shortcut = f" [{item.spec.shortcut}]" if item.spec.shortcut else ""
            suffix = "" if item.enabled else f" - {item.disabled_reason}"
            lines.append(f"{marker} {item.spec.title}{shortcut}{suffix}")
        return "\n".join(lines)


class DetailsPane(Static):
    can_focus: ClassVar[bool] = True

    def __init__(self, state: TerminalConversationState) -> None:
        self._state = state
        super().__init__(self._render_state(state), id="details-pane")
        self.display = False

    def update_state(self, state: TerminalConversationState) -> None:
        self._state = state
        self.update(self._render_state(state))

    def toggle(self) -> None:
        self.display = not self.display
        if self.display:
            self.focus()

    def _render_state(self, state: TerminalConversationState) -> str:
        return (
            "Details\n"
            f"session: {state.header.session_id}\n"
            f"mode: {state.header.mode.value}\n"
            f"stream: {state.header.stream_status.value}\n"
            f"sequence: {state.header.last_sequence}"
        )


def render_session_header(
    state: TerminalConversationState,
    *,
    width: int = 80,
) -> str:
    header = header_display_from_state(state, width=width)
    branch = f" | {header.branch_label}" if header.branch_label else ""
    dashboard = _dashboard_hint(header.dashboard_url, header.dashboard_label, width)
    if width < 52:
        line_one = (
            f"Glassbox {header.session_label} | {header.mode_label} | {dashboard}"
        )
    else:
        line_one = (
            f"Glassbox {header.session_label} | {header.mode_label} | "
            f"{header.stream_label} | {dashboard}"
        )
    line_two = (
        f"{header.cwd_label} | {header.model_label} | "
        f"{header.runtime_label}{branch} | {header.last_update_label}"
    )
    return f"{_fit_line(line_one, width)}\n{_fit_line(line_two, width)}"


def render_footer_help(*, width: int = 80) -> str:
    if width < 44:
        return _fit_line("Ctrl+Q Quit", width)
    if width < 64:
        return _fit_line("Ctrl+Q Quit | Ctrl+L Latest", width)
    if width < 84:
        return _fit_line("Ctrl+Q Quit | Ctrl+L Latest | Ctrl+P Palette", width)
    return _fit_line(
        "Ctrl+Q Quit | Ctrl+L Latest | Ctrl+P Palette | Ctrl+D Dashboard",
        width,
    )


def composer_availability(state: TerminalConversationState) -> ComposerAvailability:
    if state.header.mode == TerminalMode.HISTORICAL_ONLY:
        return ComposerAvailability(
            can_edit=False,
            can_submit=False,
            placeholder="Session is historical; start or attach to a running session.",
            disabled_reason="historical session",
        )
    if state.header.stream_status == TerminalStreamStatus.RECONNECTING:
        return ComposerAvailability(
            can_edit=False,
            can_submit=False,
            placeholder="Reconnecting to the runtime...",
            disabled_reason="runtime reconnecting",
        )
    if state.header.stream_status == TerminalStreamStatus.UNAVAILABLE:
        return ComposerAvailability(
            can_edit=False,
            can_submit=False,
            placeholder="Runtime stream unavailable; reconnect before sending.",
            disabled_reason="runtime stream unavailable",
        )
    if state.pending_approval is not None:
        return ComposerAvailability(
            can_edit=False,
            can_submit=False,
            placeholder="Resolve the pending approval before sending a prompt.",
            disabled_reason="pending approval",
        )
    if state.pending_question is not None:
        return ComposerAvailability(
            can_edit=True,
            can_submit=False,
            placeholder="Answer the pending question from the action strip.",
            disabled_reason="pending question",
        )
    if state.header.mode in {TerminalMode.THINKING, TerminalMode.RUNNING_TOOL}:
        return ComposerAvailability(
            can_edit=True,
            can_submit=False,
            placeholder="Agent is working; draft your next prompt here.",
            disabled_reason="active turn",
        )
    if state.header.mode == TerminalMode.FAILED:
        return ComposerAvailability(
            can_edit=False,
            can_submit=False,
            placeholder="Session failed; inspect details before sending.",
            disabled_reason="failed session",
        )
    return ComposerAvailability(
        can_edit=True,
        can_submit=True,
        placeholder="Write a prompt. Enter adds a line; Ctrl+Enter sends.",
    )


def render_composer_feedback(
    feedback: ComposerSubmissionFeedback | None,
) -> str:
    if feedback is None:
        return ""
    prefix = {
        ComposerSubmissionStatus.PENDING: "Sending",
        ComposerSubmissionStatus.ACCEPTED: "Accepted",
        ComposerSubmissionStatus.CONFLICT: "Not sent",
        ComposerSubmissionStatus.VALIDATION_ERROR: "Check prompt",
        ComposerSubmissionStatus.NETWORK_ERROR: "Network error",
        ComposerSubmissionStatus.UNAVAILABLE_RUNTIME: "Runtime unavailable",
        ComposerSubmissionStatus.RETRYABLE_FAILURE: "Send failed",
    }[feedback.status]
    suffix = " Retry is safe." if feedback.retryable else ""
    return f"{prefix}: {feedback.message}{suffix}"


def render_action_strip(
    state: TerminalConversationState,
    feedback: ActionFeedback | None = None,
) -> str:
    action = terminal_action_from_state(state)
    if action.kind == TerminalActionKind.PENDING_QUESTION:
        lines = [
            f"Question: {action.description}",
            _question_answer_line(action.answer_draft, state.composer.text),
            _question_hint_line(action.related_tool_name),
        ]
    elif action.kind == TerminalActionKind.PENDING_APPROVAL:
        lines = [
            f"Approval: {action.subject or action.description}",
            _approval_context_line(action),
            "Alt+A approve | Alt+X deny | Ctrl+E details",
        ]
    else:
        lines = [f"{action.title}: {action.description}"]
    if feedback is not None:
        lines.append(render_action_feedback(feedback))
    return "\n".join(lines)


def render_action_feedback(feedback: ActionFeedback) -> str:
    prefix = {
        ActionFeedbackStatus.PENDING: "Sending",
        ActionFeedbackStatus.ACCEPTED: "Accepted",
        ActionFeedbackStatus.CONFLICT: "Not sent",
        ActionFeedbackStatus.VALIDATION_ERROR: "Check answer",
        ActionFeedbackStatus.NETWORK_ERROR: "Network error",
        ActionFeedbackStatus.UNAVAILABLE_RUNTIME: "Runtime unavailable",
        ActionFeedbackStatus.RETRYABLE_FAILURE: "Action failed",
        ActionFeedbackStatus.ALREADY_RESOLVED: "Resolved",
    }[feedback.status]
    suffix = " Retry is safe." if feedback.retryable else ""
    return f"{prefix}: {feedback.message}{suffix}"


def _question_answer_line(answer_draft: str | None, composer_text: str) -> str:
    draft = answer_draft if answer_draft is not None else composer_text
    if draft.strip():
        return f"Answer draft: {_fit_line(draft.strip(), 72)}"
    return "Answer draft: write in the composer"


def _question_hint_line(related_tool_name: str | None) -> str:
    tool = f" | tool {related_tool_name}" if related_tool_name else ""
    return f"Ctrl+R submit answer{tool}"


def _approval_context_line(action: TerminalActionState) -> str:
    parts: list[str] = []
    if action.reason:
        parts.append(_fit_line(action.reason, 34))
    if action.related_tool_name:
        parts.append(f"tool {action.related_tool_name}")
    if action.policy_risk_level is not None:
        parts.append(f"risk {_enum_or_string_value(action.policy_risk_level)}")
    if action.policy_source_label:
        parts.append(f"policy {action.policy_source_label}")
    elif action.policy_source_kind is not None:
        parts.append(f"policy {_enum_or_string_value(action.policy_source_kind)}")
    if action.approval_id is not None:
        parts.append(f"id {action.approval_id}")
    return " | ".join(parts) if parts else action.description


def _enum_or_string_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def render_transcript(
    state: TerminalConversationState,
    *,
    width: int = 80,
) -> str:
    width = max(width, TRANSCRIPT_MIN_WIDTH)
    lines: list[str] = []
    if not state.messages and not state.turns and state.failure is None:
        return _empty_transcript_text(state)

    for message in state.messages:
        _append_message(lines, message.kind, message.text, width, message.status)

    for turn in state.turns:
        for tool in turn.tools:
            _append_tool(lines, tool, state, width)
        if turn.failure_message:
            _append_block(lines, "Turn failed", turn.failure_message, width)

    if state.failure is not None:
        _append_block(lines, "Failure", state.failure.message, width)

    return "\n".join(lines)


def _message_label(kind: ConversationMessageKind) -> str:
    if kind == ConversationMessageKind.USER:
        return "You"
    if kind == ConversationMessageKind.ASSISTANT:
        return "Assistant"
    if kind == ConversationMessageKind.RUNTIME:
        return "Runtime"
    return "System"


def _empty_transcript_text(state: TerminalConversationState) -> str:
    if state.header.mode == TerminalMode.STARTING:
        return "Starting session..."
    if state.header.mode == TerminalMode.HISTORICAL_ONLY:
        return "No transcript messages yet."
    return "Starting conversation..."


def _append_message(
    lines: list[str],
    kind: ConversationMessageKind,
    text: str,
    width: int,
    status: AssistantMessageStatus | None,
) -> None:
    title = _message_label(kind)
    if status == AssistantMessageStatus.STREAMING:
        title = f"{title} (streaming)"
    elif status == AssistantMessageStatus.COMPLETED:
        title = f"{title} (completed)"
    elif status == AssistantMessageStatus.INTERRUPTED:
        title = f"{title} (interrupted)"
    elif status == AssistantMessageStatus.FAILED:
        title = f"{title} (failed)"
    _append_block(lines, title, text or "...", width)


def _append_tool(
    lines: list[str],
    tool: ToolActivity,
    state: TerminalConversationState,
    width: int,
) -> None:
    status = _tool_status_label(tool, state)
    title = f"Tool: {_truncate_middle(tool.tool_name, 32)} [{status}]"
    details = _compact_tool_details(tool, state, width)
    if tool.tool_call_id in state.expanded_tool_ids:
        details.extend(_expanded_tool_details(tool, width))
    _append_block(lines, title, "\n".join(details), width)


def _tool_status_label(
    tool: ToolActivity,
    state: TerminalConversationState,
) -> str:
    if (
        state.pending_approval is not None
        and state.pending_approval.tool_call_id == tool.tool_call_id
        and state.pending_approval.decision is None
    ):
        return "awaiting approval"
    if tool.status == ToolActivityStatus.REQUESTED:
        return "requested"
    if tool.status == ToolActivityStatus.RUNNING:
        return "running"
    if tool.status == ToolActivityStatus.SUCCEEDED:
        return "completed"
    return "failed"


def _compact_tool_details(
    tool: ToolActivity,
    state: TerminalConversationState,
    width: int,
) -> list[str]:
    details: list[str] = []
    if tool.policy_outcome is not None:
        details.append(f"policy {_enum_or_string_value(tool.policy_outcome)}")
    if tool.policy_risk_level is not None:
        details.append(f"risk {_enum_or_string_value(tool.policy_risk_level)}")
    if tool.policy_source_label:
        details.append(f"source {_truncate_middle(tool.policy_source_label, 28)}")
    elif tool.policy_source_kind is not None:
        details.append(f"source {_enum_or_string_value(tool.policy_source_kind)}")
    if tool.summary:
        details.append(_fit_line(tool.summary, max(width - 2, 12)))
    if tool.exit_code is not None:
        details.append(f"exit {tool.exit_code}")
    if (
        state.pending_approval is not None
        and state.pending_approval.tool_call_id == tool.tool_call_id
        and state.pending_approval.decision is None
    ):
        details.append("approval pending")
    if tool.output_preview:
        preview = _fit_line(tool.output_preview.replace("\n", " "), max(width - 10, 12))
        suffix = " (truncated)" if tool.output_truncated else ""
        details.append(f"output: {preview}{suffix}")
    if tool.artifact_paths:
        paths = ", ".join(_truncate_path(path, 30) for path in tool.artifact_paths)
        details.append(f"artifacts: {paths}")
    if not details:
        details.append("waiting for tool output")
    return details


def _expanded_tool_details(tool: ToolActivity, width: int) -> list[str]:
    details = ["details expanded"]
    if tool.arguments_json:
        details.append(f"args: {_fit_line(tool.arguments_json, max(width - 8, 12))}")
    if tool.output_text:
        output = tool.output_text.replace("\n", "\\n")
        details.append(f"output full: {_fit_line(output, max(width - 15, 12))}")
    if tool.artifact_paths:
        for path in tool.artifact_paths:
            details.append(f"artifact: {_truncate_path(path, max(width - 12, 20))}")
    if tool.status == ToolActivityStatus.FAILED and tool.summary:
        details.append(f"failure: {_fit_line(tool.summary, max(width - 11, 12))}")
    return details


def _append_block(lines: list[str], title: str, text: str, width: int) -> None:
    if lines:
        lines.append("")
    lines.append(_fit_line(title, width))
    for raw_line in text.splitlines() or [""]:
        _append_wrapped_line(lines, raw_line, width)


def _append_wrapped_line(lines: list[str], value: str, width: int) -> None:
    line_width = max(width - 2, 12)
    if value.startswith("```"):
        lines.append("  " + _fit_line(value, line_width))
        return
    wrapped = wrap(
        value,
        width=line_width,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=False,
    )
    if not wrapped:
        lines.append("")
        return
    for line in wrapped:
        lines.append("  " + line)


def _dashboard_hint(
    dashboard_url: str | None,
    fallback: str,
    width: int,
) -> str:
    if dashboard_url is None:
        return fallback
    if width >= 104:
        return _truncate_middle(f"dashboard {dashboard_url}", 44)
    return fallback


def _fit_line(value: str, width: int) -> str:
    if width <= 0 or len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[: width - 3] + "..."


def _truncate_middle(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    if max_length <= 3:
        return value[:max_length]
    left = (max_length - 3) // 2
    right = max_length - 3 - left
    return f"{value[:left]}...{value[-right:]}"


def _truncate_path(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    path = PurePath(value)
    name = path.name
    if name and len(name) + 4 < max_length:
        prefix = _truncate_middle(str(path.parent), max_length - len(name) - 4)
        return f"{prefix}/.../{name}"
    return _truncate_middle(value, max_length)
