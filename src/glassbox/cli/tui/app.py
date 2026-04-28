"""Textual app shell for the v5 terminal client."""

import asyncio
from contextlib import suppress
from pathlib import Path
from typing import ClassVar

from textual.app import App
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import TextArea

from glassbox.cli.interactive_client import InteractiveClientError
from glassbox.cli.interactive_client import InteractiveClientErrorKind
from glassbox.cli.interactive_client import InteractiveSessionClient
from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.client import TerminalClientAdapter
from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.commands import command_from_slash
from glassbox.cli.tui.commands import command_item_by_id
from glassbox.cli.tui.commands import command_items_for_state
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import apply_event
from glassbox.cli.tui.conversation import conversation_state_from_snapshot
from glassbox.cli.tui.conversation import latest_artifact_path_from_state
from glassbox.cli.tui.conversation import with_composer_draft
from glassbox.cli.tui.conversation import with_stream_status
from glassbox.cli.tui.keybindings import TUI_KEY_BINDINGS
from glassbox.cli.tui.state import session_dashboard_url
from glassbox.cli.tui.theme import GLASSBOX_TUI_CSS
from glassbox.cli.tui.widgets import ActionFeedback
from glassbox.cli.tui.widgets import ActionFeedbackStatus
from glassbox.cli.tui.widgets import ActionStripPlaceholder
from glassbox.cli.tui.widgets import CommandPaletteWidget
from glassbox.cli.tui.widgets import ComposerAvailability
from glassbox.cli.tui.widgets import ComposerFeedbackLine
from glassbox.cli.tui.widgets import ComposerSubmissionFeedback
from glassbox.cli.tui.widgets import ComposerSubmissionStatus
from glassbox.cli.tui.widgets import ComposerWidget
from glassbox.cli.tui.widgets import ConversationPane
from glassbox.cli.tui.widgets import DetailsPane
from glassbox.cli.tui.widgets import FooterHelp
from glassbox.cli.tui.widgets import SessionHeader
from glassbox.cli.tui.widgets import composer_availability
from glassbox.core.types import ApprovalDecision

STREAM_RECONNECT_RETRY_COUNT = 3
STREAM_RECONNECT_RETRY_DELAYS_SECONDS = (0.0, 0.0, 0.0)


