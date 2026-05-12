"""Contextual command enablement for the terminal app command registry."""

from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.commands import TerminalCommandItem
from glassbox.cli.tui.commands import TerminalCommandSpec
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import latest_artifact_path_from_state


def item_for_spec(
    spec: TerminalCommandSpec,
    state: TerminalConversationState,
) -> TerminalCommandItem:
    disabled_reason = disabled_reason_for_command(spec.command_id, state)
    return TerminalCommandItem(
        spec=spec,
        enabled=disabled_reason is None,
        disabled_reason=disabled_reason,
    )


def disabled_reason_for_command(
    command_id: TerminalCommandId,
    state: TerminalConversationState,
) -> str | None:
    from glassbox.cli.tui.review_commands import is_review_command
    from glassbox.cli.tui.review_commands import review_disabled_reason

    if is_review_command(command_id):
        return review_disabled_reason(command_id, state)
    if command_id in {
        TerminalCommandId.OPEN_DASHBOARD,
        TerminalCommandId.COPY_DASHBOARD_URL,
    }:
        if state.header.dashboard_url is None:
            return "dashboard unavailable"
    if command_id in {
        TerminalCommandId.COPY_ARTIFACT_PATH,
        TerminalCommandId.OPEN_ARTIFACT_PATH,
    }:
        if latest_artifact_path_from_state(state) is None:
            return "no artifact path"
    if command_id in {TerminalCommandId.APPROVE, TerminalCommandId.DENY}:
        if (
            state.pending_approval is None
            or state.pending_approval.decision is not None
        ):
            return "no pending approval"
        if state.header.stream_status in {
            TerminalStreamStatus.RECONNECTING,
            TerminalStreamStatus.UNAVAILABLE,
            TerminalStreamStatus.HISTORICAL_ONLY,
        }:
            return "runtime unavailable"
    if command_id == TerminalCommandId.SUBMIT_ANSWER:
        if state.pending_question is None or state.pending_question.answer is not None:
            return "no pending question"
        if state.header.stream_status in {
            TerminalStreamStatus.RECONNECTING,
            TerminalStreamStatus.UNAVAILABLE,
            TerminalStreamStatus.HISTORICAL_ONLY,
        }:
            return "runtime unavailable"
        if not state.composer.text.strip():
            return "answer draft is empty"
    if command_id == TerminalCommandId.INTERRUPT:
        if state.header.mode not in {
            TerminalMode.THINKING,
            TerminalMode.RUNNING_TOOL,
            TerminalMode.AWAITING_APPROVAL,
            TerminalMode.AWAITING_ANSWER,
        }:
            return "no active turn"
    if command_id == TerminalCommandId.CLEAR_TRANSCRIPT:
        if not state.messages and not state.turns and state.failure is None:
            return "transcript is empty"
    return None


__all__ = ["disabled_reason_for_command", "item_for_spec"]
