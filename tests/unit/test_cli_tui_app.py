"""Tests for the initial Textual terminal app boundary."""

import asyncio
from collections.abc import AsyncIterator
from typing import cast

from textual.widgets import Static

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.interactive_launch import InteractiveLaunchMode
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui import GlassboxTerminalApp
from glassbox.cli.tui import create_session_tui_app
from glassbox.cli.tui import create_tui_app
from glassbox.cli.tui.commands import TerminalCommandId
from glassbox.cli.tui.keybindings import TUI_KEY_BINDINGS
from glassbox.cli.tui.state import session_dashboard_url
from glassbox.cli.tui.widgets import CommandPaletteWidget
from glassbox.cli.tui.widgets import ComposerWidget
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import AssistantMessageStarted
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_session_id
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


def test_tui_app_submits_multiline_prompt_and_clears_draft() -> None:
    asyncio.run(_run_prompt_submit_test())


def test_tui_app_preserves_draft_during_live_updates() -> None:
    asyncio.run(_run_draft_preservation_test())


def test_tui_app_keeps_local_prompt_history() -> None:
    asyncio.run(_run_prompt_history_test())


def test_tui_app_opens_filters_and_closes_command_palette() -> None:
    asyncio.run(_run_command_palette_test())


def test_tui_app_executes_palette_clipboard_and_approval_commands() -> None:
    asyncio.run(_run_command_execution_test())


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
        typed_app = cast(GlassboxTerminalApp, pilot.app)
        assert typed_app.state.composer.text == ""

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
    await app.close_client()

    assert client.closed is True


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
    def __init__(self, *, events: list[EventEnvelope] | None = None) -> None:
        self.closed = False
        self.fetch_count = 0
        self.events = events or []
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
        self.submitted_messages.append(text)

    async def submit_answer(self, question_id: QuestionId, answer: str) -> None:
        self.submitted_answers.append((question_id, answer))

    async def resolve_approval(
        self,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None:
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
