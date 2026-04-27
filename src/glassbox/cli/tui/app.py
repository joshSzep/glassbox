"""Textual app shell for the v5 terminal client."""

from typing import ClassVar

from textual.app import App
from textual.app import ComposeResult
from textual.binding import Binding

from glassbox.cli.interactive_client import InteractiveSessionClient
from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.client import TerminalClientAdapter
from glassbox.cli.tui.keybindings import TUI_KEY_BINDINGS
from glassbox.cli.tui.state import TerminalAppState
from glassbox.cli.tui.theme import GLASSBOX_TUI_CSS
from glassbox.cli.tui.widgets import ComposerPlaceholder
from glassbox.cli.tui.widgets import ConversationPane
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
        self.state = TerminalAppState.from_snapshot(
            initial_snapshot,
            launch_options=launch_options,
            dashboard_url=dashboard_url,
        )
        self._client_closed = False

    def compose(self) -> ComposeResult:
        yield SessionHeader(self.state)
        yield ConversationPane(self.state)
        yield ComposerPlaceholder(self.state)

    async def close_client(self) -> None:
        if self._client_closed:
            return
        self._client_closed = True
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
