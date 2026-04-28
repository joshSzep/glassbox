"""Textual widgets for the Glassbox terminal app shell."""

from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath
from textwrap import wrap
from typing import Any
from typing import ClassVar
from typing import cast

from rich.markdown import Markdown
from rich.text import Text
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Resize
from textual.widgets import Input
from textual.widgets import RichLog
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
DETAILS_OUTPUT_PREVIEW_CHARS = 1200
TRANSCRIPT_USER_STYLE = "#8fc7ff"
TRANSCRIPT_ASSISTANT_STYLE = "#7bd88f"
TRANSCRIPT_RUNTIME_STYLE = "#aab2b7"
TRANSCRIPT_SYSTEM_STYLE = "#f5d36b"
TRANSCRIPT_FAILURE_STYLE = "#ff6b6b"


@dataclass(frozen=True, slots=True)
class TranscriptRenderLine:
    text: str
    style: str | None = None


@dataclass(frozen=True, slots=True)
class TranscriptRenderBlock:
    text: str
    style: str | None = None
    markdown: bool = False


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


class ConversationPane(RichLog):
    can_focus: ClassVar[bool] = True

    def __init__(self, state: TerminalConversationState) -> None:
        self._state = state
        self._follow_latest = True
        self._content_text = ""
        self._render_markdown = False
        self._scroll_callback_token = 0
        self._suppress_scroll_callback_invalidation = False
        self._rebuilding_content = False
        super().__init__(
            id="conversation-pane",
            auto_scroll=True,
            min_width=1,
            wrap=False,
            markup=False,
        )

    @property
    def content_text(self) -> str:
        return self._content_text

    def on_mount(self) -> None:
        self.update_state(self._state)

    def on_resize(self, event: Resize) -> None:
        super().on_resize(event)
        self.update_state(self._state)

    @property
    def markdown_enabled(self) -> bool:
        return self._render_markdown

    def update_state(
        self,
        state: TerminalConversationState,
        *,
        render_markdown: bool | None = None,
    ) -> None:
        self._state = state
        if render_markdown is not None:
            self._render_markdown = render_markdown
        self._replace_content(
            render_transcript_lines(state, width=self._render_width()),
            render_transcript_blocks(state) if self._render_markdown else None,
        )

    def jump_to_latest(self) -> None:
        self._follow_latest = True
        self._schedule_jump_to_latest()

    def _schedule_jump_to_latest(self) -> None:
        token = self._next_scroll_callback_token()
        with suppress(Exception):
            self.call_after_refresh(lambda: self._jump_to_latest_immediate(token))

    def _jump_to_latest_immediate(self, token: int) -> None:
        if token != self._scroll_callback_token:
            return
        with suppress(Exception):
            self._set_scroll_y_without_invalidating_callbacks(self.max_scroll_y)
            self.call_after_refresh(lambda: self._jump_to_latest_final(token))

    def _jump_to_latest_final(self, token: int) -> None:
        if token != self._scroll_callback_token:
            return
        with suppress(Exception):
            self._set_scroll_y_without_invalidating_callbacks(self.max_scroll_y)

    def page_up(self) -> None:
        self._invalidate_scroll_callbacks()
        with suppress(Exception):
            self.scroll_y = max(
                self.scroll_y - max(self.size.height - 1, 1),
                0,
            )
            self._follow_latest = False

    def page_down(self) -> None:
        self._invalidate_scroll_callbacks()
        with suppress(Exception):
            self.scroll_y = min(
                self.scroll_y + max(self.size.height - 1, 1),
                self.max_scroll_y,
            )
            self._follow_latest = self._is_at_latest()

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        if (
            self.is_mounted
            and not self._rebuilding_content
            and not self._suppress_scroll_callback_invalidation
        ):
            self._follow_latest = new_value >= self.max_scroll_y
            if not self._follow_latest:
                self._invalidate_scroll_callbacks()

    def on_mouse_scroll_up(self) -> None:
        self._invalidate_scroll_callbacks()
        self._follow_latest = False

    def on_mouse_scroll_down(self) -> None:
        self._invalidate_scroll_callbacks()
        self._follow_latest = False

    def show_local_message(self, message: str) -> None:
        self._replace_content(_plain_transcript_lines(message))

    def _replace_content(
        self,
        lines: list[TranscriptRenderLine],
        blocks: list[TranscriptRenderBlock] | None = None,
    ) -> None:
        previous_scroll_y = self.scroll_y if self.is_mounted else 0
        should_follow_latest = self._follow_latest
        self._rebuilding_content = True
        try:
            self.clear()
            self._content_text = "\n".join(line.text for line in lines)
            width = self._render_width()
            if blocks is not None:
                self._write_markdown_blocks(blocks, width)
                self._restore_scroll_position(previous_scroll_y, should_follow_latest)
                return
            for line in lines:
                self.write(
                    Text(line.text, style=line.style or ""),
                    width=width,
                    scroll_end=False,
                )
        finally:
            self._rebuilding_content = False
        self._restore_scroll_position(previous_scroll_y, should_follow_latest)

    def _restore_scroll_position(
        self,
        previous_scroll_y: float,
        should_follow_latest: bool,
    ) -> None:
        if should_follow_latest:
            self._follow_latest = True
            self._schedule_jump_to_latest()
            return
        self._follow_latest = False
        token = self._next_scroll_callback_token()
        self.call_after_refresh(
            lambda: self._restore_manual_scroll_position(token, previous_scroll_y)
        )

    def _restore_manual_scroll_position(
        self,
        token: int,
        previous_scroll_y: float,
    ) -> None:
        if token != self._scroll_callback_token:
            return
        with suppress(Exception):
            self._set_scroll_y_without_invalidating_callbacks(
                min(previous_scroll_y, self.max_scroll_y)
            )

    def _next_scroll_callback_token(self) -> int:
        self._scroll_callback_token += 1
        return self._scroll_callback_token

    def _invalidate_scroll_callbacks(self) -> None:
        self._scroll_callback_token += 1

    def _set_scroll_y_without_invalidating_callbacks(self, value: float) -> None:
        self._suppress_scroll_callback_invalidation = True
        try:
            self.scroll_y = value
        finally:
            self._suppress_scroll_callback_invalidation = False

    def _write_markdown_blocks(
        self,
        blocks: list[TranscriptRenderBlock],
        width: int,
    ) -> None:
        for block in blocks:
            if block.markdown:
                self.write(
                    Markdown(
                        block.text,
                        style=block.style or "none",
                        hyperlinks=False,
                    ),
                    width=width,
                    scroll_end=False,
                )
            else:
                self.write(
                    Text(block.text, style=block.style or ""),
                    width=width,
                    scroll_end=False,
                )

    def _render_width(self) -> int:
        if not self.is_mounted:
            return 80
        content_width = self.scrollable_content_region.width
        if content_width > 0:
            return content_width
        return max(self.size.width - 2, 1)

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
        self.display = _should_show_action_strip(state, feedback)

    def update_state(
        self,
        state: TerminalConversationState,
        feedback: ActionFeedback | None = None,
    ) -> None:
        self.display = _should_show_action_strip(state, feedback)
        self.update(render_action_strip(state, feedback))


