"""Tests for the initial Textual terminal app boundary."""

import asyncio
from collections.abc import AsyncIterator
from typing import cast

from textual.widgets import Static

from glassbox.cli.interactive_client import InteractiveClientError
from glassbox.cli.interactive_client import InteractiveClientErrorKind
from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.interactive_launch import InteractiveLaunchMode
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui import GlassboxTerminalApp
from glassbox.cli.tui import create_session_tui_app
from glassbox.cli.tui import create_tui_app
from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import with_stream_status
from glassbox.cli.tui.keybindings import TUI_KEY_BINDINGS
from glassbox.cli.tui.state import session_dashboard_url
from glassbox.cli.tui.widgets import CommandPaletteWidget
from glassbox.cli.tui.widgets import ComposerFeedbackLine
from glassbox.cli.tui.widgets import ComposerWidget
from glassbox.cli.tui.widgets import ConversationPane
from glassbox.cli.tui.widgets import DetailsPane
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_artifact_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_session_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.core.models import MessagePart
from glassbox.core.models import SessionState
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import SessionStatus


def test_tui_app_factory_builds_app_with_fake_client() -> None:
    client = _FakeInteractiveClient()
    snapshot = _snapshot()
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
        dashboard_url="http://127.0.0.1:8765/?session=abc",
    )

    assert isinstance(app, GlassboxTerminalApp)
    assert app.state.header.dashboard_url == (
        f"http://127.0.0.1:8765/?session={snapshot.session_id}"
    )


def test_session_dashboard_url_adds_or_replaces_session_query() -> None:
    session_id = new_session_id()

    assert session_dashboard_url("http://127.0.0.1:8765/", session_id) == (
        f"http://127.0.0.1:8765/?session={session_id}"
    )
    assert (
        session_dashboard_url(
            "http://127.0.0.1:8765/?view=operator&session=old",
            session_id,
        )
        == f"http://127.0.0.1:8765/?view=operator&session={session_id}"
    )


def test_create_session_tui_app_fetches_snapshot_and_preserves_dashboard_url() -> None:
    asyncio.run(_run_lifecycle_test())


def test_tui_app_can_mount_and_close_client() -> None:
    asyncio.run(_run_app_mount_test())


def test_tui_app_ingests_live_events_into_transcript() -> None:
    asyncio.run(_run_live_event_test())


def test_tui_app_declares_latest_activity_keybinding() -> None:
    assert any(
        binding.key == "ctrl+l" and binding.action == "latest"
        for binding in TUI_KEY_BINDINGS
    )


def test_tui_app_declares_prompt_submit_keybinding() -> None:
    assert any(
        binding.key == "enter" and binding.action == "submit_prompt"
        for binding in ComposerWidget.BINDINGS
    )
    assert any(
        binding.key == "ctrl+enter" and binding.action == "insert_newline"
        for binding in ComposerWidget.BINDINGS
    )


def test_tui_app_declares_command_palette_keybinding() -> None:
    assert any(
        binding.key == "ctrl+p" and binding.action == "command_palette"
        for binding in TUI_KEY_BINDINGS
    )


def test_tui_app_declares_keyboard_navigation_keybindings() -> None:
    expected = {
        ("ctrl+escape", "quit"),
        ("ctrl+g", "focus_composer"),
        ("pageup", "transcript_page_up"),
        ("pagedown", "transcript_page_down"),
        ("ctrl+e", "toggle_details"),
        ("ctrl+d", "open_dashboard"),
        ("alt+d", "copy_dashboard_url"),
        ("alt+a", "approve"),
        ("alt+x", "deny"),
        ("ctrl+r", "submit_answer"),
        ("ctrl+c", "interrupt"),
        ("escape", "cancel_transient"),
    }

    assert expected.issubset(
        {(binding.key, binding.action) for binding in TUI_KEY_BINDINGS}
    )


def test_tui_app_submits_multiline_prompt_and_clears_draft() -> None:
    asyncio.run(_run_prompt_submit_test())


def test_tui_app_shows_pending_submission_feedback() -> None:
    asyncio.run(_run_pending_submission_feedback_test())


def test_tui_app_preserves_draft_for_validation_and_conflict_errors() -> None:
    asyncio.run(_run_validation_and_conflict_feedback_test())


def test_tui_app_preserves_draft_for_network_and_retryable_errors() -> None:
    asyncio.run(_run_network_and_retryable_feedback_test())


