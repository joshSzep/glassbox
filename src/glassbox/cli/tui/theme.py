"""Textual CSS for the Glassbox terminal app shell."""

GLASSBOX_TUI_CSS = """
Screen {
    layout: vertical;
}

#session-header {
    height: 3;
    padding: 0 1;
    border-bottom: solid $accent;
}

#conversation-pane {
    height: 1fr;
    padding: 1;
}

#action-strip {
    height: 3;
    padding: 0 1;
    border-top: solid $accent;
}

#composer {
    height: 3;
    padding: 0 1;
    border-top: solid $accent;
}

#footer {
    height: 1;
    padding: 0 1;
}
"""
