"""Compatibility facade for terminal conversation state."""

from glassbox.cli.tui.conversation_hydration import conversation_state_from_snapshot
from glassbox.cli.tui.conversation_models import AssistantMessageStatus
from glassbox.cli.tui.conversation_models import ComposerDraftState
from glassbox.cli.tui.conversation_models import ConversationMessage
from glassbox.cli.tui.conversation_models import ConversationMessageKind
from glassbox.cli.tui.conversation_models import ConversationTurn
from glassbox.cli.tui.conversation_models import FailureState
from glassbox.cli.tui.conversation_models import PendingApprovalState
from glassbox.cli.tui.conversation_models import PendingQuestionState
from glassbox.cli.tui.conversation_models import TerminalActionKind
from glassbox.cli.tui.conversation_models import TerminalActionState
from glassbox.cli.tui.conversation_models import TerminalConversationState
from glassbox.cli.tui.conversation_models import TerminalHeaderDisplayState
from glassbox.cli.tui.conversation_models import TerminalHeaderState
from glassbox.cli.tui.conversation_models import TerminalMode
from glassbox.cli.tui.conversation_models import TerminalStreamStatus
from glassbox.cli.tui.conversation_models import ToolActivity
from glassbox.cli.tui.conversation_models import ToolActivityStatus
from glassbox.cli.tui.conversation_reducer import apply_event
from glassbox.cli.tui.conversation_reducer import reduce_events
from glassbox.cli.tui.conversation_selectors import header_display_from_state
from glassbox.cli.tui.conversation_selectors import latest_artifact_path_from_state
from glassbox.cli.tui.conversation_selectors import terminal_action_from_state
from glassbox.cli.tui.conversation_selectors import with_composer_draft
from glassbox.cli.tui.conversation_selectors import with_runtime_owner
from glassbox.cli.tui.conversation_selectors import with_stream_status
from glassbox.cli.tui.conversation_selectors import with_tool_expanded

__all__ = [
    "AssistantMessageStatus",
    "ComposerDraftState",
    "ConversationMessage",
    "ConversationMessageKind",
    "ConversationTurn",
    "FailureState",
    "PendingApprovalState",
    "PendingQuestionState",
    "TerminalActionKind",
    "TerminalActionState",
    "TerminalConversationState",
    "TerminalHeaderDisplayState",
    "TerminalHeaderState",
    "TerminalMode",
    "TerminalStreamStatus",
    "ToolActivity",
    "ToolActivityStatus",
    "apply_event",
    "conversation_state_from_snapshot",
    "header_display_from_state",
    "latest_artifact_path_from_state",
    "reduce_events",
    "terminal_action_from_state",
    "with_composer_draft",
    "with_runtime_owner",
    "with_stream_status",
    "with_tool_expanded",
]
