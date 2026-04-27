"""Textual widgets for the Glassbox terminal app shell."""

from textual.widgets import Static

from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.conversation import AssistantMessageStatus
from glassbox.cli.tui.conversation import ConversationMessageKind
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import header_display_from_state
from glassbox.cli.tui.conversation import terminal_action_from_state


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
    def __init__(self, state: TerminalConversationState) -> None:
        super().__init__(self._render_state(state), id="conversation-pane")

    def update_state(self, state: TerminalConversationState) -> None:
        self.update(self._render_state(state))

    def _render_state(self, state: TerminalConversationState) -> str:
        if not state.messages and not state.turns and state.failure is None:
            return "Starting conversation..."
        lines: list[str] = []
        for message in state.messages:
            label = _message_label(message.kind)
            suffix = (
                " (streaming)"
                if message.status == AssistantMessageStatus.STREAMING
                else ""
            )
            lines.append(f"{label}{suffix}: {message.text or '...'}")
        for turn in state.turns:
            for tool in turn.tools:
                lines.append(
                    f"tool {tool.tool_name}: {tool.status.value}"
                    + (f" - {tool.summary}" if tool.summary else "")
                )
        if state.failure is not None:
            lines.append(f"failure: {state.failure.message}")
        return "\n".join(lines)


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


def _message_label(kind: ConversationMessageKind) -> str:
    if kind == ConversationMessageKind.USER:
        return "you"
    if kind == ConversationMessageKind.ASSISTANT:
        return "assistant"
    return kind.value


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
