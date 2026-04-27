"""Textual CSS for the Glassbox terminal app shell."""

GLASSBOX_TUI_CSS = """
Screen {
    layout: vertical;
    background: #101214;
    color: #e7e9ea;
}

#session-header {
    height: 3;
    padding: 0 1;
    border-bottom: solid $accent;
    background: #171a1d;
    color: #f3f4f4;
}

#conversation-pane {
    height: 1fr;
    padding: 1;
    background: #101214;
    color: #e7e9ea;
    overflow-y: auto;
}

#action-strip {
    height: 3;
    padding: 0 1;
    border-top: solid $accent;
    background: #15181a;
    color: #d7dbdd;
}

#composer {
    height: 3;
    padding: 0 1;
    border-top: solid $accent;
    background: #121518;
    color: #f3f4f4;
    scrollbar-size-vertical: 1;
}

#footer {
    height: 1;
    padding: 0 1;
    background: #171a1d;
    color: #aab2b7;
}

.status-normal {
    color: #e7e9ea;
}

.status-muted {
    color: #aab2b7;
}

.status-success {
    color: #7bd88f;
}

.status-warning {
    color: #f0b35a;
}

.status-danger {
    color: #ff6b6b;
}

.status-active {
    color: #8fc7ff;
}

.status-focus {
    color: #f5d36b;
}
"""
