"""Composer widgets and render helpers for the terminal UI."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from typing import ClassVar
from typing import cast

from textual.binding import Binding
from textual.widgets import Static
from textual.widgets import TextArea

from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.conversation import TerminalActionKind
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import terminal_action_from_state


@dataclass(frozen=True, slots=True)
class ComposerAvailability:
    can_edit: bool
    can_submit: bool
    placeholder: str
    disabled_reason: str | None = None


class ComposerSubmissionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    UNAVAILABLE_RUNTIME = "unavailable_runtime"
    RETRYABLE_FAILURE = "retryable_failure"


@dataclass(frozen=True, slots=True)
class ComposerSubmissionFeedback:
    status: ComposerSubmissionStatus
    message: str
    retryable: bool = False


class ComposerWidget(TextArea):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("enter", "submit_prompt", "Send", show=False),
        Binding("ctrl+enter", "insert_newline", "New line", show=False),
        Binding("ctrl+s", "submit_prompt", "Send", show=False),
        Binding("ctrl+up", "prompt_history_previous", "Previous prompt", show=False),
        Binding("ctrl+down", "prompt_history_next", "Next prompt", show=False),
    ]

    def __init__(
        self,
        state: TerminalConversationState,
        launch_options: InteractiveLaunchOptions,
    ) -> None:
        self._state = state
        self._launch_options = launch_options
        self._syncing_state = False
        availability = composer_availability(state)
        super().__init__(
            text=state.composer.text,
            id="composer",
            placeholder=availability.placeholder,
            soft_wrap=True,
            show_line_numbers=False,
        )
        self.update_state(state, launch_options)

    @property
    def is_syncing_state(self) -> bool:
        return self._syncing_state

    @property
    def can_submit(self) -> bool:
        return composer_availability(self._state).can_submit

    def update_state(
        self,
        state: TerminalConversationState,
        launch_options: InteractiveLaunchOptions,
    ) -> None:
        self._state = state
        self._launch_options = launch_options
        availability = composer_availability(state)
        self.read_only = not availability.can_edit
        self.placeholder = availability.placeholder
        self.tooltip = availability.disabled_reason
        self.styles.height = composer_height_for_state(state)
        if self.text != state.composer.text:
            self._syncing_state = True
            try:
                self.text = state.composer.text
            finally:
                self._syncing_state = False

    async def on_key(self, event) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            await self.action_submit_prompt()
        elif event.key == "ctrl+enter":
            event.prevent_default()
            event.stop()
            self.action_insert_newline()

    def show_submit_blocked(self) -> None:
        self.placeholder = composer_availability(self._state).placeholder

    async def action_submit_prompt(self) -> None:
        await cast(Any, self.app).action_submit_prompt()

    def action_insert_newline(self) -> None:
        self.insert("\n")

    def action_prompt_history_previous(self) -> None:
        cast(Any, self.app).action_prompt_history_previous()

    def action_prompt_history_next(self) -> None:
        cast(Any, self.app).action_prompt_history_next()


class ComposerFeedbackLine(Static):
    def __init__(self, feedback: ComposerSubmissionFeedback | None = None) -> None:
        self._feedback = feedback
        super().__init__(render_composer_feedback(feedback), id="composer-feedback")

    def update_feedback(self, feedback: ComposerSubmissionFeedback | None) -> None:
        self._feedback = feedback
        self.update(render_composer_feedback(feedback))


def composer_availability(state: TerminalConversationState) -> ComposerAvailability:
    if state.header.mode == TerminalMode.HISTORICAL_ONLY:
        return ComposerAvailability(
            can_edit=False,
            can_submit=False,
            placeholder="Session is historical; start or attach to a running session.",
            disabled_reason="historical session",
        )
    if state.header.stream_status == TerminalStreamStatus.RECONNECTING:
        return ComposerAvailability(
            can_edit=False,
            can_submit=False,
            placeholder="Reconnecting to the runtime...",
            disabled_reason="runtime reconnecting",
        )
    if state.header.stream_status == TerminalStreamStatus.UNAVAILABLE:
        return ComposerAvailability(
            can_edit=False,
            can_submit=False,
            placeholder="Runtime stream unavailable; reconnect before sending.",
            disabled_reason="runtime stream unavailable",
        )
    if state.pending_approval is not None:
        return ComposerAvailability(
            can_edit=True,
            can_submit=False,
            placeholder="Use Alt+A/Alt+X or type /approve or /deny.",
            disabled_reason="pending approval",
        )
    if state.pending_question is not None:
        return ComposerAvailability(
            can_edit=True,
            can_submit=False,
            placeholder="Answer the pending question from the action strip.",
            disabled_reason="pending question",
        )
    if state.header.mode in {TerminalMode.THINKING, TerminalMode.RUNNING_TOOL}:
        return ComposerAvailability(
            can_edit=True,
            can_submit=False,
            placeholder="Agent is working; draft your next prompt here.",
            disabled_reason="active turn",
        )
    if state.header.mode == TerminalMode.FAILED:
        return ComposerAvailability(
            can_edit=False,
            can_submit=False,
            placeholder="Session failed; inspect details before sending.",
            disabled_reason="failed session",
        )
    return ComposerAvailability(
        can_edit=True,
        can_submit=True,
        placeholder="Write a prompt. Enter sends; Ctrl+Enter adds a line.",
    )


def render_composer_feedback(
    feedback: ComposerSubmissionFeedback | None,
) -> str:
    if feedback is None:
        return ""
    prefix = {
        ComposerSubmissionStatus.PENDING: "Sending",
        ComposerSubmissionStatus.ACCEPTED: "Accepted",
        ComposerSubmissionStatus.CONFLICT: "Not sent",
        ComposerSubmissionStatus.VALIDATION_ERROR: "Check prompt",
        ComposerSubmissionStatus.NETWORK_ERROR: "Network error",
        ComposerSubmissionStatus.UNAVAILABLE_RUNTIME: "Runtime unavailable",
        ComposerSubmissionStatus.RETRYABLE_FAILURE: "Send failed",
    }[feedback.status]
    suffix = " Retry is safe." if feedback.retryable else ""
    return f"{prefix}: {feedback.message}{suffix}"


def composer_height_for_state(state: TerminalConversationState) -> int:
    if terminal_action_from_state(state).kind == TerminalActionKind.PROMPT:
        return 8
    return 3
