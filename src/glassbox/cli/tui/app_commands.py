"""Command dispatch helpers for the terminal app."""

from typing import Any
from urllib.parse import quote
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from glassbox.cli.interactive_client import InteractiveClientError
from glassbox.cli.interactive_client import ReviewLoopAction
from glassbox.cli.interactive_client import ReviewLoopActionResult
from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.commands import command_item_by_id
from glassbox.cli.tui.commands import command_items_for_state
from glassbox.cli.tui.widgets import ActionFeedback
from glassbox.cli.tui.widgets import ActionFeedbackStatus
from glassbox.cli.tui.widgets import ConversationPane
from glassbox.cli.tui.widgets import DetailsPane
from glassbox.core.types import ApprovalDecision


async def execute_terminal_command(
    app: Any,
    command_id: TerminalCommandId,
    *,
    argument: str | None = None,
) -> None:
    if command_id == TerminalCommandId.INTERRUPT:
        app.close_command_palette(restore_focus=True)
        await app._handle_interrupt_request()
        return
    if command_id == TerminalCommandId.SUBMIT_ANSWER:
        app.close_command_palette(restore_focus=True)
        await app._submit_pending_answer()
        return
    if command_id == TerminalCommandId.APPROVE:
        app.close_command_palette(restore_focus=True)
        await app._resolve_pending_approval(ApprovalDecision.APPROVED)
        return
    if command_id == TerminalCommandId.DENY:
        app.close_command_palette(restore_focus=True)
        await app._resolve_pending_approval(ApprovalDecision.DENIED)
        return
    item = command_item_by_id(command_items_for_state(app.state), command_id)
    if item is not None and not item.enabled:
        return
    app.close_command_palette(restore_focus=True)
    if command_id == TerminalCommandId.STATUS:
        return
    if command_id == TerminalCommandId.OPEN_DASHBOARD:
        app._open_dashboard()
        return
    if command_id == TerminalCommandId.COPY_SESSION_ID:
        app._copy_handoff_value(
            str(app.state.header.session_id),
            success_message="Session ID copied.",
        )
        return
    if command_id == TerminalCommandId.COPY_DASHBOARD_URL:
        app._copy_dashboard_url()
        return
    if command_id == TerminalCommandId.COPY_ARTIFACT_PATH:
        app._copy_latest_artifact_path()
        return
    if command_id == TerminalCommandId.OPEN_ARTIFACT_PATH:
        app._open_latest_artifact_path()
        return
    if command_id == TerminalCommandId.TOGGLE_DETAILS:
        app._details_visible = not app._details_visible
        details = app.query_one(DetailsPane)
        details.toggle()
        if details.display:
            app.set_focus(details)
        return
    if command_id == TerminalCommandId.TOGGLE_MARKDOWN:
        app._transcript_markdown_enabled = not app._transcript_markdown_enabled
        app.query_one(ConversationPane).update_state(
            app.state,
            render_markdown=app._transcript_markdown_enabled,
        )
        state_label = "enabled" if app._transcript_markdown_enabled else "disabled"
        app._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.ACCEPTED,
                f"Markdown rendering {state_label}.",
            )
        )
        return
    if command_id == TerminalCommandId.JUMP_LATEST:
        app.action_latest()
        return
    if command_id == TerminalCommandId.CLEAR_TRANSCRIPT:
        app.query_one(ConversationPane).show_local_message("Transcript hidden locally.")
        return
    if command_id == TerminalCommandId.REVIEW_CREATE_CHANGESET:
        await _execute_review_create(app, argument)
        return
    if command_id == TerminalCommandId.REVIEW_OPEN_DASHBOARD:
        _open_review_dashboard(app, argument)
        return
    review_action = _review_action_for_command(command_id)
    if review_action is not None:
        await _execute_review_action(app, review_action, argument)
        return
    if command_id == TerminalCommandId.QUIT:
        app._handle_quit_request()


async def _execute_review_create(app: Any, argument: str | None) -> None:
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
    _show_review_result(app, result)


async def _execute_review_action(
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
    _show_review_result(app, result)


def _show_review_result(app: Any, result: ReviewLoopActionResult) -> None:
    lines = [result.headline]
    lines.extend(result.details)
    if result.limitations:
        lines.append("Limitations:")
        lines.extend(f"- {item}" for item in result.limitations[:5])
    if result.safe_next_actions:
        lines.append("Safe next actions:")
        lines.extend(f"- {item}" for item in result.safe_next_actions[:5])
    if result.dashboard_path is not None and app.state.header.dashboard_url is not None:
        dashboard_url = _dashboard_review_url(
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
        ActionFeedback(ActionFeedbackStatus.ACCEPTED, _review_feedback_message(result))
    )


def _open_review_dashboard(app: Any, argument: str | None) -> None:
    url = _dashboard_review_url(
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


def _dashboard_review_url(
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


def _review_feedback_message(result: ReviewLoopActionResult) -> str:
    parts = [result.headline]
    if result.limitations:
        parts.append(f"Limitation: {result.limitations[0]}")
    if result.safe_next_actions:
        parts.append(f"Next: {result.safe_next_actions[0]}")
    return " ".join(parts)


def _review_action_for_command(
    command_id: TerminalCommandId,
) -> ReviewLoopAction | None:
    if command_id == TerminalCommandId.REVIEW_REFRESH_INVENTORY:
        return ReviewLoopAction.REFRESH_INVENTORY
    if command_id == TerminalCommandId.REVIEW_GENERATE_BRIEF:
        return ReviewLoopAction.GENERATE_BRIEF
    if command_id == TerminalCommandId.REVIEW_PREVIEW_VERIFICATION:
        return ReviewLoopAction.PREVIEW_VERIFICATION
    if command_id == TerminalCommandId.REVIEW_INSPECT_HANDOFF:
        return ReviewLoopAction.INSPECT_HANDOFF
    if command_id == TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS:
        return ReviewLoopAction.SHOW_FEEDBACK_STATUS
    return None
