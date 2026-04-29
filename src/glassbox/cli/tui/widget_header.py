"""Header and footer widgets for the terminal UI."""

from textual.widgets import Static

from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import header_display_from_state
from glassbox.cli.tui.widget_formatting import dashboard_hint
from glassbox.cli.tui.widget_formatting import fit_line


class SessionHeader(Static):
    def __init__(self, state: TerminalConversationState) -> None:
        self._state = state
        super().__init__(render_session_header(state), id="session-header")

    def on_mount(self) -> None:
        self.update_state(self._state)

    def on_resize(self) -> None:
        self.update_state(self._state)

    def update_state(self, state: TerminalConversationState) -> None:
        self._state = state
        self.update(render_session_header(state, width=self._render_width()))

    def _render_width(self) -> int:
        if not self.is_mounted:
            return 80
        return max(self.size.width, 36)


class FooterHelp(Static):
    def __init__(self) -> None:
        super().__init__(render_footer_help(), id="footer")

    def on_mount(self) -> None:
        self.update(render_footer_help(width=self._render_width()))

    def on_resize(self) -> None:
        self.update(render_footer_help(width=self._render_width()))

    def _render_width(self) -> int:
        if not self.is_mounted:
            return 80
        return max(self.size.width, 24)


def render_session_header(
    state: TerminalConversationState,
    *,
    width: int = 80,
) -> str:
    header = header_display_from_state(state, width=width)
    branch = f" | {header.branch_label}" if header.branch_label else ""
    dashboard = dashboard_hint(header.dashboard_url, header.dashboard_label, width)
    if width < 52:
        line_one = (
            f"Glassbox {header.session_label} | {header.mode_label} | {dashboard}"
        )
    else:
        line_one = (
            f"Glassbox {header.session_label} | {header.mode_label} | "
            f"{header.stream_label} | {dashboard}"
        )
    line_two = (
        f"{header.cwd_label} | {header.model_label} | "
        f"{header.runtime_label}{branch} | {header.last_update_label}"
    )
    return f"{fit_line(line_one, width)}\n{fit_line(line_two, width)}"


def render_footer_help(*, width: int = 80) -> str:
    if width < 44:
        return fit_line("Ctrl+Esc Quit", width)
    if width < 64:
        return fit_line("Ctrl+Esc Quit | Ctrl+L Bottom", width)
    if width < 84:
        return fit_line("Ctrl+Esc Quit | Ctrl+L Bottom | Ctrl+P Palette", width)
    return fit_line(
        "Ctrl+Esc Quit | Ctrl+L Bottom | Ctrl+P Palette | Ctrl+D Dashboard",
        width,
    )