def test_tui_app_reports_unavailable_runtime_without_dispatching() -> None:
    asyncio.run(_run_unavailable_runtime_feedback_test())


def test_tui_app_reconnects_stream_and_resumes_from_last_sequence() -> None:
    asyncio.run(_run_stream_reconnect_success_test())


def test_tui_app_reports_unavailable_stream_after_retry_exhaustion() -> None:
    asyncio.run(_run_stream_retry_exhaustion_test())


def test_tui_app_preserves_draft_during_live_updates() -> None:
    asyncio.run(_run_draft_preservation_test())


def test_tui_app_keeps_local_prompt_history() -> None:
    asyncio.run(_run_prompt_history_test())


def test_tui_app_opens_filters_and_closes_command_palette() -> None:
    asyncio.run(_run_command_palette_test())


def test_tui_app_executes_palette_clipboard_and_approval_commands() -> None:
    asyncio.run(_run_command_execution_test())


def test_tui_app_toggles_markdown_transcript_rendering() -> None:
    asyncio.run(_run_markdown_toggle_test())


def test_tui_app_restores_focus_after_command_palette() -> None:
    asyncio.run(_run_palette_focus_restore_test())


def test_tui_app_focuses_composer_and_toggles_details_from_keyboard() -> None:
    asyncio.run(_run_keyboard_focus_test())


def test_tui_app_submits_answer_from_keyboard_action() -> None:
    asyncio.run(_run_answer_shortcut_test())


def test_tui_app_preserves_answer_draft_for_failures() -> None:
    asyncio.run(_run_answer_failure_feedback_test())


def test_tui_app_reports_stale_and_unavailable_question_answer_states() -> None:
    asyncio.run(_run_answer_stale_and_unavailable_test())


def test_tui_app_reports_approval_resolution_feedback() -> None:
    asyncio.run(_run_approval_resolution_feedback_test())


def test_tui_app_approval_slash_commands_are_typeable() -> None:
    asyncio.run(_run_approval_slash_command_test())


def test_tui_app_follows_latest_streaming_transcript() -> None:
    asyncio.run(_run_streaming_transcript_follow_latest_test())


def test_tui_app_scrolls_markdown_streaming_transcript() -> None:
    asyncio.run(_run_streaming_transcript_follow_latest_test(render_markdown=True))


def test_tui_app_details_wrap_full_dashboard_url() -> None:
    asyncio.run(_run_dashboard_details_wrap_test())


def test_tui_app_reports_handoff_copy_and_open_feedback() -> None:
    asyncio.run(_run_handoff_feedback_test())


def test_tui_app_handles_interrupt_and_quit_contract() -> None:
    asyncio.run(_run_interrupt_and_quit_contract_test())


async def _run_app_mount_test() -> None:
    client = _FakeInteractiveClient()
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        header = pilot.app.query_one("#session-header", Static)
        conversation = pilot.app.query_one(ConversationPane)
        action_strip = pilot.app.query_one("#action-strip", Static)
        composer = pilot.app.query_one("#composer", ComposerWidget)

        assert "Glassbox" in str(header.content)
        assert str(app.state.header.session_id)[:8] in str(header.content)
        assert "Starting conversation" in conversation.content_text
        assert action_strip.display is False
        assert pilot.app.focused is composer
        assert composer.size.height > 3
        assert composer.placeholder == (
            "Write a prompt. Enter sends; Ctrl+Enter adds a line."
        )

        pilot.app.exit()

    await app.close_client()


async def _run_prompt_submit_test() -> None:
    client = _FakeInteractiveClient()
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "Inspect this file"
        await pilot.pause()

        await pilot.press("ctrl+enter")
        await pilot.pause()

        assert composer.text == "\nInspect this file"
        assert client.submitted_messages == []

        composer.text = "Inspect this file\nThen summarize it"
        await pilot.pause()

        await pilot.press("enter")
        await pilot.pause()

        assert client.submitted_messages == ["Inspect this file\nThen summarize it"]
        assert composer.text == ""
        feedback = pilot.app.query_one(ComposerFeedbackLine)
        assert "Accepted: Prompt accepted" in str(feedback.content)
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        assert typed_app.state.composer.text == ""

        pilot.app.exit()

    await app.close_client()


