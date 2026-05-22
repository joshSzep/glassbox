"""Local handoff command helpers for the terminal app."""

from typing import Any

from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.handoff_dashboard import dashboard_handoff_url
from glassbox.cli.tui.handoff_dashboard import open_handoff_dashboard
from glassbox.cli.tui.handoff_message_builders import handoff_message
from glassbox.cli.tui.widgets import ActionFeedback
from glassbox.cli.tui.widgets import ActionFeedbackStatus
from glassbox.cli.tui.widgets import ConversationPane

_HANDOFF_COMMANDS = {
    TerminalCommandId.HANDOFF_READINESS,
    TerminalCommandId.HANDOFF_PREPARE_PREVIEW,
    TerminalCommandId.HANDOFF_PACKAGE_INSPECT,
    TerminalCommandId.HANDOFF_CUSTODY_ACTIONS,
    TerminalCommandId.HANDOFF_SAFE_COMMANDS,
    TerminalCommandId.HANDOFF_OPEN_DASHBOARD,
}


def is_handoff_command(command_id: TerminalCommandId) -> bool:
    return command_id in _HANDOFF_COMMANDS


def handoff_disabled_reason(
    command_id: TerminalCommandId,
    state: TerminalConversationState,
) -> str | None:
    if command_id == TerminalCommandId.HANDOFF_OPEN_DASHBOARD:
        if state.header.dashboard_url is None:
            return "dashboard unavailable"
        return None
    if state.header.cwd is None:
        return "workspace unavailable"
    return None


def execute_handoff_command(
    app: Any,
    command_id: TerminalCommandId,
    argument: str | None,
) -> None:
    if command_id == TerminalCommandId.HANDOFF_OPEN_DASHBOARD:
        open_handoff_dashboard(app)
        return
    message = handoff_message(command_id, app.state, argument)
    app.query_one(ConversationPane).show_local_message(message)
    app._set_action_feedback(
        ActionFeedback(ActionFeedbackStatus.ACCEPTED, "Handoff commands shown.")
    )


__all__ = [
    "dashboard_handoff_url",
    "execute_handoff_command",
    "handoff_disabled_reason",
    "is_handoff_command",
]
