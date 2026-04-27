"""Textual widgets for the Glassbox terminal app shell."""

from contextlib import suppress
from textwrap import wrap
from typing import ClassVar

from textual.widgets import Static

from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.conversation import AssistantMessageStatus
from glassbox.cli.tui.conversation import ConversationMessageKind
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import header_display_from_state
from glassbox.cli.tui.conversation import terminal_action_from_state

TRANSCRIPT_MIN_WIDTH = 36


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
    def __init__(self, state: TerminalConversationState) -> None:
        super().__init__(self._render_state(state), id="action-strip")

    def update_state(self, state: TerminalConversationState) -> None:
        self.update(self._render_state(state))

    def _render_state(self, state: TerminalConversationState) -> str:
        action = terminal_action_from_state(state)
        return f"{action.title}: {action.description}"


class ComposerPlaceholder(Static):
    def __init__(
        self,
        state: TerminalConversationState,
        launch_options: InteractiveLaunchOptions,
    ) -> None:
        super().__init__(self._render_state(state, launch_options), id="composer")

    def update_state(
        self,
        state: TerminalConversationState,
        launch_options: InteractiveLaunchOptions,
    ) -> None:
        self.update(self._render_state(state, launch_options))

    def _render_state(
        self,
        state: TerminalConversationState,
        launch_options: InteractiveLaunchOptions,
    ) -> str:
        draft = f" draft: {state.composer.text}" if state.composer.text else ""
        return f"{launch_options.default_mode.value} composer ready{draft}"


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
            _append_tool(lines, tool, width)
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


def _append_tool(lines: list[str], tool, width: int) -> None:
    title = f"Tool: {_truncate_middle(tool.tool_name, 32)} ({tool.status.value})"
    details: list[str] = []
    if tool.summary:
        details.append(tool.summary)
    if tool.exit_code is not None:
        details.append(f"exit {tool.exit_code}")
    if tool.output_preview:
        details.append(f"output: {tool.output_preview}")
    if tool.artifact_paths:
        details.append("artifacts: " + ", ".join(tool.artifact_paths))
    _append_block(lines, title, " | ".join(details) or "running", width)


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