async def _run_pending_submission_feedback_test() -> None:
    client = _FakeInteractiveClient()
    client.submit_started = asyncio.Event()
    client.submit_release = asyncio.Event()
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "long prompt"
        await pilot.pause()

        submit_task = asyncio.create_task(pilot.press("enter"))
        await client.submit_started.wait()
        feedback = pilot.app.query_one(ComposerFeedbackLine)

        assert "Sending: Waiting for the runtime" in str(feedback.content)
        assert composer.text == ""

        client.submit_release.set()
        await submit_task
        await pilot.pause()

        assert "Accepted: Prompt accepted" in str(feedback.content)

        pilot.app.exit()

    await app.close_client()


async def _run_validation_and_conflict_feedback_test() -> None:
    validation_client = _FakeInteractiveClient()
    validation_app = create_tui_app(
        client=validation_client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with validation_app.run_test(size=(100, 30)) as pilot:
        await pilot.press("enter")
        feedback = pilot.app.query_one(ComposerFeedbackLine)

        assert "Check prompt: Write a prompt before sending" in str(feedback.content)
        assert validation_client.submitted_messages == []

        pilot.app.exit()

    await validation_app.close_client()

    conflict_client = _FakeInteractiveClient(
        submit_error=InteractiveClientError(
            InteractiveClientErrorKind.CONFLICT,
            "session is busy",
        )
    )
    conflict_app = create_tui_app(
        client=conflict_client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with conflict_app.run_test(size=(100, 30)) as pilot:
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "keep this draft"
        await pilot.pause()
        await pilot.press("enter")
        feedback = pilot.app.query_one(ComposerFeedbackLine)

        assert "Not sent: session is busy" in str(feedback.content)
        assert composer.text == "keep this draft"
        assert conflict_client.submitted_messages == []

        pilot.app.exit()

    await conflict_app.close_client()


async def _run_network_and_retryable_feedback_test() -> None:
    network_client = _FakeInteractiveClient(
        submit_error=InteractiveClientError(
            InteractiveClientErrorKind.RUNTIME_UNAVAILABLE,
            "daemon unavailable",
        )
    )
    network_app = create_tui_app(
        client=network_client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with network_app.run_test(size=(100, 30)) as pilot:
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "retry me"
        await pilot.pause()
        await pilot.press("enter")
        feedback = pilot.app.query_one(ComposerFeedbackLine)

        assert "Network error: daemon unavailable" in str(feedback.content)
        assert "Retry is safe" in str(feedback.content)
        assert composer.text == "retry me"

        pilot.app.exit()

    await network_app.close_client()

    retry_client = _FakeInteractiveClient(submit_error=RuntimeError("boom"))
    retry_app = create_tui_app(
        client=retry_client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with retry_app.run_test(size=(100, 30)) as pilot:
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "still here"
        await pilot.pause()
        await pilot.press("enter")
        feedback = pilot.app.query_one(ComposerFeedbackLine)

        assert "Send failed: boom" in str(feedback.content)
        assert "Retry is safe" in str(feedback.content)
        assert composer.text == "still here"

        pilot.app.exit()

    await retry_app.close_client()


async def _run_unavailable_runtime_feedback_test() -> None:
    client = _FakeInteractiveClient()
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        typed_app.update_conversation_state(
            with_stream_status(
                typed_app.state,
                TerminalStreamStatus.UNAVAILABLE,
                detail="lost stream",
            )
        )
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "preserve while unavailable"
        await pilot.pause()
        await pilot.press("enter")
        feedback = pilot.app.query_one(ComposerFeedbackLine)

        assert "Runtime unavailable" in str(feedback.content)
        assert "Runtime stream unavailable" in str(feedback.content)
        assert "Retry is safe" in str(feedback.content)
        assert composer.text == "preserve while unavailable"
        assert client.submitted_messages == []

        pilot.app.exit()

    await app.close_client()


async def _run_stream_reconnect_success_test() -> None:
    snapshot = _snapshot()
    message_id = new_message_id()
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=AssistantMessageStarted(message_id=message_id),
            ),
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=9,
                payload=AssistantMessageDelta(message_id=message_id, delta="hello"),
            ),
        ],
        stream_errors=[RuntimeError("temporary stream break")],
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        header = pilot.app.query_one("#session-header", Static)
        conversation = pilot.app.query_one(ConversationPane)

        assert client.stream_after_sequences == [7, 7]
        assert "live: reconnected" in str(header.content)
        assert "hello" in conversation.content_text

        pilot.app.exit()

    await app.close_client()


async def _run_stream_retry_exhaustion_test() -> None:
    client = _FakeInteractiveClient(
        stream_errors=[
            RuntimeError("break 1"),
            RuntimeError("break 2"),
            RuntimeError("break 3"),
            RuntimeError("break 4"),
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        header = pilot.app.query_one("#session-header", Static)
        composer = pilot.app.query_one(ComposerWidget)

        assert client.stream_after_sequences == [7, 7, 7, 7]
        assert "unavailable: stream unavailable after 3 retries" in str(header.content)
        assert composer.read_only is True

        pilot.app.exit()

    await app.close_client()


async def _run_draft_preservation_test() -> None:
    snapshot = _snapshot()
    message_id = new_message_id()
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=AssistantMessageStarted(message_id=message_id),
            )
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "keep my draft"
        await pilot.pause()

        assert composer.text == "keep my draft"
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        assert typed_app.state.composer.text == "keep my draft"

        pilot.app.exit()

    await app.close_client()


async def _run_prompt_history_test() -> None:
    client = _FakeInteractiveClient()
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "first prompt"
        await pilot.press("enter")
        await pilot.pause()
        composer.text = "second prompt"
        await pilot.press("enter")
        await pilot.pause()

        typed_app = cast(GlassboxTerminalApp, pilot.app)
        typed_app.action_prompt_history_previous()
        assert composer.text == "second prompt"
        typed_app.action_prompt_history_previous()
        assert composer.text == "first prompt"
        typed_app.action_prompt_history_next()
        assert composer.text == "second prompt"

        pilot.app.exit()

    await app.close_client()


async def _run_command_palette_test() -> None:
    client = _FakeInteractiveClient()
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        palette = pilot.app.query_one(CommandPaletteWidget)
        assert palette.display is False

        await pilot.press("ctrl+p")
        await pilot.press("d", "a", "s", "h")
        command_list = pilot.app.query_one("#command-list", Static)

        assert palette.display is True
        assert "Open Dashboard" in str(command_list.content)
        assert "Copy Dashboard URL" in str(command_list.content)

        await pilot.press("escape")
        assert palette.display is False

        await pilot.press("ctrl+p")
        await pilot.press("c", "o", "p", "y", "-", "s", "e", "s", "s", "i", "o", "n")
        await pilot.press("enter")
        await pilot.pause()

        assert palette.display is False
        assert pilot.app.clipboard == str(app.state.header.session_id)

        pilot.app.exit()

    await app.close_client()


async def _run_command_execution_test() -> None:
    snapshot = _snapshot()
    approval_id = new_approval_id()
    turn_id = new_turn_id()
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=turn_id,
                    subject="run command",
                    reason="needs permission",
                ),
            )
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        await typed_app.execute_terminal_command(TerminalCommandId.COPY_SESSION_ID)
        await typed_app.execute_terminal_command(TerminalCommandId.APPROVE)

        assert pilot.app.clipboard == str(snapshot.session_id)
        assert client.resolved_approvals == [
            (approval_id, ApprovalDecision.APPROVED),
        ]

        pilot.app.exit()

    await app.close_client()


