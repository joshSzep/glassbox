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
from glassbox.cli.tui.widgets import DetailsPane
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ToolArtifactRecorded
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
        binding.key == "ctrl+enter" and binding.action == "submit_prompt"
        for binding in TUI_KEY_BINDINGS
    )


def test_tui_app_declares_command_palette_keybinding() -> None:
    assert any(
        binding.key == "ctrl+p" and binding.action == "command_palette"
        for binding in TUI_KEY_BINDINGS
    )


def test_tui_app_declares_keyboard_navigation_keybindings() -> None:
    expected = {
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


def test_tui_app_preserves_draft_during_live_updates() -> None:
    asyncio.run(_run_draft_preservation_test())


def test_tui_app_keeps_local_prompt_history() -> None:
    asyncio.run(_run_prompt_history_test())


def test_tui_app_opens_filters_and_closes_command_palette() -> None:
    asyncio.run(_run_command_palette_test())


def test_tui_app_executes_palette_clipboard_and_approval_commands() -> None:
    asyncio.run(_run_command_execution_test())


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


def test_tui_app_reports_handoff_copy_and_open_feedback() -> None:
    asyncio.run(_run_handoff_feedback_test())


async def _run_app_mount_test() -> None:
    client = _FakeInteractiveClient()
    app = create_tui_app(
        client=client,
        initial_snapshot=_snapshot(),
        launch_options=_launch_options(),
    )

    async with app.run_test(size=(100, 30)) as pilot:
        header = pilot.app.query_one("#session-header", Static)
        conversation = pilot.app.query_one("#conversation-pane", Static)
        composer = pilot.app.query_one("#composer", ComposerWidget)

        assert "Glassbox" in str(header.content)
        assert str(app.state.header.session_id)[:8] in str(header.content)
        assert "Starting conversation" in str(conversation.content)
        assert composer.placeholder == (
            "Write a prompt. Enter adds a line; Ctrl+Enter sends."
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
        composer.text = "Inspect this file\nThen summarize it"
        await pilot.pause()

        await pilot.press("ctrl+enter")
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

        submit_task = asyncio.create_task(pilot.press("ctrl+enter"))
        await client.submit_started.wait()
        feedback = pilot.app.query_one(ComposerFeedbackLine)

        assert "Sending: Waiting for the runtime" in str(feedback.content)
        assert composer.text == "long prompt"

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
        await pilot.press("ctrl+enter")
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
        await pilot.press("ctrl+enter")
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
        await pilot.press("ctrl+enter")
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
        await pilot.press("ctrl+enter")
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
        await pilot.press("ctrl+enter")
        feedback = pilot.app.query_one(ComposerFeedbackLine)

        assert "Runtime unavailable" in str(feedback.content)
        assert "Runtime stream unavailable" in str(feedback.content)
        assert "Retry is safe" in str(feedback.content)
        assert composer.text == "preserve while unavailable"
        assert client.submitted_messages == []

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
        await pilot.press("ctrl+enter")
        await pilot.pause()
        composer.text = "second prompt"
        await pilot.press("ctrl+enter")
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
        conversation = pilot.app.query_one("#conversation-pane", Static)

        assert "Assistant (streaming)" in str(conversation.content)
        assert "hello" in str(conversation.content)

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
    ) -> None:
        self.closed = False
        self.fetch_count = 0
        self.events = events or []
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
        for event in self.events:
            if event.sequence > after_sequence:
                yield event

    async def aclose(self) -> None:
        self.closed = True
