"""Initial Textual widgets for the Glassbox terminal app shell."""

from textual.widgets import Static

from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.conversation import AssistantMessageStatus
from glassbox.cli.tui.conversation import ConversationMessageKind
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import header_display_from_state
from glassbox.cli.tui.conversation import terminal_action_from_state


class SessionHeader(Static):
    def __init__(self, state: TerminalConversationState) -> None:
        super().__init__(self._render_state(state), id="session-header")

    def update_state(self, state: TerminalConversationState) -> None:
        self.update(self._render_state(state))

    def _render_state(self, state: TerminalConversationState) -> str:
        header = header_display_from_state(state, width=80)
        branch = f" | {header.branch_label}" if header.branch_label else ""
        return (
            f"Glassbox {header.session_label} | {header.mode_label} | "
            f"{header.stream_label} | {header.dashboard_label}\n"
            f"{header.cwd_label} | {header.model_label} | "
            f"{header.runtime_label}{branch} | {header.last_update_label}"
        )


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
        super().__init__("Ctrl+Q quit | Ctrl+L latest | Ctrl+P palette", id="footer")


def _message_label(kind: ConversationMessageKind) -> str:
    if kind == ConversationMessageKind.USER:
        return "you"
    if kind == ConversationMessageKind.ASSISTANT:
        return "assistant"
    return kind.value