async def _run_markdown_toggle_test() -> None:
    snapshot = _snapshot()
    user_message_id = new_message_id()
    assistant_message_id = new_message_id()
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=UserMessageReceived(
                    message_id=user_message_id,
                    text="Please keep **bold** visible.",
                ),
            ),
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=9,
                payload=AssistantMessageCompleted(
                    message_id=assistant_message_id,
                    parts=[
                        MessagePart(
                            kind="text",
                            text="## Result\n\n- **done**\n- `code`",
                        )
                    ],
                ),
            ),
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        conversation = pilot.app.query_one(ConversationPane)
        assert conversation.markdown_enabled is True
        assert "**done**" in conversation.content_text

        rendered_text = "\n".join(strip.text for strip in conversation.lines)
        assert "done" in rendered_text
        assert "**done**" not in rendered_text

        await app.execute_terminal_command(TerminalCommandId.TOGGLE_MARKDOWN)
        await pilot.pause()

        action_strip = pilot.app.query_one("#action-strip", Static)
        rendered_text = "\n".join(strip.text for strip in conversation.lines)

        assert conversation.markdown_enabled is False
        assert "Markdown rendering disabled" in str(action_strip.content)
        assert "**done**" in conversation.content_text
        assert "**done**" in rendered_text

        await app.execute_terminal_command(TerminalCommandId.TOGGLE_MARKDOWN)
        await pilot.pause()

        rendered_text = "\n".join(strip.text for strip in conversation.lines)
        assert conversation.markdown_enabled is True
        assert "Markdown rendering enabled" in str(action_strip.content)
        assert "done" in rendered_text
        assert "**done**" not in rendered_text

        pilot.app.exit()

    await app.close_client()


