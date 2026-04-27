"""Keybinding declarations for the Glassbox terminal app."""

from textual.binding import Binding

TUI_KEY_BINDINGS: list[Binding] = [
    Binding("ctrl+q", "quit", "Quit", show=True),
]
