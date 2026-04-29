"""Action strip widget and render helpers for the terminal UI."""

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from textual.widgets import Static

from glassbox.cli.tui.conversation import TerminalActionKind
from glassbox.cli.tui.conversation import TerminalActionState
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import terminal_action_from_state
from glassbox.cli.tui.widget_formatting import enum_or_string_value
from glassbox.cli.tui.widget_formatting import fit_line
from glassbox.cli.tui.widget_formatting import policy_decision_label
from glassbox.cli.tui.widget_formatting import policy_source_label


class ActionFeedbackStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    UNAVAILABLE_RUNTIME = "unavailable_runtime"
    RETRYABLE_FAILURE = "retryable_failure"
    ALREADY_RESOLVED = "already_resolved"


@dataclass(frozen=True, slots=True)
class ActionFeedback:
    status: ActionFeedbackStatus
    message: str
    retryable: bool = False


class ActionStripPlaceholder(Static):
    can_focus: ClassVar[bool] = True

    def __init__(
        self,
        state: TerminalConversationState,
        feedback: ActionFeedback | None = None,
    ) -> None:
        super().__init__(render_action_strip(state, feedback), id="action-strip")
        self.display = should_show_action_strip(state, feedback)

    def update_state(
        self,
        state: TerminalConversationState,
        feedback: ActionFeedback | None = None,
    ) -> None:
        self.display = should_show_action_strip(state, feedback)
        self.update(render_action_strip(state, feedback))


def render_action_strip(
    state: TerminalConversationState,
    feedback: ActionFeedback | None = None,
) -> str:
    action = terminal_action_from_state(state)
    if action.kind == TerminalActionKind.PENDING_QUESTION:
        lines = [
            f"Question: {action.description}",
            _question_answer_line(action.answer_draft, state.composer.text),
            _question_hint_line(action.related_tool_name),
        ]
    elif action.kind == TerminalActionKind.PENDING_APPROVAL:
        lines = [
            f"{_approval_title(action)}: {action.subject or action.description}",
            _approval_context_line(action),
            "Primary: Alt+A approve | Alt+X deny | Ctrl+E policy details",
        ]
    else:
        lines = [f"{action.title}: {action.description}"]
    if feedback is not None:
        lines.append(render_action_feedback(feedback))
    return "\n".join(lines)


def should_show_action_strip(
    state: TerminalConversationState,
    feedback: ActionFeedback | None,
) -> bool:
    if feedback is not None:
        return True
    return terminal_action_from_state(state).kind != TerminalActionKind.PROMPT


def render_action_feedback(feedback: ActionFeedback) -> str:
    prefix = {
        ActionFeedbackStatus.PENDING: "Sending",
        ActionFeedbackStatus.ACCEPTED: "Accepted",
        ActionFeedbackStatus.CONFLICT: "Not sent",
        ActionFeedbackStatus.VALIDATION_ERROR: "Check answer",
        ActionFeedbackStatus.NETWORK_ERROR: "Network error",
        ActionFeedbackStatus.UNAVAILABLE_RUNTIME: "Runtime unavailable",
        ActionFeedbackStatus.RETRYABLE_FAILURE: "Action failed",
        ActionFeedbackStatus.ALREADY_RESOLVED: "Resolved",
    }[feedback.status]
    suffix = " Retry is safe." if feedback.retryable else ""
    return f"{prefix}: {feedback.message}{suffix}"


def _question_answer_line(answer_draft: str | None, composer_text: str) -> str:
    draft = answer_draft if answer_draft is not None else composer_text
    if draft.strip():
        return f"Answer draft: {fit_line(draft.strip(), 72)}"
    return "Answer draft: write in the composer"


def _question_hint_line(related_tool_name: str | None) -> str:
    tool = f" | tool {related_tool_name}" if related_tool_name else ""
    return f"Ctrl+R submit answer{tool}"


def _approval_context_line(action: TerminalActionState) -> str:
    parts: list[str] = []
    if action.policy_outcome is not None:
        parts.append(
            policy_decision_label(action.policy_outcome, action.policy_source_kind)
        )
    if action.reason:
        parts.append(fit_line(action.reason, 34))
    if action.related_tool_name:
        parts.append(f"tool {action.related_tool_name}")
    if action.policy_risk_level is not None:
        parts.append(f"risk {enum_or_string_value(action.policy_risk_level)}")
    source = policy_source_label(action.policy_source_kind, action.policy_source_label)
    if source:
        parts.append(f"source {source}")
    if action.approval_id is not None:
        parts.append(f"id {action.approval_id}")
    return " | ".join(parts) if parts else action.description


def _approval_title(action: TerminalActionState) -> str:
    if action.policy_outcome is not None:
        return policy_decision_label(
            action.policy_outcome,
            action.policy_source_kind,
        ).title()
    return "Approval"
