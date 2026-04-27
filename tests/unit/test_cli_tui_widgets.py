"""Widget rendering tests for the terminal app frame."""

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import conversation_state_from_snapshot
from glassbox.cli.tui.conversation import reduce_events
from glassbox.cli.tui.conversation import with_runtime_owner
from glassbox.cli.tui.conversation import with_stream_status
from glassbox.cli.tui.theme import GLASSBOX_TUI_CSS
from glassbox.cli.tui.widgets import ComposerSubmissionFeedback
from glassbox.cli.tui.widgets import ComposerSubmissionStatus
from glassbox.cli.tui.widgets import composer_availability
from glassbox.cli.tui.widgets import render_composer_feedback
from glassbox.cli.tui.widgets import render_footer_help
from glassbox.cli.tui.widgets import render_session_header
from glassbox.cli.tui.widgets import render_transcript
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import ToolOutputChunk
from glassbox.core.events import TurnFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_session_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.core.models import MessagePart
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
    assert "#composer-feedback" in GLASSBOX_TUI_CSS
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


def test_composer_feedback_renders_normalized_submission_states() -> None:
    assert render_composer_feedback(None) == ""
    assert (
        render_composer_feedback(
            ComposerSubmissionFeedback(
                ComposerSubmissionStatus.PENDING,
                "Waiting for runtime.",
            )
        )
        == "Sending: Waiting for runtime."
    )
    assert (
        render_composer_feedback(
            ComposerSubmissionFeedback(
                ComposerSubmissionStatus.ACCEPTED,
                "Prompt accepted.",
            )
        )
        == "Accepted: Prompt accepted."
    )
    assert (
        render_composer_feedback(
            ComposerSubmissionFeedback(
                ComposerSubmissionStatus.NETWORK_ERROR,
                "daemon unavailable",
                retryable=True,
            )
        )
        == "Network error: daemon unavailable Retry is safe."
    )


def test_composer_availability_blocks_historical_and_reconnecting_states() -> None:
    historical_state = conversation_state_from_snapshot(
        InteractiveSessionSnapshot(
            state=SessionState(
                session_id=new_session_id(),
                status=SessionStatus.COMPLETED,
            )
        )
    )
    reconnecting_state = with_stream_status(
        _state(),
        TerminalStreamStatus.RECONNECTING,
    )

    assert composer_availability(_state()).can_submit is True
    assert composer_availability(historical_state).can_edit is False
    assert composer_availability(historical_state).disabled_reason == (
        "historical session"
    )
    assert composer_availability(reconnecting_state).can_submit is False
    assert composer_availability(reconnecting_state).disabled_reason == (
        "runtime reconnecting"
    )


def test_transcript_renders_chat_tools_and_failure() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    state = reduce_events(
        _state(session_id=session_id),
        [
            _event(
                session_id,
                1,
                UserMessageReceived(
                    message_id=new_message_id(),
                    text="Please inspect src/glassbox/cli/tui/widgets.py carefully.",
                ),
            ),
            _event(
                session_id,
                2,
                TurnStarted(turn_id=turn_id, trigger_message_id=new_message_id()),
            ),
            _event(
                session_id,
                3,
                ToolExecutionStarted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="read_file_with_a_long_name_that_needs_truncation",
                ),
            ),
            _event(
                session_id,
                4,
                ToolOutputChunk(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    stream="stdout",
                    chunk="opened widgets.py",
                ),
            ),
            _event(
                session_id,
                5,
                ToolExecutionCompleted(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    success=True,
                    exit_code=0,
                    summary="read complete",
                ),
            ),
            _event(
                session_id,
                6,
                AssistantMessageCompleted(
                    message_id=new_message_id(),
                    parts=[MessagePart(kind="text", text="I found the transcript.")],
                ),
            ),
        ],
    )

    rendered = render_transcript(state, width=54)
    lines = rendered.splitlines()

    assert "You" in rendered
    assert "Assistant (completed)" in rendered
    assert "Tool:" in rendered
    assert "read complete" in rendered
    assert "output: opened widgets.py" in rendered
    assert all(len(line) <= 54 for line in lines if line)


def test_transcript_empty_states_are_specific() -> None:
    assert render_transcript(_state()) == "Starting conversation..."
    historical_state = conversation_state_from_snapshot(
        InteractiveSessionSnapshot(
            state=SessionState(
                session_id=new_session_id(),
                status=SessionStatus.COMPLETED,
            )
        )
    )

    assert render_transcript(historical_state) == "No transcript messages yet."


def test_transcript_distinguishes_failed_assistant_stream() -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    message_id = new_message_id()
    state = reduce_events(
        _state(session_id=session_id),
        [
            _event(
                session_id,
                1,
                TurnStarted(turn_id=turn_id, trigger_message_id=new_message_id()),
            ),
            _event(session_id, 2, AssistantMessageStarted(message_id=message_id)),
            _event(
                session_id,
                3,
                AssistantMessageDelta(message_id=message_id, delta="Half"),
            ),
            _event(session_id, 4, TurnFailed(turn_id=turn_id, error_message="boom")),
        ],
    )

    rendered = render_transcript(state, width=60)

    assert "Assistant (failed)" in rendered
    assert "Half" in rendered
    assert "Turn failed" in rendered


def _state(*, session_id=None):
    return conversation_state_from_snapshot(
        InteractiveSessionSnapshot(
            state=SessionState(
                session_id=session_id or new_session_id(),
                status=SessionStatus.RUNNING,
            ),
            cwd="/workspace",
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
            dashboard_url="http://127.0.0.1:8765/?session=abc",
        )
    )


def _event(session_id, sequence, payload) -> EventEnvelope:
    return EventEnvelope(session_id=session_id, sequence=sequence, payload=payload)