async def _run_palette_focus_restore_test() -> None:
    client = _FakeInteractiveClient()
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        composer = pilot.app.query_one(ComposerWidget)
        composer.focus()
        await pilot.press("ctrl+p")
        await pilot.press("escape")

        assert pilot.app.focused is composer

        pilot.app.exit()

    await app.close_client()


async def _run_keyboard_focus_test() -> None:
    client = _FakeInteractiveClient()
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        await pilot.press("ctrl+g")
        assert pilot.app.focused is pilot.app.query_one(ComposerWidget)

        await typed_app.action_toggle_details()
        details = pilot.app.query_one(DetailsPane)
        assert details.display is True
        assert pilot.app.focused is details

        await pilot.press("escape")
        assert details.display is False
        assert pilot.app.focused is pilot.app.query_one(ComposerWidget)

        pilot.app.exit()

    await app.close_client()


async def _run_answer_shortcut_test() -> None:
    snapshot = _snapshot()
    question_id = new_question_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=UserQuestionAsked(
                    question_id=question_id,
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    provider_tool_call_id="ask-1",
                    question="Which file?",
                ),
            )
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "src/glassbox/cli/tui/app.py"
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)

        assert typed_app.state.composer.question_id == question_id

        await typed_app.action_submit_answer()
        action_strip = pilot.app.query_one("#action-strip", Static)

        assert client.submitted_answers == [
            (question_id, "src/glassbox/cli/tui/app.py")
        ]
        assert composer.text == ""
        assert "Accepted: Answer accepted" in str(action_strip.content)

        pilot.app.exit()

    await app.close_client()
    await app.close_client()

    assert client.closed is True


async def _run_answer_failure_feedback_test() -> None:
    snapshot = _snapshot()
    question_id = new_question_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=UserQuestionAsked(
                    question_id=question_id,
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    provider_tool_call_id="ask-1",
                    question="Which file?",
                ),
            )
        ],
        answer_error=InteractiveClientError(
            InteractiveClientErrorKind.CONFLICT,
            "question already answered",
        ),
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "src/app.py"
        await pilot.pause()

        typed_app = cast(GlassboxTerminalApp, pilot.app)
        await typed_app.action_submit_answer()
        action_strip = pilot.app.query_one("#action-strip", Static)

        assert "Not sent: question already answered" in str(action_strip.content)
        assert composer.text == "src/app.py"
        assert client.submitted_answers == []

        pilot.app.exit()

    await app.close_client()


async def _run_answer_stale_and_unavailable_test() -> None:
    stale_client = _FakeInteractiveClient()
    stale_app = create_tui_app(
        client=stale_client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )
    async with stale_app.run_test(size=(100, 30)) as pilot:
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        await typed_app.action_submit_answer()
        action_strip = pilot.app.query_one("#action-strip", Static)

        assert "Not sent: No pending question" in str(action_strip.content)
        assert stale_client.submitted_answers == []

        pilot.app.exit()

    await stale_app.close_client()

    snapshot = _snapshot()
    question_id = new_question_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    unavailable_client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=UserQuestionAsked(
                    question_id=question_id,
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    provider_tool_call_id="ask-1",
                    question="Which file?",
                ),
            )
        ]
    )
    unavailable_app = create_tui_app(
        client=unavailable_client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )
    async with unavailable_app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        typed_app.update_conversation_state(
            with_stream_status(
                typed_app.state,
                TerminalStreamStatus.UNAVAILABLE,
                detail="lost stream",
            )
        )
        composer = pilot.app.query_one(ComposerWidget)
        composer.text = "src/app.py"
        await pilot.pause()
        await typed_app.action_submit_answer()
        action_strip = pilot.app.query_one("#action-strip", Static)

        assert "Runtime unavailable: lost stream" in str(action_strip.content)
        assert "Retry is safe" in str(action_strip.content)
        assert composer.text == "src/app.py"
        assert unavailable_client.submitted_answers == []

        pilot.app.exit()

    await unavailable_app.close_client()


