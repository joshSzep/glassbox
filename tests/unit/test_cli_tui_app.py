"""Tests for the initial Textual terminal app boundary."""

import asyncio
from collections.abc import AsyncIterator

from textual.widgets import Static

from glassbox.cli.interactive_client import InteractiveSessionSnapshot
from glassbox.cli.interactive_launch import InteractiveLaunchMode
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui import GlassboxTerminalApp
from glassbox.cli.tui import create_session_tui_app
from glassbox.cli.tui import create_tui_app
from glassbox.cli.tui.state import session_dashboard_url
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import ApprovalId
from glassbox.core.ids import QuestionId
from glassbox.core.ids import new_session_id
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
    assert app.state.dashboard_url == (
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
        composer = pilot.app.query_one("#composer", Static)

        assert "Glassbox session" in str(header.content)
        assert f"?session={app.state.session_id}" in str(header.content)
        assert "last event sequence 7" in str(conversation.content)
        assert "plain composer ready" in str(composer.content)

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
    assert app.state.dashboard_url == (
        f"http://127.0.0.1:8765/?session={app.state.session_id}"
    )


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
    closed = False
    fetch_count = 0

    @property
    def session_id(self):
        return new_session_id()

    async def fetch_snapshot(self) -> InteractiveSessionSnapshot:
        self.fetch_count += 1
        return _snapshot()

    async def submit_message(self, text: str) -> None:
        return None

    async def submit_answer(self, question_id: QuestionId, answer: str) -> None:
        return None

    async def resolve_approval(
        self,
        approval_id: ApprovalId,
        decision: ApprovalDecision,
    ) -> None:
        return None

    def stream_events(self, *, after_sequence: int = 0) -> AsyncIterator[EventEnvelope]:
        raise NotImplementedError

    async def aclose(self) -> None:
        self.closed = True