class GlassboxTerminalApp(App[None]):
    """Minimal full-screen terminal app boundary for future TUI work."""

    CSS = GLASSBOX_TUI_CSS
    BINDINGS: ClassVar[list[Binding]] = TUI_KEY_BINDINGS

    def __init__(
        self,
        *,
        client: InteractiveSessionClient,
        initial_snapshot: InteractiveSessionSnapshot,
        launch_options: InteractiveLaunchOptions,
        dashboard_url: str | None = None,
    ) -> None:
        super().__init__()
        self.client_adapter = TerminalClientAdapter(client)
        self.launch_options = launch_options
        self.state = conversation_state_from_snapshot(initial_snapshot)
        if dashboard_url is not None:
            self.state = self.state.with_dashboard_url(
                session_dashboard_url(dashboard_url, initial_snapshot.session_id)
            )
        self._stream_task: asyncio.Task[None] | None = None
        self._client_closed = False
        self._prompt_history: list[str] = []
        self._prompt_history_index: int | None = None
        self._focused_before_palette = None
        self._details_visible = False
        self._transcript_markdown_enabled = True
        self._composer_feedback: ComposerSubmissionFeedback | None = None
        self._action_feedback: ActionFeedback | None = None
        self._quit_confirmation_pending = False

    def compose(self) -> ComposeResult:
        yield SessionHeader(self.state)
        yield ConversationPane(self.state)
        yield ActionStripPlaceholder(self.state, self._action_feedback)
        yield ComposerWidget(self.state, self.launch_options)
        yield ComposerFeedbackLine(self._composer_feedback)
        yield FooterHelp()
        yield DetailsPane(self.state)
        yield CommandPaletteWidget(self.state)

    def on_mount(self) -> None:
        self.set_focus(self.query_one(ComposerWidget))
        self._stream_task = asyncio.create_task(self._consume_live_events())

    async def _consume_live_events(self) -> None:
        reconnect_attempts = 0
        while True:
            try:
                async for event in self.client_adapter.stream_events(
                    after_sequence=self.state.header.last_sequence,
                ):
                    self.apply_runtime_event(event)
                if reconnect_attempts > 0:
                    self.update_conversation_state(
                        with_stream_status(
                            self.state,
                            TerminalStreamStatus.LIVE,
                            detail="reconnected",
                        )
                    )
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                reconnect_attempts += 1
                if reconnect_attempts > STREAM_RECONNECT_RETRY_COUNT:
                    self.update_conversation_state(
                        with_stream_status(
                            self.state,
                            TerminalStreamStatus.UNAVAILABLE,
                            detail=(
                                "stream unavailable after "
                                f"{STREAM_RECONNECT_RETRY_COUNT} retries: {exc}"
                            ),
                        )
                    )
                    return
                self.update_conversation_state(
                    with_stream_status(
                        self.state,
                        TerminalStreamStatus.RECONNECTING,
                        detail=(
                            f"retry {reconnect_attempts}/"
                            f"{STREAM_RECONNECT_RETRY_COUNT}: {exc}"
                        ),
                    )
                )
                delay = STREAM_RECONNECT_RETRY_DELAYS_SECONDS[
                    min(
                        reconnect_attempts - 1,
                        len(STREAM_RECONNECT_RETRY_DELAYS_SECONDS) - 1,
                    )
                ]
                if delay > 0:
                    await asyncio.sleep(delay)

    def apply_runtime_event(self, event) -> None:
        self.update_conversation_state(apply_event(self.state, event))

    def update_conversation_state(self, state: TerminalConversationState) -> None:
        self.state = state
        if not self.is_mounted:
            return
        self.query_one(SessionHeader).update_state(state)
        self.query_one(ConversationPane).update_state(
            state,
            render_markdown=self._transcript_markdown_enabled,
        )
        self.query_one(ActionStripPlaceholder).update_state(
            state,
            self._action_feedback,
        )
        self.query_one(ComposerWidget).update_state(
            state,
            self.launch_options,
        )
        self.query_one(ComposerFeedbackLine).update_feedback(self._composer_feedback)
        self.query_one(DetailsPane).update_state(state)
        self.query_one(CommandPaletteWidget).update_state(state)

    def action_latest(self) -> None:
        self.query_one(ConversationPane).jump_to_latest()
        self._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.ACCEPTED,
                "Showing latest transcript output.",
            )
        )

    def action_focus_composer(self) -> None:
        self.set_focus(self.query_one(ComposerWidget))

    def action_focus_transcript(self) -> None:
        self.set_focus(self.query_one(ConversationPane))

    def action_focus_actions(self) -> None:
        self.set_focus(self.query_one(ActionStripPlaceholder))

    def action_transcript_page_up(self) -> None:
        self.query_one(ConversationPane).page_up()

    def action_transcript_page_down(self) -> None:
        self.query_one(ConversationPane).page_down()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if not isinstance(event.text_area, ComposerWidget):
            return
        if event.text_area.is_syncing_state:
            return
        self._prompt_history_index = None
        if (
            self._composer_feedback is not None
            and event.text_area.text != self.state.composer.text
        ):
            self._set_composer_feedback(None)
        if (
            self._action_feedback is not None
            and event.text_area.text != self.state.composer.text
        ):
            self._set_action_feedback(None)
        question_id = None
        if (
            self.state.pending_question is not None
            and self.state.pending_question.answer is None
        ):
            question_id = self.state.pending_question.question_id
        self.update_conversation_state(
            with_composer_draft(
                self.state,
                event.text_area.text,
                question_id=question_id,
            )
        )

    async def action_submit_prompt(self) -> None:
        composer = self.query_one(ComposerWidget)
        text = composer.text
        command_id = command_from_slash(text)
        if command_id is not None:
            await self.execute_terminal_command(command_id)
            return
        availability = composer_availability(self.state)
        if self._is_prompt_submit_pending():
            return
        if not text.strip():
            self._set_composer_feedback(
                ComposerSubmissionFeedback(
                    ComposerSubmissionStatus.VALIDATION_ERROR,
                    "Write a prompt before sending.",
                )
            )
            composer.show_submit_blocked()
            return
        if not composer.can_submit:
            self._set_composer_feedback(_feedback_for_blocked_submit(availability))
            composer.show_submit_blocked()
            return
        self._set_composer_feedback(
            ComposerSubmissionFeedback(
                ComposerSubmissionStatus.PENDING,
                "Waiting for the runtime to accept the prompt.",
            )
        )
        self.update_conversation_state(with_composer_draft(self.state, ""))
        try:
            await self.client_adapter.submit_message(text)
        except InteractiveClientError as exc:
            self.update_conversation_state(with_composer_draft(self.state, text))
            self._set_composer_feedback(_feedback_for_client_error(exc))
            return
        except Exception as exc:
            self.update_conversation_state(with_composer_draft(self.state, text))
            self._set_composer_feedback(
                ComposerSubmissionFeedback(
                    ComposerSubmissionStatus.RETRYABLE_FAILURE,
                    str(exc) or "The prompt was not accepted.",
                    retryable=True,
                )
            )
            return
        self._record_prompt_history(text)
        self._set_composer_feedback(
            ComposerSubmissionFeedback(
                ComposerSubmissionStatus.ACCEPTED,
                "Prompt accepted. Waiting for session events.",
            )
        )

    def action_command_palette(self) -> None:
        self.open_command_palette()

    def open_command_palette(self) -> None:
        self._focused_before_palette = self.focused
        self.query_one(CommandPaletteWidget).open()

    def close_command_palette(self, *, restore_focus: bool = False) -> None:
        self.query_one(CommandPaletteWidget).close()
        if restore_focus and self._focused_before_palette is not None:
            self.set_focus(self._focused_before_palette)
        self._focused_before_palette = None

    async def execute_terminal_command(self, command_id: TerminalCommandId) -> None:
        if command_id == TerminalCommandId.INTERRUPT:
            self.close_command_palette(restore_focus=True)
            self._handle_interrupt_request()
            return
        if command_id == TerminalCommandId.SUBMIT_ANSWER:
            self.close_command_palette(restore_focus=True)
            await self._submit_pending_answer()
            return
        if command_id == TerminalCommandId.APPROVE:
            self.close_command_palette(restore_focus=True)
            await self._resolve_pending_approval(ApprovalDecision.APPROVED)
            return
        if command_id == TerminalCommandId.DENY:
            self.close_command_palette(restore_focus=True)
            await self._resolve_pending_approval(ApprovalDecision.DENIED)
            return
        item = command_item_by_id(command_items_for_state(self.state), command_id)
        if item is not None and not item.enabled:
            return
        self.close_command_palette(restore_focus=True)
        if command_id == TerminalCommandId.STATUS:
            return
        if command_id == TerminalCommandId.OPEN_DASHBOARD:
            self._open_dashboard()
            return
        if command_id == TerminalCommandId.COPY_SESSION_ID:
            self._copy_handoff_value(
                str(self.state.header.session_id),
                success_message="Session ID copied.",
            )
            return
        if command_id == TerminalCommandId.COPY_DASHBOARD_URL:
            self._copy_dashboard_url()
            return
        if command_id == TerminalCommandId.COPY_ARTIFACT_PATH:
            self._copy_latest_artifact_path()
            return
        if command_id == TerminalCommandId.OPEN_ARTIFACT_PATH:
            self._open_latest_artifact_path()
            return
        if command_id == TerminalCommandId.TOGGLE_DETAILS:
            self._details_visible = not self._details_visible
            details = self.query_one(DetailsPane)
            details.toggle()
            if details.display:
                self.set_focus(details)
            return
        if command_id == TerminalCommandId.TOGGLE_MARKDOWN:
            self._transcript_markdown_enabled = not self._transcript_markdown_enabled
            self.query_one(ConversationPane).update_state(
                self.state,
                render_markdown=self._transcript_markdown_enabled,
            )
            state_label = "enabled" if self._transcript_markdown_enabled else "disabled"
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.ACCEPTED,
                    f"Markdown rendering {state_label}.",
                )
            )
            return
        if command_id == TerminalCommandId.JUMP_LATEST:
            self.action_latest()
            return
        if command_id == TerminalCommandId.CLEAR_TRANSCRIPT:
            self.query_one(ConversationPane).show_local_message(
                "Transcript hidden locally."
            )
            return
        if command_id == TerminalCommandId.QUIT:
            self._handle_quit_request()

    async def action_toggle_details(self) -> None:
        await self.execute_terminal_command(TerminalCommandId.TOGGLE_DETAILS)

    async def action_open_dashboard(self) -> None:
        await self.execute_terminal_command(TerminalCommandId.OPEN_DASHBOARD)

    async def action_copy_dashboard_url(self) -> None:
        await self.execute_terminal_command(TerminalCommandId.COPY_DASHBOARD_URL)

    async def action_approve(self) -> None:
        await self.execute_terminal_command(TerminalCommandId.APPROVE)

    async def action_deny(self) -> None:
        await self.execute_terminal_command(TerminalCommandId.DENY)

    async def action_submit_answer(self) -> None:
        await self.execute_terminal_command(TerminalCommandId.SUBMIT_ANSWER)

    async def action_interrupt(self) -> None:
        await self.execute_terminal_command(TerminalCommandId.INTERRUPT)

    async def action_quit(self) -> None:
        self._handle_quit_request()

    def action_cancel_transient(self) -> None:
        if self.query_one(CommandPaletteWidget).display:
            self.close_command_palette(restore_focus=True)
            return
        details = self.query_one(DetailsPane)
        if details.display:
            self._details_visible = False
            details.display = False
            self.query_one(ComposerWidget).focus()
            return
        if self._quit_confirmation_pending:
            self._quit_confirmation_pending = False
            self._set_action_feedback(
                ActionFeedback(ActionFeedbackStatus.CONFLICT, "Quit cancelled.")
            )
            return
        self._set_action_feedback(None)

    def action_prompt_history_previous(self) -> None:
        if not self._prompt_history:
            return
        if self._prompt_history_index is None:
            self._prompt_history_index = len(self._prompt_history) - 1
        else:
            self._prompt_history_index = max(self._prompt_history_index - 1, 0)
        self._load_prompt_history_entry()

    def action_prompt_history_next(self) -> None:
        if self._prompt_history_index is None:
            return
        self._prompt_history_index += 1
        if self._prompt_history_index >= len(self._prompt_history):
            self._prompt_history_index = None
            text = ""
        else:
            text = self._prompt_history[self._prompt_history_index]
        self.update_conversation_state(with_composer_draft(self.state, text))

    def _record_prompt_history(self, text: str) -> None:
        self._prompt_history.append(text)
        self._prompt_history_index = None

    def _load_prompt_history_entry(self) -> None:
        if self._prompt_history_index is None:
            return
        self.update_conversation_state(
            with_composer_draft(
                self.state,
                self._prompt_history[self._prompt_history_index],
            )
        )

    def _set_composer_feedback(
        self,
        feedback: ComposerSubmissionFeedback | None,
    ) -> None:
        self._composer_feedback = feedback
        if self.is_mounted:
            self.query_one(ComposerFeedbackLine).update_feedback(feedback)

    def _set_action_feedback(self, feedback: ActionFeedback | None) -> None:
        self._action_feedback = feedback
        if self.is_mounted:
            self.query_one(ActionStripPlaceholder).update_state(
                self.state,
                feedback,
            )

    def _handle_interrupt_request(self) -> None:
        if self.query_one(CommandPaletteWidget).display:
            self.close_command_palette(restore_focus=True)
            return
        details = self.query_one(DetailsPane)
        if details.display:
            self._details_visible = False
            details.display = False
            self.query_one(ComposerWidget).focus()
            return
        self._quit_confirmation_pending = False
        if self.state.pending_approval is not None:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    "Resolve or deny the pending approval; no interrupt was sent.",
                )
            )
            return
        if self.state.pending_question is not None:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    "Answer the pending question; no interrupt was sent.",
                )
            )
            return
        if self.state.header.stream_status in {
            TerminalStreamStatus.RECONNECTING,
            TerminalStreamStatus.UNAVAILABLE,
        }:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.UNAVAILABLE_RUNTIME,
                    "Runtime is not writable; no interrupt was sent.",
                    retryable=True,
                )
            )
            return
        if self.state.header.current_turn_id is not None or self.state.header.mode in {
            TerminalMode.THINKING,
            TerminalMode.RUNNING_TOOL,
        }:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    "Runtime turn interruption is not supported yet; "
                    "session continues.",
                )
            )
            return
        self._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.CONFLICT,
                "No active runtime action to interrupt.",
            )
        )

    def _handle_quit_request(self) -> None:
        if self._quit_confirmation_pending or not self._quit_requires_confirmation():
            self.exit()
            return
        self._quit_confirmation_pending = True
        self._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.CONFLICT,
                "Press Ctrl+Escape again to leave; the session will keep running.",
            )
        )

    def _quit_requires_confirmation(self) -> bool:
        return (
            self.state.header.current_turn_id is not None
            or self.state.pending_approval is not None
            or self.state.pending_question is not None
            or self.state.header.stream_status == TerminalStreamStatus.RECONNECTING
            or self.state.header.mode
            in {
                TerminalMode.THINKING,
                TerminalMode.RUNNING_TOOL,
                TerminalMode.AWAITING_APPROVAL,
                TerminalMode.AWAITING_ANSWER,
            }
        )

    def _is_prompt_submit_pending(self) -> bool:
        return (
            self._composer_feedback is not None
            and self._composer_feedback.status == ComposerSubmissionStatus.PENDING
        )

    async def _submit_pending_answer(self) -> None:
        question = self.state.pending_question
        if question is None or question.answer is not None:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    "No pending question needs an answer.",
                )
            )
            return
        if self.state.header.stream_status in {
            TerminalStreamStatus.RECONNECTING,
            TerminalStreamStatus.UNAVAILABLE,
            TerminalStreamStatus.HISTORICAL_ONLY,
        }:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.UNAVAILABLE_RUNTIME,
                    self.state.header.stream_detail or "Runtime is not writable.",
                    retryable=True,
                )
            )
            return
        answer = self.query_one(ComposerWidget).text
        if not answer.strip():
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.VALIDATION_ERROR,
                    "Write an answer in the composer before submitting.",
                )
            )
            return
        self._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.PENDING,
                "Submitting answer to the runtime.",
            )
        )
        try:
            await self.client_adapter.submit_answer(question.question_id, answer)
        except InteractiveClientError as exc:
            self._set_action_feedback(_action_feedback_for_client_error(exc))
            return
        except Exception as exc:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.RETRYABLE_FAILURE,
                    str(exc) or "The answer was not accepted.",
                    retryable=True,
                )
            )
            return
        self._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.ACCEPTED,
                "Answer accepted. Waiting for session events.",
            )
        )
        self.update_conversation_state(with_composer_draft(self.state, ""))

    async def _resolve_pending_approval(
        self,
        decision: ApprovalDecision,
    ) -> None:
        approval = self.state.pending_approval
        if approval is None:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    "No pending approval needs a decision.",
                )
            )
            return
        if approval.decision is not None:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.ALREADY_RESOLVED,
                    "Approval already resolved by session events.",
                )
            )
            return
        if self.state.header.stream_status in {
            TerminalStreamStatus.RECONNECTING,
            TerminalStreamStatus.UNAVAILABLE,
            TerminalStreamStatus.HISTORICAL_ONLY,
        }:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.UNAVAILABLE_RUNTIME,
                    self.state.header.stream_detail or "Runtime is not writable.",
                    retryable=True,
                )
            )
            return
        label = "approval" if decision == ApprovalDecision.APPROVED else "denial"
        self._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.PENDING,
                f"Submitting {label} to the runtime.",
            )
        )
        try:
            await self.client_adapter.resolve_approval(approval.approval_id, decision)
        except InteractiveClientError as exc:
            self._set_action_feedback(_action_feedback_for_client_error(exc))
            return
        except Exception as exc:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.RETRYABLE_FAILURE,
                    str(exc) or "The approval decision was not accepted.",
                    retryable=True,
                )
            )
            return
        self._set_action_feedback(
            ActionFeedback(
                ActionFeedbackStatus.ACCEPTED,
                f"{label.title()} accepted. Waiting for session events.",
            )
        )

    def _open_dashboard(self) -> None:
        url = self.state.header.dashboard_url
        if url is None:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    "Dashboard URL is unavailable.",
                )
            )
            return
        try:
            self.open_url(url)
        except Exception as exc:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.RETRYABLE_FAILURE,
                    str(exc) or "Dashboard did not open.",
                    retryable=True,
                )
            )
            return
        self._set_action_feedback(
            ActionFeedback(ActionFeedbackStatus.ACCEPTED, "Dashboard opened.")
        )

    def _copy_dashboard_url(self) -> None:
        url = self.state.header.dashboard_url
        if url is None:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    "Dashboard URL is unavailable.",
                )
            )
            return
        self._copy_handoff_value(url, success_message="Dashboard URL copied.")

    def _copy_latest_artifact_path(self) -> None:
        path = latest_artifact_path_from_state(self.state)
        if path is None:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    "No artifact path is available yet.",
                )
            )
            return
        self._copy_handoff_value(path, success_message="Artifact path copied.")

    def _open_latest_artifact_path(self) -> None:
        raw_path = latest_artifact_path_from_state(self.state)
        if raw_path is None:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    "No artifact path is available yet.",
                )
            )
            return
        path = _local_artifact_path(raw_path, self.state.header.cwd)
        if not path.exists():
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.CONFLICT,
                    f"Artifact path is missing: {raw_path}",
                )
            )
            return
        try:
            self.open_url(path.as_uri())
        except Exception as exc:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.RETRYABLE_FAILURE,
                    str(exc) or "Artifact did not open.",
                    retryable=True,
                )
            )
            return
        self._set_action_feedback(
            ActionFeedback(ActionFeedbackStatus.ACCEPTED, "Artifact opened.")
        )

    def _copy_handoff_value(self, value: str, *, success_message: str) -> None:
        try:
            self.copy_to_clipboard(value)
        except Exception as exc:
            self._set_action_feedback(
                ActionFeedback(
                    ActionFeedbackStatus.RETRYABLE_FAILURE,
                    str(exc) or "Copy failed.",
                    retryable=True,
                )
            )
            return
        self._set_action_feedback(
            ActionFeedback(ActionFeedbackStatus.ACCEPTED, success_message)
        )

    async def close_client(self) -> None:
        if self._client_closed:
            return
        self._client_closed = True
        if self._stream_task is not None:
            self._stream_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._stream_task
        await self.client_adapter.close()