async def _run_approval_resolution_feedback_test() -> None:
    snapshot = _snapshot()
    approval_id = new_approval_id()
    turn_id = new_turn_id()
    approve_client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=turn_id,
                    subject="run command",
                    reason="needs permission",
                ),
            )
        ]
    )
    approve_app = create_tui_app(
        client=approve_client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )
    async with approve_app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        await typed_app.execute_terminal_command(TerminalCommandId.APPROVE)
        action_strip = pilot.app.query_one("#action-strip", Static)

        assert approve_client.resolved_approvals == [
            (approval_id, ApprovalDecision.APPROVED)
        ]
        assert "Accepted: Approval accepted" in str(action_strip.content)

        pilot.app.exit()
    await approve_app.close_client()

    deny_client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=turn_id,
                    subject="run command",
                    reason="needs permission",
                ),
            )
        ],
        approval_error=InteractiveClientError(
            InteractiveClientErrorKind.VALIDATION_ERROR,
            "invalid decision",
        ),
    )
    deny_app = create_tui_app(
        client=deny_client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )
    async with deny_app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        await typed_app.execute_terminal_command(TerminalCommandId.DENY)
        action_strip = pilot.app.query_one("#action-strip", Static)

        assert deny_client.resolved_approvals == []
        assert "Check answer: invalid decision" in str(action_strip.content)

        pilot.app.exit()
    await deny_app.close_client()

    network_client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=turn_id,
                    subject="run command",
                    reason="needs permission",
                ),
            )
        ],
        approval_error=InteractiveClientError(
            InteractiveClientErrorKind.RUNTIME_UNAVAILABLE,
            "daemon unavailable",
        ),
    )
    network_app = create_tui_app(
        client=network_client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )
    async with network_app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        await typed_app.execute_terminal_command(TerminalCommandId.APPROVE)
        action_strip = pilot.app.query_one("#action-strip", Static)

        assert "Network error: daemon unavailable" in str(action_strip.content)
        assert "Retry is safe" in str(action_strip.content)

        pilot.app.exit()
    await network_app.close_client()

    resolved_client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=turn_id,
                    subject="run command",
                    reason="needs permission",
                ),
            ),
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=9,
                payload=ApprovalResolved(
                    approval_id=approval_id,
                    decision=ApprovalDecision.APPROVED,
                    decided_by="operator",
                ),
            ),
        ]
    )
    resolved_app = create_tui_app(
        client=resolved_client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )
    async with resolved_app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        await typed_app.execute_terminal_command(TerminalCommandId.APPROVE)
        action_strip = pilot.app.query_one("#action-strip", Static)

        assert resolved_client.resolved_approvals == []
        assert "Resolved: Approval already resolved" in str(action_strip.content)

        pilot.app.exit()
    await resolved_app.close_client()


async def _run_handoff_feedback_test() -> None:
    snapshot = _snapshot()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    artifact_path = "/workspace/reports/output.txt"
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=ModelToolCallRequested(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    tool_name="write_file",
                    arguments_json='{"path":"/workspace/reports/output.txt"}',
                ),
            ),
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=9,
                payload=ToolArtifactRecorded(
                    turn_id=turn_id,
                    tool_call_id=tool_call_id,
                    artifact_id=new_artifact_id(),
                    artifact_kind="file",
                    path=artifact_path,
                ),
            ),
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)

        await typed_app.execute_terminal_command(TerminalCommandId.COPY_SESSION_ID)
        action_strip = pilot.app.query_one("#action-strip", Static)
        assert pilot.app.clipboard == str(snapshot.session_id)
        assert "Accepted: Session ID copied." in str(action_strip.content)

        await typed_app.execute_terminal_command(TerminalCommandId.COPY_DASHBOARD_URL)
        assert pilot.app.clipboard == snapshot.dashboard_url
        assert "Accepted: Dashboard URL copied." in str(action_strip.content)

        await typed_app.execute_terminal_command(TerminalCommandId.COPY_ARTIFACT_PATH)
        assert pilot.app.clipboard == artifact_path
        assert "Accepted: Artifact path copied." in str(action_strip.content)

        await typed_app.execute_terminal_command(TerminalCommandId.OPEN_ARTIFACT_PATH)
        assert "Not sent: Artifact path is missing" in str(action_strip.content)

        pilot.app.exit()

    await app.close_client()


async def _run_approval_slash_command_test() -> None:
    snapshot = _snapshot()
    approval_id = new_approval_id()
    turn_id = new_turn_id()
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=ApprovalRequested(
                    approval_id=approval_id,
                    turn_id=turn_id,
                    subject="run command",
                    reason="needs permission",
                ),
            )
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        composer = pilot.app.query_one(ComposerWidget)

        assert composer.read_only is False

        composer.text = "/approve"
        await pilot.pause()
        await pilot.press("enter")
        action_strip = pilot.app.query_one("#action-strip", Static)

        assert client.resolved_approvals == [(approval_id, ApprovalDecision.APPROVED)]
        assert "Accepted: Approval accepted" in str(action_strip.content)

        pilot.app.exit()

    await app.close_client()


