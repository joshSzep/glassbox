"""Keybinding declarations for the Glassbox terminal app."""

from textual.binding import Binding

TUI_KEY_BINDINGS: list[Binding] = [
    Binding("ctrl+q", "quit", "Quit", show=True),
    Binding("ctrl+l", "latest", "Latest", show=True),
    Binding("ctrl+enter", "submit_prompt", "Send", show=True),
    Binding("ctrl+s", "submit_prompt", "Send", show=False),
]