class ComposerWidget(TextArea):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("enter", "submit_prompt", "Send", show=False),
        Binding("ctrl+enter", "insert_newline", "New line", show=False),
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
        self.styles.height = _composer_height_for_state(state)
        if self.text != state.composer.text:
            self._syncing_state = True
            try:
                self.text = state.composer.text
            finally:
                self._syncing_state = False

    async def on_key(self, event) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            await self.action_submit_prompt()
        elif event.key == "ctrl+enter":
            event.prevent_default()
            event.stop()
            self.action_insert_newline()

    def show_submit_blocked(self) -> None:
        self.placeholder = composer_availability(self._state).placeholder

    async def action_submit_prompt(self) -> None:
        await cast(Any, self.app).action_submit_prompt()

    def action_insert_newline(self) -> None:
        self.insert("\n")

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


class CommandPaletteInput(Input):
    async def on_key(self, event) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            await cast(Any, self.parent).execute_selected_command()
        elif event.key == "down":
            event.prevent_default()
            event.stop()
            cast(Any, self.parent).action_command_next()
        elif event.key == "up":
            event.prevent_default()
            event.stop()
            cast(Any, self.parent).action_command_previous()
        elif event.key == "escape":
            event.prevent_default()
            event.stop()
            cast(Any, self.app).close_command_palette(restore_focus=True)


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
        yield CommandPaletteInput(placeholder="Search commands", id="command-filter")
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

    async def action_execute_selected_command(self) -> None:
        await self.execute_selected_command()

    async def execute_selected_command(self) -> None:
        item = self.selected_item
        if item is None:
            return
        await cast(Any, self.app).execute_terminal_command(item.spec.command_id)

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
        super().__init__(render_details_pane(state), id="details-pane")
        self.display = False

    def update_state(self, state: TerminalConversationState) -> None:
        self._state = state
        self.update(render_details_pane(state, width=self._render_width()))

    def on_mount(self) -> None:
        self.update_state(self._state)

    def on_resize(self) -> None:
        self.update_state(self._state)

    def toggle(self) -> None:
        self.display = not self.display
        if self.display:
            self.focus()

    def _render_width(self) -> int:
        if not self.is_mounted:
            return 80
        return max(self.size.width, 24)


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
        return _fit_line("Ctrl+Esc Quit", width)
    if width < 64:
        return _fit_line("Ctrl+Esc Quit | Ctrl+L Bottom", width)
    if width < 84:
        return _fit_line("Ctrl+Esc Quit | Ctrl+L Bottom | Ctrl+P Palette", width)
    return _fit_line(
        "Ctrl+Esc Quit | Ctrl+L Bottom | Ctrl+P Palette | Ctrl+D Dashboard",
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
            can_edit=True,
            can_submit=False,
            placeholder="Use Alt+A/Alt+X or type /approve or /deny.",
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
        placeholder="Write a prompt. Enter sends; Ctrl+Enter adds a line.",
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
            f"{_approval_title(action)}: {action.subject or action.description}",
            _approval_context_line(action),
            "Primary: Alt+A approve | Alt+X deny | Ctrl+E policy details",
        ]
    else:
        lines = [f"{action.title}: {action.description}"]
    if feedback is not None:
        lines.append(render_action_feedback(feedback))
    return "\n".join(lines)


