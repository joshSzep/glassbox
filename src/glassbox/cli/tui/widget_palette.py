"""Command palette widget for the terminal UI."""

from typing import Any
from typing import ClassVar
from typing import cast

from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input
from textual.widgets import Static

from glassbox.cli.tui.commands import TerminalCommandItem
from glassbox.cli.tui.commands import command_items_for_state
from glassbox.cli.tui.commands import filter_command_items
from glassbox.cli.tui.conversation import TerminalConversationState


class CommandPaletteInput(Input):
    async def on_key(self, event) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            await cast(Any, self.parent).execute_selected_command()
        elif event.key == "down":
            event.prevent_default()
            event.stop()
            cast(Any, self.parent).action_command_next()
        elif event.key == "up":
            event.prevent_default()
            event.stop()
            cast(Any, self.parent).action_command_previous()
        elif event.key == "escape":
            event.prevent_default()
            event.stop()
            cast(Any, self.app).close_command_palette(restore_focus=True)


class CommandPaletteWidget(Vertical):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close_palette", "Close", show=False),
        Binding("enter", "execute_selected_command", "Run", show=False),
        Binding("down", "command_next", "Next", show=False),
        Binding("up", "command_previous", "Previous", show=False),
    ]

    def __init__(self, state: TerminalConversationState) -> None:
        self._state = state
        self._items = command_items_for_state(state)
        self._filtered_items = self._items
        self._selected_index = 0
        super().__init__(id="command-palette")
        self.display = False

    def compose(self):
        yield CommandPaletteInput(placeholder="Search commands", id="command-filter")
        yield Static(self._render_items(), id="command-list")

    def open(self) -> None:
        self.display = True
        self.query_one(Input).value = ""
        self._refresh_filter("")
        self.query_one(Input).focus()

    def close(self) -> None:
        self.display = False

    def update_state(self, state: TerminalConversationState) -> None:
        self._state = state
        self._items = command_items_for_state(state)
        query = self.query_one(Input).value if self.is_mounted else ""
        self._refresh_filter(query)

    @property
    def selected_item(self) -> TerminalCommandItem | None:
        if not self._filtered_items:
            return None
        return self._filtered_items[self._selected_index]

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "command-filter":
            self._refresh_filter(event.value)

    def action_close_palette(self) -> None:
        cast(Any, self.app).close_command_palette(restore_focus=True)

    async def action_execute_selected_command(self) -> None:
        await self.execute_selected_command()

    async def execute_selected_command(self) -> None:
        item = self.selected_item
        if item is None:
            return
        await cast(Any, self.app).execute_terminal_command(item.spec.command_id)

    def action_command_next(self) -> None:
        if self._filtered_items:
            self._selected_index = min(
                self._selected_index + 1,
                len(self._filtered_items) - 1,
            )
            self._render_list()

    def action_command_previous(self) -> None:
        if self._filtered_items:
            self._selected_index = max(self._selected_index - 1, 0)
            self._render_list()

    def _refresh_filter(self, query: str) -> None:
        self._filtered_items = filter_command_items(self._items, query)
        self._selected_index = min(self._selected_index, len(self._filtered_items) - 1)
        self._selected_index = max(self._selected_index, 0)
        self._render_list()

    def _render_list(self) -> None:
        if self.is_mounted:
            self.query_one("#command-list", Static).update(self._render_items())

    def _render_items(self) -> str:
        if not self._filtered_items:
            return "No matching commands"
        lines: list[str] = []
        for index, item in enumerate(self._filtered_items[:8]):
            marker = ">" if index == self._selected_index else " "
            shortcut = f" [{item.spec.shortcut}]" if item.spec.shortcut else ""
            suffix = "" if item.enabled else f" - {item.disabled_reason}"
            lines.append(f"{marker} {item.spec.title}{shortcut}{suffix}")
        return "\n".join(lines)
