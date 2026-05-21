"""Local handoff command helpers for the terminal app."""

from typing import Any
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.conversation import TerminalConversationState
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
        _open_handoff_dashboard(app)
        return
    message = _handoff_message(command_id, app.state, argument)
    app.query_one(ConversationPane).show_local_message(message)
    app._set_action_feedback(
        ActionFeedback(ActionFeedbackStatus.ACCEPTED, "Handoff commands shown.")
    )


def _handoff_message(
    command_id: TerminalCommandId,
    state: TerminalConversationState,
    argument: str | None,
) -> str:
    session_id = str(state.header.session_id)
    source_id = _argument_or_default(argument, session_id)
    cwd = state.header.cwd or "."
    if command_id == TerminalCommandId.HANDOFF_READINESS:
        return "\n".join(
            [
                "Handoff readiness",
                _command(
                    "glassbox",
                    "session",
                    "handoff-readiness",
                    source_id,
                    "--intent",
                    "review-only",
                    "--cwd",
                    cwd,
                ),
                _command(
                    "glassbox",
                    "handoff",
                    "prepare",
                    "session",
                    source_id,
                    "handoff.json",
                    "--preview",
                    "--cwd",
                    cwd,
                ),
                "Non-claims: local posture, not approval or continuation authority.",
            ]
        )
    if command_id == TerminalCommandId.HANDOFF_PREPARE_PREVIEW:
        return "\n".join(
            [
                "Handoff prepare preview",
                _command(
                    "glassbox",
                    "handoff",
                    "prepare",
                    "session",
                    source_id,
                    "handoff.json",
                    "--preview",
                    "--json",
                    "--cwd",
                    cwd,
                ),
                _command(
                    "glassbox",
                    "handoff",
                    "prepare",
                    "session",
                    source_id,
                    "handoff.json",
                    "--intent",
                    "future-self",
                    "--markdown-output",
                    "handoff.md",
                    "--cwd",
                    cwd,
                ),
                "Preview shows redaction, local-only evidence, and safe commands.",
            ]
        )
    if command_id == TerminalCommandId.HANDOFF_PACKAGE_INSPECT:
        package_path = _argument_or_default(argument, "handoff.json")
        return "\n".join(
            [
                "Handoff package inspection",
                _command("glassbox", "handoff", "inspect", package_path, "--cwd", cwd),
                _command(
                    "glassbox",
                    "handoff",
                    "inspect",
                    package_path,
                    "--markdown",
                    "--cwd",
                    cwd,
                ),
                _command(
                    "glassbox",
                    "handoff",
                    "import",
                    package_path,
                    "--triage",
                    "--cwd",
                    cwd,
                ),
                "Inspection and triage do not resume or merge imported state.",
            ]
        )
    if command_id == TerminalCommandId.HANDOFF_CUSTODY_ACTIONS:
        session_arg, package_arg = _session_package_args(argument, session_id)
        return "\n".join(
            [
                "Handoff custody actions",
                _command(
                    "glassbox",
                    "handoff",
                    "guidance",
                    session_arg,
                    package_arg,
                    "--cwd",
                    cwd,
                ),
                _command(
                    "glassbox",
                    "handoff",
                    "accept",
                    session_arg,
                    package_arg,
                    "--cwd",
                    cwd,
                ),
                _command(
                    "glassbox",
                    "handoff",
                    "reject",
                    session_arg,
                    package_arg,
                    "--reason",
                    "REASON",
                    "--cwd",
                    cwd,
                ),
                _command(
                    "glassbox",
                    "handoff",
                    "archive",
                    session_arg,
                    package_arg,
                    "--reason",
                    "REASON",
                    "--cwd",
                    cwd,
                ),
                "Custody is not verification, review, release, or runtime authority.",
            ]
        )
    return "\n".join(
        [
            "Safe handoff commands",
            _command("glassbox", "handoff", "list", "--cwd", cwd),
            _command(
                "glassbox", "session", "handoff-readiness", session_id, "--cwd", cwd
            ),
            _command(
                "glassbox",
                "handoff",
                "prepare",
                "session",
                session_id,
                "handoff.json",
                "--preview",
                "--cwd",
                cwd,
            ),
            _command("glassbox", "handoff", "inspect", "handoff.json", "--cwd", cwd),
            "These inspect or preview first; mutating follow-up remains explicit.",
        ]
    )


def _open_handoff_dashboard(app: Any) -> None:
    url = dashboard_handoff_url(app.state.header.dashboard_url)
    if url is None:
        app._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.CONFLICT,
                "Dashboard URL is unavailable.",
            )
        )
        return
    try:
        app.open_url(url)
    except Exception as exc:
        app._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.RETRYABLE_FAILURE,
                str(exc) or "Handoff dashboard did not open.",
                retryable=True,
            )
        )
        return
    app._set_action_feedback(
        ActionFeedback(ActionFeedbackStatus.ACCEPTED, "Handoff dashboard opened.")
    )


def dashboard_handoff_url(dashboard_url: str | None) -> str | None:
    if dashboard_url is None:
        return None
    parts = urlsplit(dashboard_url)
    return urlunsplit((parts.scheme, parts.netloc, "/app/handoffs", "", ""))


def _argument_or_default(argument: str | None, default: str) -> str:
    value = argument.strip() if argument and argument.strip() else ""
    return value or default


def _command(*parts: str) -> str:
    return "- " + " ".join(parts)


def _session_package_args(
    argument: str | None, default_session_id: str
) -> tuple[str, str]:
    parts = argument.strip().split(maxsplit=1) if argument and argument.strip() else []
    if len(parts) == 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return default_session_id, parts[0]
    return default_session_id, "PACKAGE_ID"


__all__ = [
    "dashboard_handoff_url",
    "execute_handoff_command",
    "handoff_disabled_reason",
    "is_handoff_command",
]
