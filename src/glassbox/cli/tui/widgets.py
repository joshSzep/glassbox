"""Initial Textual widgets for the Glassbox terminal app shell."""

from textual.widgets import Static

from glassbox.cli.tui.state import TerminalAppState


class SessionHeader(Static):
    def __init__(self, state: TerminalAppState) -> None:
        dashboard = state.dashboard_url or "dashboard unavailable"
        super().__init__(
            f"Glassbox session {state.session_id}\n"
            f"{state.status} | {state.model_name or 'model unknown'} | {dashboard}",
            id="session-header",
        )


class ConversationPane(Static):
    def __init__(self, state: TerminalAppState) -> None:
        detail = f"last event sequence {state.last_sequence}"
        if state.pending_question_text is not None:
            detail = f"pending question: {state.pending_question_text}"
        super().__init__(detail, id="conversation-pane")


class ComposerPlaceholder(Static):
    def __init__(self, state: TerminalAppState) -> None:
        super().__init__(
            f"{state.launch_options.default_mode.value} composer ready",
            id="composer",
        )