def _should_show_action_strip(
    state: TerminalConversationState,
    feedback: ActionFeedback | None,
) -> bool:
    if feedback is not None:
        return True
    return terminal_action_from_state(state).kind != TerminalActionKind.PROMPT


def _composer_height_for_state(state: TerminalConversationState) -> int:
    if terminal_action_from_state(state).kind == TerminalActionKind.PROMPT:
        return 8
    return 3


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


def render_details_pane(
    state: TerminalConversationState,
    *,
    width: int = 80,
) -> str:
    tool = _selected_tool_for_details(state)
    tool_count = sum(len(turn.tools) for turn in state.turns)
    lines = [
        "Details",
        f"session: {state.header.session_id}",
        f"mode: {state.header.mode.value}",
        f"stream: {state.header.stream_status.value}",
        f"sequence: {state.header.last_sequence}",
        (
            f"recent: {len(state.messages)} messages | "
            f"{len(state.turns)} turns | {tool_count} tools"
        ),
    ]
    if state.header.dashboard_url is not None:
        lines.extend(
            _wrapped_label_lines("dashboard", state.header.dashboard_url, width)
        )
    if state.failure is not None:
        lines.append(f"failure: {_fit_line(state.failure.message, width - 9)}")
    if tool is None:
        lines.append("selected tool: none")
        return "\n".join(_fit_line(line, width) for line in lines)
    lines.extend(_tool_details_lines(tool, state, width))
    return "\n".join(_fit_line(line, width) for line in lines)


def _selected_tool_for_details(
    state: TerminalConversationState,
) -> ToolActivity | None:
    tools = [tool for turn in state.turns for tool in turn.tools]
    if not tools:
        return None
    for tool in reversed(tools):
        if tool.tool_call_id in state.expanded_tool_ids:
            return tool
    return tools[-1]


def _tool_details_lines(
    tool: ToolActivity,
    state: TerminalConversationState,
    width: int,
) -> list[str]:
    status = _tool_status_label(tool, state)
    lines = [
        f"selected tool: {_truncate_middle(tool.tool_name, 40)} [{status}]",
        f"tool id: {tool.tool_call_id}",
    ]
    if tool.arguments_json:
        lines.append(f"args: {_fit_line(tool.arguments_json, width - 6)}")
    policy_parts: list[str] = []
    if tool.policy_outcome is not None:
        policy_parts.append(
            _policy_decision_label(tool.policy_outcome, tool.policy_source_kind)
        )
    if tool.policy_risk_level is not None:
        policy_parts.append(f"risk {_enum_or_string_value(tool.policy_risk_level)}")
    source = _policy_source_label(tool.policy_source_kind, tool.policy_source_label)
    if source:
        policy_parts.append(f"source {source}")
    if policy_parts:
        lines.append("policy: " + " | ".join(policy_parts))
    if tool.policy_reason:
        lines.append(f"policy reason: {_fit_line(tool.policy_reason, width - 15)}")
    if tool.summary:
        lines.append(f"summary: {_fit_line(tool.summary, width - 9)}")
    if tool.exit_code is not None:
        lines.append(f"exit: {tool.exit_code}")
    if tool.output_text:
        output = tool.output_text.replace("\n", "\\n")
        truncated = len(output) > DETAILS_OUTPUT_PREVIEW_CHARS
        preview = output[:DETAILS_OUTPUT_PREVIEW_CHARS]
        lines.append(f"output: {_fit_line(preview, width - 8)}")
        if truncated:
            lines.append("output policy: truncated; dashboard has full output")
    else:
        lines.append("output: none yet")
    for path in tool.artifact_paths:
        lines.append(f"artifact: {_truncate_path(path, width - 10)}")
    return lines


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
    if action.policy_outcome is not None:
        parts.append(
            _policy_decision_label(action.policy_outcome, action.policy_source_kind)
        )
    if action.reason:
        parts.append(_fit_line(action.reason, 34))
    if action.related_tool_name:
        parts.append(f"tool {action.related_tool_name}")
    if action.policy_risk_level is not None:
        parts.append(f"risk {_enum_or_string_value(action.policy_risk_level)}")
    source = _policy_source_label(action.policy_source_kind, action.policy_source_label)
    if source:
        parts.append(f"source {source}")
    if action.approval_id is not None:
        parts.append(f"id {action.approval_id}")
    return " | ".join(parts) if parts else action.description


