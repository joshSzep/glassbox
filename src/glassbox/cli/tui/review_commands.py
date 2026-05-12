"""Review-loop command helpers for the terminal app."""

from typing import Any
from urllib.parse import quote
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from glassbox.cli.interactive_client import InteractiveClientError
from glassbox.cli.interactive_client import ReviewLoopAction
from glassbox.cli.interactive_client import ReviewLoopActionResult
from glassbox.cli.interactive_review_actions import review_feedback_message
from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.commands import TerminalSlashCommand
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.widgets import ActionFeedback
from glassbox.cli.tui.widgets import ActionFeedbackStatus
from glassbox.cli.tui.widgets import ConversationPane


def review_slash_command(rest: str) -> TerminalSlashCommand:
    parts = rest.strip().split(maxsplit=1)
    subcommand = parts[0].lower() if parts else "status"
    argument = parts[1] if len(parts) > 1 else None
    if subcommand in {"workup", "guide", "guided"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_WORKUP_GUIDE, argument)
    if subcommand in {"queue", "operator-queue"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_OPERATOR_QUEUE, argument)
    if subcommand in {"next", "next-action", "next-actions"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_NEXT_ACTIONS, argument)
    if subcommand in {"create", "new"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_CREATE_CHANGESET, argument)
    if subcommand == "refresh":
        return TerminalSlashCommand(
            TerminalCommandId.REVIEW_REFRESH_INVENTORY, argument
        )
    if subcommand in {"dashboard", "open-dashboard"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_OPEN_DASHBOARD, argument)
    if subcommand in {"brief", "lifecycle-brief"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_GENERATE_BRIEF, argument)
    if subcommand in {"verify", "verification", "verification-plan"}:
        return TerminalSlashCommand(
            TerminalCommandId.REVIEW_PREVIEW_VERIFICATION, argument
        )
    if subcommand in {"evidence", "evidence-graph", "graph"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_EVIDENCE_GRAPH, argument)
    if subcommand in {"handoff", "handoff-readiness"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_INSPECT_HANDOFF, argument)
    if subcommand in {"maintenance", "maintenance-checks"}:
        return TerminalSlashCommand(
            TerminalCommandId.REVIEW_MAINTENANCE_CHECKS,
            argument,
        )
    if subcommand in {"status", "feedback", "responses"}:
        return TerminalSlashCommand(
            TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS, argument
        )
    if subcommand in {"fixup", "fixup-inventory", "record-fixup"}:
        return TerminalSlashCommand(
            TerminalCommandId.REVIEW_RECORD_FEEDBACK_FIXUP, argument
        )
    return TerminalSlashCommand(
        TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS,
        f"{subcommand} {argument}".strip() if argument else subcommand,
    )


def review_disabled_reason(
    command_id: TerminalCommandId,
    state: TerminalConversationState,
) -> str | None:
    if command_id in {
        TerminalCommandId.REVIEW_CREATE_CHANGESET,
        TerminalCommandId.REVIEW_WORKUP_GUIDE,
        TerminalCommandId.REVIEW_REFRESH_INVENTORY,
        TerminalCommandId.REVIEW_GENERATE_BRIEF,
    }:
        if state.header.cwd is None:
            return "workspace unavailable"
        if state.header.stream_status in {
            TerminalStreamStatus.RECONNECTING,
            TerminalStreamStatus.UNAVAILABLE,
            TerminalStreamStatus.HISTORICAL_ONLY,
        }:
            return "runtime unavailable"
        return None
    if command_id in {
        TerminalCommandId.REVIEW_OPERATOR_QUEUE,
        TerminalCommandId.REVIEW_NEXT_ACTIONS,
        TerminalCommandId.REVIEW_PREVIEW_VERIFICATION,
        TerminalCommandId.REVIEW_EVIDENCE_GRAPH,
        TerminalCommandId.REVIEW_INSPECT_HANDOFF,
        TerminalCommandId.REVIEW_MAINTENANCE_CHECKS,
        TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS,
        TerminalCommandId.REVIEW_RECORD_FEEDBACK_FIXUP,
    }:
        if state.header.cwd is None:
            return "workspace unavailable"
        return None
    if command_id == TerminalCommandId.REVIEW_OPEN_DASHBOARD:
        if state.header.dashboard_url is None:
            return "dashboard unavailable"
        return None
    return None


def is_review_command(command_id: TerminalCommandId) -> bool:
    return command_id.name.startswith("REVIEW_")