def create_tui_app(
    *,
    client: InteractiveSessionClient,
    initial_snapshot: InteractiveSessionSnapshot,
    launch_options: InteractiveLaunchOptions,
    dashboard_url: str | None = None,
) -> GlassboxTerminalApp:
    return GlassboxTerminalApp(
        client=client,
        initial_snapshot=initial_snapshot,
        launch_options=launch_options,
        dashboard_url=dashboard_url,
    )


async def run_tui_app(app: GlassboxTerminalApp) -> None:
    try:
        await app.run_async()
    finally:
        await app.close_client()


def _feedback_for_blocked_submit(
    availability: ComposerAvailability,
) -> ComposerSubmissionFeedback:
    if availability.disabled_reason in {
        "runtime reconnecting",
        "runtime stream unavailable",
    }:
        return ComposerSubmissionFeedback(
            ComposerSubmissionStatus.UNAVAILABLE_RUNTIME,
            availability.placeholder,
            retryable=True,
        )
    return ComposerSubmissionFeedback(
        ComposerSubmissionStatus.CONFLICT,
        availability.placeholder,
    )


def _feedback_for_client_error(
    error: InteractiveClientError,
) -> ComposerSubmissionFeedback:
    if error.kind == InteractiveClientErrorKind.CONFLICT:
        return ComposerSubmissionFeedback(ComposerSubmissionStatus.CONFLICT, str(error))
    if error.kind == InteractiveClientErrorKind.VALIDATION_ERROR:
        return ComposerSubmissionFeedback(
            ComposerSubmissionStatus.VALIDATION_ERROR,
            str(error),
        )
    if error.kind in {
        InteractiveClientErrorKind.RUNTIME_UNAVAILABLE,
        InteractiveClientErrorKind.STREAM_UNAVAILABLE,
    }:
        return ComposerSubmissionFeedback(
            ComposerSubmissionStatus.NETWORK_ERROR,
            str(error),
            retryable=True,
        )
    if error.kind in {
        InteractiveClientErrorKind.UNKNOWN_SESSION,
        InteractiveClientErrorKind.HISTORICAL_ONLY,
    }:
        return ComposerSubmissionFeedback(ComposerSubmissionStatus.CONFLICT, str(error))
    return ComposerSubmissionFeedback(
        ComposerSubmissionStatus.RETRYABLE_FAILURE,
        str(error),
        retryable=True,
    )