def _approval_title(action: TerminalActionState) -> str:
    if action.policy_outcome is not None:
        return _policy_decision_label(
            action.policy_outcome,
            action.policy_source_kind,
        ).title()
    return "Approval"


def _policy_decision_label(
    outcome: object,
    source_kind: object | None = None,
) -> str:
    outcome_value = _enum_or_string_value(outcome)
    source_value = (
        _enum_or_string_value(source_kind) if source_kind is not None else None
    )
    if outcome_value == "approve":
        return "policy approval required"
    if outcome_value == "deny":
        return "denied by policy"
    if outcome_value == "blocked" and source_value == "invariant":
        return "invariant block"
    if outcome_value == "blocked":
        return "blocked by policy"
    if outcome_value == "allow":
        return "advisory risk accepted"
    return f"outcome {outcome_value}"


def _policy_source_label(source_kind: object | None, source_label: str | None) -> str:
    if source_kind is not None and source_label:
        return f"{_enum_or_string_value(source_kind)}:{source_label}"
    if source_label:
        return source_label
    if source_kind is not None:
        return _enum_or_string_value(source_kind)
    return ""


def _enum_or_string_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def render_transcript(
    state: TerminalConversationState,
    *,
    width: int = 80,
) -> str:
    return "\n".join(line.text for line in render_transcript_lines(state, width=width))


def render_transcript_lines(
    state: TerminalConversationState,
    *,
    width: int = 80,
) -> list[TranscriptRenderLine]:
    width = max(width, TRANSCRIPT_MIN_WIDTH)
    lines: list[TranscriptRenderLine] = []
    if not _has_visible_transcript_content(state):
        return [
            TranscriptRenderLine(
                _empty_transcript_text(state),
                TRANSCRIPT_RUNTIME_STYLE,
            )
        ]

    for message in state.messages:
        _append_message(lines, message.kind, message.text, width, message.status)

    for turn in state.turns:
        if turn.failure_message:
            _append_block(
                lines,
                "Turn failed",
                turn.failure_message,
                width,
                title_style=TRANSCRIPT_FAILURE_STYLE,
                body_style=TRANSCRIPT_FAILURE_STYLE,
            )

    if state.failure is not None:
        _append_block(
            lines,
            "Failure",
            state.failure.message,
            width,
            title_style=TRANSCRIPT_FAILURE_STYLE,
            body_style=TRANSCRIPT_FAILURE_STYLE,
        )

    return lines


def render_transcript_blocks(
    state: TerminalConversationState,
) -> list[TranscriptRenderBlock]:
    blocks: list[TranscriptRenderBlock] = []
    if not _has_visible_transcript_content(state):
        return [
            TranscriptRenderBlock(
                _empty_transcript_text(state),
                TRANSCRIPT_RUNTIME_STYLE,
            )
        ]

    for message in state.messages:
        if blocks:
            blocks.append(TranscriptRenderBlock(""))
        style = _message_style(message.kind)
        blocks.append(
            TranscriptRenderBlock(message.text or "...", style, markdown=True)
        )
        if marker := _message_status_marker(message.status):
            blocks.append(
                TranscriptRenderBlock(
                    marker,
                    _message_status_style(message.status),
                )
            )

    for turn in state.turns:
        if turn.failure_message:
            if blocks:
                blocks.append(TranscriptRenderBlock(""))
            blocks.append(
                TranscriptRenderBlock("Turn failed", TRANSCRIPT_FAILURE_STYLE)
            )
            blocks.append(
                TranscriptRenderBlock(turn.failure_message, TRANSCRIPT_FAILURE_STYLE)
            )

    if state.failure is not None:
        if blocks:
            blocks.append(TranscriptRenderBlock(""))
        blocks.append(TranscriptRenderBlock("Failure", TRANSCRIPT_FAILURE_STYLE))
        blocks.append(
            TranscriptRenderBlock(state.failure.message, TRANSCRIPT_FAILURE_STYLE)
        )

    return blocks


