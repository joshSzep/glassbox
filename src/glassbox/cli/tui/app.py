"""Textual app shell for the v5 terminal client."""

import asyncio
from contextlib import suppress
from typing import ClassVar

from textual.app import App
from textual.app import ComposeResult
from textual.binding import Binding

from glassbox.cli.interactive_client import InteractiveSessionClient
from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.client import TerminalClientAdapter
from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import apply_event
from glassbox.cli.tui.conversation import conversation_state_from_snapshot
from glassbox.cli.tui.conversation import with_stream_status
from glassbox.cli.tui.keybindings import TUI_KEY_BINDINGS
from glassbox.cli.tui.state import session_dashboard_url
from glassbox.cli.tui.theme import GLASSBOX_TUI_CSS
from glassbox.cli.tui.widgets import ActionStripPlaceholder
from glassbox.cli.tui.widgets import ComposerPlaceholder
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

    def compose(self) -> ComposeResult:
        yield SessionHeader(self.state)
        yield ConversationPane(self.state)
        yield ActionStripPlaceholder(self.state)
        yield ComposerPlaceholder(self.state, self.launch_options)
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
        self.query_one(ComposerPlaceholder).update_state(
            state,
            self.launch_options,
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
