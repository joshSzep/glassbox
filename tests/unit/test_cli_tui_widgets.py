"""Widget rendering tests for the terminal app frame."""

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import conversation_state_from_snapshot
from glassbox.cli.tui.conversation import with_runtime_owner
from glassbox.cli.tui.conversation import with_stream_status
from glassbox.cli.tui.theme import GLASSBOX_TUI_CSS
from glassbox.cli.tui.widgets import render_footer_help
from glassbox.cli.tui.widgets import render_session_header
from glassbox.core.ids import new_session_id
from glassbox.core.models import SessionState
from glassbox.core.types import SessionStatus


def test_session_header_renders_wide_dashboard_and_runtime_context() -> None:
    state = with_runtime_owner(_state(), "local runtime")
    state = with_stream_status(
        state,
        TerminalStreamStatus.RECONNECTING,
        detail="retry 2",
    )

    rendered = render_session_header(state, width=120)
    lines = rendered.splitlines()

    assert len(lines) == 2
    assert all(len(line) <= 120 for line in lines)
    assert "Glassbox" in lines[0]
    assert "reconnecting: retry 2" in lines[0]
    assert "dashboard http://127" in lines[0]
    assert "/workspace" in lines[1]
    assert "openai:gpt-5.4" in lines[1]
    assert "local runtime" in lines[1]


def test_session_header_fits_narrow_terminal_width() -> None:
    state = conversation_state_from_snapshot(
        InteractiveSessionSnapshot(
            state=SessionState(
                session_id=new_session_id(),
                status=SessionStatus.RUNNING,
            ),
            cwd="/very/long/workspace/path/with/a/deep/project-name",
            model_name="anthropic:claude-sonnet-super-long-model-name",
            dashboard_url=None,
        )
    )

    rendered = render_session_header(state, width=42)
    lines = rendered.splitlines()

    assert len(lines) == 2
    assert all(len(line) <= 42 for line in lines)
    assert "no dashboard" in lines[0]
    assert "project-name" in lines[1]


def test_footer_help_collapses_for_available_width() -> None:
    assert render_footer_help(width=100) == (
        "Ctrl+Q Quit | Ctrl+L Latest | Ctrl+P Palette | Ctrl+D Dashboard"
    )
    assert render_footer_help(width=70) == (
        "Ctrl+Q Quit | Ctrl+L Latest | Ctrl+P Palette"
    )
    assert render_footer_help(width=50) == "Ctrl+Q Quit | Ctrl+L Latest"
    assert render_footer_help(width=30) == "Ctrl+Q Quit"


def test_theme_defines_terminal_frame_surfaces() -> None:
    assert "#session-header" in GLASSBOX_TUI_CSS
    assert "#conversation-pane" in GLASSBOX_TUI_CSS
    assert "#action-strip" in GLASSBOX_TUI_CSS
    assert "#composer" in GLASSBOX_TUI_CSS
    assert "#footer" in GLASSBOX_TUI_CSS
    for class_name in [
        ".status-normal",
        ".status-muted",
        ".status-success",
        ".status-warning",
        ".status-danger",
        ".status-active",
        ".status-focus",
    ]:
        assert class_name in GLASSBOX_TUI_CSS


def _state():
    return conversation_state_from_snapshot(
        InteractiveSessionSnapshot(
            state=SessionState(
                session_id=new_session_id(),
                status=SessionStatus.RUNNING,
            ),
            cwd="/workspace",
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            dashboard_url="http://127.0.0.1:8765/?session=abc",
        )
    )