async def execute_review_create(app: Any, argument: str | None) -> None:
    try:
        result = await app.client_adapter.create_review_changeset(
            objective=argument.strip() if argument and argument.strip() else None,
        )
    except InteractiveClientError as exc:
        app._set_action_feedback(
            ActionFeedback(ActionFeedbackStatus.CONFLICT, str(exc))
        )
        return
    except Exception as exc:
        app._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.RETRYABLE_FAILURE,
                str(exc) or "Review changeset creation failed.",
                retryable=True,
            )
        )
        return
    show_review_result(app, result)


async def execute_review_action(
    app: Any,
    action: ReviewLoopAction,
    argument: str | None,
) -> None:
    changeset_id = argument.strip() if argument and argument.strip() else None
    try:
        result = await app.client_adapter.run_review_action(
            action,
            changeset_id=changeset_id,
        )
    except InteractiveClientError as exc:
        app._set_action_feedback(
            ActionFeedback(ActionFeedbackStatus.CONFLICT, str(exc))
        )
        return
    except Exception as exc:
        app._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.RETRYABLE_FAILURE,
                str(exc) or "Review action failed.",
                retryable=True,
            )
        )
        return
    show_review_result(app, result)


def show_review_result(app: Any, result: ReviewLoopActionResult) -> None:
    lines = [result.headline]
    lines.extend(result.details)
    if result.limitations:
        lines.append("Limitations:")
        lines.extend(f"- {item}" for item in result.limitations[:5])
    if result.safe_next_actions:
        lines.append("Safe next actions:")
        lines.extend(f"- {item}" for item in result.safe_next_actions[:5])
    if result.dashboard_path is not None and app.state.header.dashboard_url is not None:
        dashboard_url = dashboard_review_url(
            app.state.header.dashboard_url,
            result.changeset_id,
        )
        lines.append(
            "Dashboard: " + dashboard_url
            if dashboard_url is not None
            else "Dashboard: unavailable"
        )
    app.query_one(ConversationPane).show_local_message("\n".join(lines))
    app._set_action_feedback(
        ActionFeedback(ActionFeedbackStatus.ACCEPTED, review_feedback_message(result))
    )


def open_review_dashboard(app: Any, argument: str | None) -> None:
    url = dashboard_review_url(
        app.state.header.dashboard_url,
        argument.strip() if argument and argument.strip() else None,
    )
    if url is None:
        app._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.CONFLICT, "Dashboard URL is unavailable."
            )
        )
        return
    try:
        app.open_url(url)
    except Exception as exc:
        app._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.RETRYABLE_FAILURE,
                str(exc) or "Review dashboard did not open.",
                retryable=True,
            )
        )
        return
    app._set_action_feedback(
        ActionFeedback(ActionFeedbackStatus.ACCEPTED, "Review dashboard opened.")
    )


def dashboard_review_url(
    dashboard_url: str | None,
    changeset_id: str | None,
) -> str | None:
    if dashboard_url is None:
        return None
    parts = urlsplit(dashboard_url)
    path = "/app/changesets"
    if changeset_id:
        path += "/" + quote(changeset_id, safe="")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def review_action_for_command(
    command_id: TerminalCommandId,
) -> ReviewLoopAction | None:
    if command_id == TerminalCommandId.REVIEW_OPERATOR_QUEUE:
        return ReviewLoopAction.OPERATOR_QUEUE
    if command_id == TerminalCommandId.REVIEW_NEXT_ACTIONS:
        return ReviewLoopAction.NEXT_ACTIONS
    if command_id == TerminalCommandId.REVIEW_REFRESH_INVENTORY:
        return ReviewLoopAction.REFRESH_INVENTORY
    if command_id == TerminalCommandId.REVIEW_WORKUP_GUIDE:
        return ReviewLoopAction.WORKUP_GUIDE
    if command_id == TerminalCommandId.REVIEW_GENERATE_BRIEF:
        return ReviewLoopAction.GENERATE_BRIEF
    if command_id == TerminalCommandId.REVIEW_PREVIEW_VERIFICATION:
        return ReviewLoopAction.PREVIEW_VERIFICATION
    if command_id == TerminalCommandId.REVIEW_EVIDENCE_GRAPH:
        return ReviewLoopAction.EVIDENCE_GRAPH
    if command_id == TerminalCommandId.REVIEW_INSPECT_HANDOFF:
        return ReviewLoopAction.INSPECT_HANDOFF
    if command_id == TerminalCommandId.REVIEW_MAINTENANCE_CHECKS:
        return ReviewLoopAction.MAINTENANCE_CHECKS
    if command_id == TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS:
        return ReviewLoopAction.SHOW_FEEDBACK_STATUS
    if command_id == TerminalCommandId.REVIEW_RECORD_FEEDBACK_FIXUP:
        return ReviewLoopAction.RECORD_FEEDBACK_FIXUP
    return None