def _action_feedback_for_client_error(
    error: InteractiveClientError,
) -> ActionFeedback:
    if error.kind == InteractiveClientErrorKind.CONFLICT:
        return ActionFeedback(ActionFeedbackStatus.CONFLICT, str(error))
    if error.kind == InteractiveClientErrorKind.VALIDATION_ERROR:
        return ActionFeedback(ActionFeedbackStatus.VALIDATION_ERROR, str(error))
    if error.kind in {
        InteractiveClientErrorKind.RUNTIME_UNAVAILABLE,
        InteractiveClientErrorKind.STREAM_UNAVAILABLE,
    }:
        return ActionFeedback(
            ActionFeedbackStatus.NETWORK_ERROR,
            str(error),
            retryable=True,
        )
    if error.kind in {
        InteractiveClientErrorKind.UNKNOWN_SESSION,
        InteractiveClientErrorKind.HISTORICAL_ONLY,
    }:
        return ActionFeedback(ActionFeedbackStatus.CONFLICT, str(error))
    return ActionFeedback(
        ActionFeedbackStatus.RETRYABLE_FAILURE,
        str(error),
        retryable=True,
    )


def _local_artifact_path(raw_path: str, cwd: str | None) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    if cwd is not None:
        return Path(cwd).expanduser() / path
    return path.absolute()