async def _run_streaming_transcript_follow_latest_test(
    *,
    render_markdown: bool = False,
) -> None:
    snapshot = _snapshot()
    message_id = new_message_id()
    if render_markdown:
        long_response = "\n".join(
            f"- **item {index:03d}**: streaming markdown content" for index in range(90)
        )
        expected_tail = "item 089"
    else:
        long_response = " ".join(f"token{i:03d}" for i in range(240))
        expected_tail = "token239"
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=AssistantMessageStarted(message_id=message_id),
            ),
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=9,
                payload=AssistantMessageDelta(
                    message_id=message_id,
                    delta=long_response,
                ),
            ),
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(60, 16)) as pilot:
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        conversation = pilot.app.query_one(ConversationPane)
        if conversation.markdown_enabled is not render_markdown:
            await typed_app.execute_terminal_command(TerminalCommandId.TOGGLE_MARKDOWN)
            await pilot.pause()

        assert conversation.markdown_enabled is render_markdown
        assert expected_tail in conversation.content_text
        assert conversation.scroll_y == conversation.max_scroll_y
        assert conversation.show_vertical_scrollbar is True
        assert conversation.show_horizontal_scrollbar is False
        assert conversation.vertical_scrollbar.position == conversation.scroll_y

        if render_markdown:
            typed_app.apply_runtime_event(
                EventEnvelope(
                    session_id=snapshot.session_id,
                    sequence=10,
                    payload=AssistantMessageDelta(
                        message_id=message_id,
                        delta="\n- **late item**: still streaming",
                    ),
                )
            )
            conversation.page_up()
        else:
            await pilot.press("pageup")
        await pilot.pause()
        assert conversation.scroll_y < conversation.max_scroll_y
        assert conversation.vertical_scrollbar.position == conversation.scroll_y
        manual_scroll_y = conversation.scroll_y

        typed_app.apply_runtime_event(
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=11 if render_markdown else 10,
                payload=AssistantMessageDelta(
                    message_id=message_id,
                    delta=" live update after manual scroll",
                ),
            )
        )
        await pilot.pause()

        assert conversation.scroll_y == manual_scroll_y
        assert conversation.scroll_y < conversation.max_scroll_y

        await pilot.press("ctrl+l")
        await pilot.pause()
        action_strip = pilot.app.query_one("#action-strip", Static)
        assert conversation.scroll_y == conversation.max_scroll_y
        assert conversation.vertical_scrollbar.position == conversation.scroll_y
        assert "Showing latest transcript output" in str(action_strip.content)

        pilot.app.exit()

    await app.close_client()


async def _run_dashboard_details_wrap_test() -> None:
    snapshot = _snapshot()
    dashboard_url = (
        "http://127.0.0.1:8765/?view=operator&branch=feature-super-long"
        f"&session={snapshot.session_id}"
    )
    app = create_tui_app(
        client=_FakeInteractiveClient(),
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
        dashboard_url=dashboard_url,
    )

    async with app.run_test(size=(120, 20)) as pilot:
        await pilot.pause()
        details = pilot.app.query_one(DetailsPane)
        details.toggle()
        await pilot.pause()
        details_text = str(details.content)
        dashboard_block = details_text.split("dashboard: ", 1)[1].split(
            "\nselected tool",
            1,
        )[0]
        compact_dashboard = "".join(dashboard_block.split())

        assert "..." not in dashboard_block
        assert "http://127.0.0.1:8765/?view=operator" in compact_dashboard
        assert str(snapshot.session_id) in compact_dashboard

        pilot.app.exit()

    await app.close_client()