def _has_visible_transcript_content(state: TerminalConversationState) -> bool:
    if state.messages or state.failure is not None:
        return True
    return any(turn.failure_message for turn in state.turns)


def _message_style(kind: ConversationMessageKind) -> str:
    if kind == ConversationMessageKind.USER:
        return TRANSCRIPT_USER_STYLE
    if kind == ConversationMessageKind.ASSISTANT:
        return TRANSCRIPT_ASSISTANT_STYLE
    if kind == ConversationMessageKind.RUNTIME:
        return TRANSCRIPT_RUNTIME_STYLE
    return TRANSCRIPT_SYSTEM_STYLE


def _message_status_marker(status: AssistantMessageStatus | None) -> str | None:
    if status == AssistantMessageStatus.INTERRUPTED:
        return "[interrupted]"
    if status == AssistantMessageStatus.FAILED:
        return "[failed]"
    return None


def _message_status_style(status: AssistantMessageStatus | None) -> str:
    if status == AssistantMessageStatus.FAILED:
        return TRANSCRIPT_FAILURE_STYLE
    return TRANSCRIPT_SYSTEM_STYLE


def _empty_transcript_text(state: TerminalConversationState) -> str:
    if state.header.mode == TerminalMode.STARTING:
        return "Starting session..."
    if state.header.mode == TerminalMode.HISTORICAL_ONLY:
        return "No transcript messages yet."
    return "Starting conversation..."


def _append_message(
    lines: list[TranscriptRenderLine],
    kind: ConversationMessageKind,
    text: str,
    width: int,
    status: AssistantMessageStatus | None,
) -> None:
    if lines:
        lines.append(TranscriptRenderLine(""))
    style = _message_style(kind)
    for raw_line in (text or "...").splitlines() or [""]:
        _append_wrapped_line(lines, raw_line, width, style)
    if marker := _message_status_marker(status):
        _append_wrapped_line(lines, marker, width, _message_status_style(status))


def _append_tool(
    lines: list[TranscriptRenderLine],
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


def _append_block(
    lines: list[TranscriptRenderLine],
    title: str,
    text: str,
    width: int,
    *,
    title_style: str | None = TRANSCRIPT_SYSTEM_STYLE,
    body_style: str | None = None,
) -> None:
    if lines:
        lines.append(TranscriptRenderLine(""))
    lines.append(TranscriptRenderLine(_fit_line(title, width), title_style))
    for raw_line in text.splitlines() or [""]:
        _append_wrapped_line(lines, raw_line, width, body_style)


def _append_wrapped_line(
    lines: list[TranscriptRenderLine],
    value: str,
    width: int,
    style: str | None,
) -> None:
    line_width = max(width, 12)
    if value.startswith("```"):
        lines.append(TranscriptRenderLine(_fit_line(value, line_width), style))
        return
    wrapped = wrap(
        value,
        width=line_width,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=False,
    )
    if not wrapped:
        lines.append(TranscriptRenderLine("", style))
        return
    for line in wrapped:
        lines.append(TranscriptRenderLine(line, style))


def _plain_transcript_lines(text: str) -> list[TranscriptRenderLine]:
    return [TranscriptRenderLine(line) for line in text.splitlines() or [""]]


def _dashboard_hint(
    dashboard_url: str | None,
    fallback: str,
    width: int,
) -> str:
    if dashboard_url is None:
        return fallback
    if width >= 104:
        return "dashboard ready (Ctrl+D open, Alt+D copy)"
    return "dashboard ready"


def _wrapped_label_lines(label: str, value: str, width: int) -> list[str]:
    prefix = f"{label}: "
    available_width = max(width - len(prefix), 12)
    wrapped = wrap(
        value,
        width=available_width,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=False,
    ) or [""]
    return [
        (prefix if index == 0 else " " * len(prefix)) + line
        for index, line in enumerate(wrapped)
    ]


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
