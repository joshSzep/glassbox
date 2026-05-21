"""Command dispatch helpers for the terminal app."""

from typing import Any

from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.commands import command_item_by_id
from glassbox.cli.tui.commands import command_items_for_state
from glassbox.cli.tui.handoff_commands import execute_handoff_command
from glassbox.cli.tui.handoff_commands import is_handoff_command
from glassbox.cli.tui.review_commands import execute_review_action
from glassbox.cli.tui.review_commands import execute_review_create
from glassbox.cli.tui.review_commands import open_review_dashboard
from glassbox.cli.tui.review_commands import review_action_for_command
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
        await execute_review_create(app, argument)
        return
    if command_id == TerminalCommandId.REVIEW_OPEN_DASHBOARD:
        open_review_dashboard(app, argument)
        return
    if is_handoff_command(command_id):
        execute_handoff_command(app, command_id, argument)
        return
    review_action = review_action_for_command(command_id)
    if review_action is not None:
        await execute_review_action(app, review_action, argument)
        return
    if command_id == TerminalCommandId.QUIT:
        app._handle_quit_request()
