"""Textual app shell for the v5 terminal client."""

import asyncio
from contextlib import suppress
from typing import ClassVar

from textual.app import App
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import TextArea

from glassbox.cli.interactive_client import InteractiveSessionClient
from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.client import TerminalClientAdapter
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import apply_event
from glassbox.cli.tui.conversation import conversation_state_from_snapshot
from glassbox.cli.tui.conversation import with_composer_draft
from glassbox.cli.tui.conversation import with_stream_status
from glassbox.cli.tui.keybindings import TUI_KEY_BINDINGS
from glassbox.cli.tui.state import session_dashboard_url
from glassbox.cli.tui.theme import GLASSBOX_TUI_CSS
from glassbox.cli.tui.widgets import ActionStripPlaceholder
from glassbox.cli.tui.widgets import ComposerWidget
from glassbox.cli.tui.widgets import ConversationPane
from glassbox.cli.tui.widgets import FooterHelp
from glassbox.cli.tui.widgets import SessionHeader


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

    def compose(self) -> ComposeResult:
        yield SessionHeader(self.state)
        yield ConversationPane(self.state)
        yield ActionStripPlaceholder(self.state)
        yield ComposerWidget(self.state, self.launch_options)
        yield FooterHelp()

    def on_mount(self) -> None:
        self._stream_task = asyncio.create_task(self._consume_live_events())

    async def _consume_live_events(self) -> None:
        try:
            async for event in self.client_adapter.stream_events(
                after_sequence=self.state.header.last_sequence,
            ):
                self.apply_runtime_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.update_conversation_state(
                with_stream_status(
                    self.state,
                    TerminalStreamStatus.UNAVAILABLE,
                    detail=str(exc),
                )
            )

    def apply_runtime_event(self, event) -> None:
        self.update_conversation_state(apply_event(self.state, event))

    def update_conversation_state(self, state: TerminalConversationState) -> None:
        self.state = state
        if not self.is_mounted:
            return
        self.query_one(SessionHeader).update_state(state)
        self.query_one(ConversationPane).update_state(state)
        self.query_one(ActionStripPlaceholder).update_state(state)
        self.query_one(ComposerWidget).update_state(
            state,
            self.launch_options,
        )

    def action_latest(self) -> None:
        self.query_one(ConversationPane).jump_to_latest()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if not isinstance(event.text_area, ComposerWidget):
            return
        if event.text_area.is_syncing_state:
            return
        self._prompt_history_index = None
        self.update_conversation_state(
            with_composer_draft(self.state, event.text_area.text)
        )

    async def action_submit_prompt(self) -> None:
        composer = self.query_one(ComposerWidget)
        text = composer.text
        if not composer.can_submit or not text.strip():
            composer.show_submit_blocked()
            return
        await self.client_adapter.submit_message(text)
        self._record_prompt_history(text)
        self.update_conversation_state(with_composer_draft(self.state, ""))

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