async def _run_interrupt_and_quit_contract_test() -> None:
    snapshot = _snapshot()
    turn_id = new_turn_id()
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=TurnStarted(
                    turn_id=turn_id,
                    trigger_message_id=new_message_id(),
                ),
            )
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        typed_app = cast(GlassboxTerminalApp, pilot.app)

        await typed_app.execute_terminal_command(TerminalCommandId.INTERRUPT)
        action_strip = pilot.app.query_one("#action-strip", Static)
        assert "Runtime turn interruption is not supported yet" in str(
            action_strip.content
        )

        await typed_app.execute_terminal_command(TerminalCommandId.QUIT)
        assert "Press Ctrl+Escape again to leave" in str(action_strip.content)

        typed_app.action_cancel_transient()
        assert "Quit cancelled" in str(action_strip.content)

        await pilot.press("ctrl+p")
        assert pilot.app.query_one(CommandPaletteWidget).display is True
        await pilot.press("ctrl+c")
        assert pilot.app.query_one(CommandPaletteWidget).display is False

        pilot.app.exit()

    await app.close_client()


async def _run_lifecycle_test() -> None:
    client = _FakeInteractiveClient()
    app = await create_session_tui_app(
        client=client,
        launch_options=_launch_options(),
        dashboard_url="http://127.0.0.1:8765/",
    )

    assert client.fetch_count == 1
    assert app.state.header.dashboard_url == (
        f"http://127.0.0.1:8765/?session={app.state.header.session_id}"
    )


async def _run_live_event_test() -> None:
    snapshot = _snapshot()
    message_id = new_message_id()
    client = _FakeInteractiveClient(
        events=[
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=8,
                payload=AssistantMessageStarted(message_id=message_id),
            ),
            EventEnvelope(
                session_id=snapshot.session_id,
                sequence=9,
                payload=AssistantMessageDelta(message_id=message_id, delta="hello"),
            ),
        ]
    )
    app = create_tui_app(
        client=client,
        initial_snapshot=snapshot,
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        conversation = pilot.app.query_one(ConversationPane)

        assert "Assistant" not in conversation.content_text
        assert "hello" in conversation.content_text

        pilot.app.exit()

    await app.close_client()


def _snapshot() -> InteractiveSessionSnapshot:
    session_id = new_session_id()
    return InteractiveSessionSnapshot(
        state=SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            last_sequence=7,
        ),
        cwd="/workspace",
        model_name="openai:gpt-5.4",
        approval_mode="confirm",
        dashboard_url="http://127.0.0.1:8765/",
    )


def _launch_options() -> InteractiveLaunchOptions:
    return InteractiveLaunchOptions(
        requested_mode=InteractiveLaunchMode.TUI,
        default_mode=InteractiveLaunchMode.PLAIN,
        stdin_is_tty=True,
        stdout_is_tty=True,
        term="xterm-256color",
        ci=False,
        tui_available=True,
    )


class _FakeInteractiveClient:
    def __init__(
        self,
        *,
        events: list[EventEnvelope] | None = None,
        submit_error: Exception | None = None,
        answer_error: Exception | None = None,
        approval_error: Exception | None = None,
        stream_errors: list[Exception] | None = None,
    ) -> None:
        self.closed = False
        self.fetch_count = 0
        self.events = events or []
        self.stream_errors = stream_errors or []
        self.stream_after_sequences: list[int] = []
        self.submit_error = submit_error
        self.answer_error = answer_error
        self.approval_error = approval_error
        self.submit_started: asyncio.Event | None = None
        self.submit_release: asyncio.Event | None = None
        self.submitted_messages: list[str] = []
        self.submitted_answers: list[tuple[QuestionId, str]] = []
        self.resolved_approvals: list[tuple[ApprovalId, ApprovalDecision]] = []

    @property
    def session_id(self):
        return new_session_id()

    async def fetch_snapshot(self) -> InteractiveSessionSnapshot:
        self.fetch_count += 1
        return _snapshot()

    async def submit_message(self, text: str) -> None:
        if self.submit_started is not None:
            self.submit_started.set()
        if self.submit_release is not None:
            await self.submit_release.wait()
        if self.submit_error is not None:
            raise self.submit_error
        self.submitted_messages.append(text)

    async def submit_answer(self, question_id: QuestionId, answer: str) -> None:
        if self.answer_error is not None:
            raise self.answer_error
        self.submitted_answers.append((question_id, answer))

    async def resolve_approval(
        self,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None:
        if self.approval_error is not None:
            raise self.approval_error
        self.resolved_approvals.append((approval_id, decision))

    async def stream_events(
        self,
        *,
        after_sequence: int = 0,
    ) -> AsyncIterator[EventEnvelope]:
        self.stream_after_sequences.append(after_sequence)
        if self.stream_errors:
            raise self.stream_errors.pop(0)
        for event in self.events:
            if event.sequence > after_sequence:
                yield event

    async def aclose(self) -> None:
        self.closed = True
