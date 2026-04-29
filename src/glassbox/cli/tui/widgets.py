"""Compatibility facade for terminal UI widgets."""

from glassbox.cli.tui.widget_action import ActionFeedback
from glassbox.cli.tui.widget_action import ActionFeedbackStatus
from glassbox.cli.tui.widget_action import ActionStripPlaceholder
from glassbox.cli.tui.widget_action import render_action_feedback
from glassbox.cli.tui.widget_action import render_action_strip
from glassbox.cli.tui.widget_composer import ComposerAvailability
from glassbox.cli.tui.widget_composer import ComposerFeedbackLine
from glassbox.cli.tui.widget_composer import ComposerSubmissionFeedback
from glassbox.cli.tui.widget_composer import ComposerSubmissionStatus
from glassbox.cli.tui.widget_composer import ComposerWidget
from glassbox.cli.tui.widget_composer import composer_availability
from glassbox.cli.tui.widget_composer import render_composer_feedback
from glassbox.cli.tui.widget_details import DetailsPane
from glassbox.cli.tui.widget_details import render_details_pane
from glassbox.cli.tui.widget_header import FooterHelp
from glassbox.cli.tui.widget_header import SessionHeader
from glassbox.cli.tui.widget_header import render_footer_help
from glassbox.cli.tui.widget_header import render_session_header
from glassbox.cli.tui.widget_palette import CommandPaletteInput
from glassbox.cli.tui.widget_palette import CommandPaletteWidget
from glassbox.cli.tui.widget_transcript import ConversationPane
from glassbox.cli.tui.widget_transcript import TranscriptRenderBlock
from glassbox.cli.tui.widget_transcript import TranscriptRenderLine
from glassbox.cli.tui.widget_transcript import render_transcript
from glassbox.cli.tui.widget_transcript import render_transcript_blocks
from glassbox.cli.tui.widget_transcript import render_transcript_lines

__all__ = [
    "ActionFeedback",
    "ActionFeedbackStatus",
    "ActionStripPlaceholder",
    "CommandPaletteInput",
    "CommandPaletteWidget",
    "ComposerAvailability",
    "ComposerFeedbackLine",
    "ComposerSubmissionFeedback",
    "ComposerSubmissionStatus",
    "ComposerWidget",
    "ConversationPane",
    "DetailsPane",
    "FooterHelp",
    "SessionHeader",
    "TranscriptRenderBlock",
    "TranscriptRenderLine",
    "composer_availability",
    "render_action_feedback",
    "render_action_strip",
    "render_composer_feedback",
    "render_details_pane",
    "render_footer_help",
    "render_session_header",
    "render_transcript",
    "render_transcript_blocks",
    "render_transcript_lines",
]
