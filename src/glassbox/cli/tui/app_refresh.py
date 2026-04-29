"""Widget refresh helpers for the terminal app."""

from typing import Any

from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.widgets import ActionFeedback
from glassbox.cli.tui.widgets import ActionStripPlaceholder
from glassbox.cli.tui.widgets import CommandPaletteWidget
from glassbox.cli.tui.widgets import ComposerFeedbackLine
from glassbox.cli.tui.widgets import ComposerSubmissionFeedback
from glassbox.cli.tui.widgets import ComposerWidget
from glassbox.cli.tui.widgets import ConversationPane
from glassbox.cli.tui.widgets import DetailsPane
from glassbox.cli.tui.widgets import SessionHeader


def refresh_conversation_widgets(app: Any, state: TerminalConversationState) -> None:
    app.query_one(SessionHeader).update_state(state)
    app.query_one(ConversationPane).update_state(
        state,
        render_markdown=app._transcript_markdown_enabled,
    )
    app.query_one(ActionStripPlaceholder).update_state(
        state,
        app._action_feedback,
    )
    app.query_one(ComposerWidget).update_state(
        state,
        app.launch_options,
    )
    app.query_one(ComposerFeedbackLine).update_feedback(app._composer_feedback)
    app.query_one(DetailsPane).update_state(state)
    app.query_one(CommandPaletteWidget).update_state(state)


def set_composer_feedback(
    app: Any,
    feedback: ComposerSubmissionFeedback | None,
) -> None:
    app._composer_feedback = feedback
    if app.is_mounted:
        app.query_one(ComposerFeedbackLine).update_feedback(feedback)


def set_action_feedback(app: Any, feedback: ActionFeedback | None) -> None:
    app._action_feedback = feedback
    if app.is_mounted:
        app.query_one(ActionStripPlaceholder).update_state(
            app.state,
            feedback,
        )
