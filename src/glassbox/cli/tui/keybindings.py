"""Keybinding declarations for the Glassbox terminal app."""

from textual.binding import Binding

TUI_KEY_BINDINGS: list[Binding] = [
    Binding("ctrl+q", "quit", "Quit", show=True),
    Binding("ctrl+l", "latest", "Latest", show=True, priority=True),
    Binding("ctrl+p", "command_palette", "Palette", show=True),
    Binding("ctrl+g", "focus_composer", "Composer", show=True),
    Binding("pageup", "transcript_page_up", "Scroll Up", show=False, priority=True),
    Binding(
        "pagedown",
        "transcript_page_down",
        "Scroll Down",
        show=False,
        priority=True,
    ),
    Binding("ctrl+e", "toggle_details", "Details", show=True),
    Binding("ctrl+d", "open_dashboard", "Dashboard", show=False),
    Binding("alt+d", "copy_dashboard_url", "Copy Dashboard", show=False),
    Binding("alt+a", "approve", "Approve", show=False),
    Binding("alt+x", "deny", "Deny", show=False),
    Binding("ctrl+r", "submit_answer", "Answer", show=False),
    Binding("ctrl+c", "interrupt", "Interrupt", show=False),
    Binding("escape", "cancel_transient", "Cancel", show=False),
    Binding("ctrl+enter", "submit_prompt", "Send", show=True),
    Binding("ctrl+s", "submit_prompt", "Send", show=False),
]
