"""Integration tests for interactive CLI chat and attach commands."""

import asyncio
import json
import subprocess
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from glassbox.cli import main
from glassbox.cli.interactive_launch import InteractiveLaunchMode
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionStarted
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import ChangesetSourceKind
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import open_database
from glassbox.web import WebServerConfig
from tests.integration.cli_test_support import _make_approval_runtime_context
from tests.integration.cli_test_support import _make_ask_user_runtime_context
from tests.integration.cli_test_support import _read_session_events
from tests.integration.cli_test_support import _run_baseline_session
from tests.integration.cli_test_support import _seed_pending_approval


class FakeChatDashboardServer:
    def __init__(self, *, host: str, port: int) -> None:
        self.config = WebServerConfig(host=host, port=port)
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


class FailingChatDashboardServer(FakeChatDashboardServer):
    async def start(self) -> None:
        raise RuntimeError("web server failed to start")


def test_cli_chat_keeps_session_open_for_multiple_prompts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    interactive_inputs = iter(
        [
            "Inspect the repository",
            "Now summarize the tests.",
            "/exit",
        ]
    )

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    exit_code = main(
        [
            "session",
            "chat",
            "--no-dashboard",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        sessions = repository.list_sessions()
        assert len(sessions) == 1
        session_id = sessions[0].session_id
        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert "Started session" in captured.out
    assert "Queued user message: Inspect the repository" in captured.out
    assert "Assistant: I received your request: Inspect the repository" in captured.out
    assert "Queued user message: Now summarize the tests." in captured.out
    assert (
        "Assistant: I received your request: Now summarize the tests." in captured.out
    )
    assert "Leaving interactive session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.current_turn_id is None
    assert [message.role for message in transcript] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert transcript[0].parts[0].text == "Inspect the repository"
    assert transcript[1].parts[0].text == (
        "I received your request: Inspect the repository"
    )
    assert transcript[2].parts[0].text == "Now summarize the tests."
    assert transcript[3].parts[0].text == (
        "I received your request: Now summarize the tests."
    )


def test_cli_chat_plain_flag_uses_line_mode_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: "/exit",
    )

    exit_code = main(
        [
            "session",
            "chat",
            "--plain",
            "--no-dashboard",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Attached to session" in captured.out
    assert "Leaving interactive session" in captured.out


def test_cli_chat_plain_supports_review_shortcuts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "app.py").write_text("print('plain review')\n", encoding="utf-8")
    interactive_inputs = iter(
        [
            "/review create Plain review parity",
            "/review workup",
            "/review status",
            "/review verify",
            "/review dashboard",
            "/exit",
        ]
    )

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    exit_code = main(
        [
            "session",
            "chat",
            "--plain",
            "--no-dashboard",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        session_id = repository.list_sessions()[0].session_id
        changesets = repository.list_changesets(
            session_id=session_id,
            include_archived=False,
            limit=10,
        )
        sources = repository.list_changeset_sources(
            session_id,
            changesets[0].changeset_id,
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert len(changesets) == 1
    assert changesets[0].objective == "Plain review parity"
    assert sources[0].source_kind == ChangesetSourceKind.WORKSPACE_DIFF
    assert "Created review changeset" in captured.out
    assert "Guided workup for changeset" in captured.out
    assert "Feedback status for" in captured.out
    assert "Previewed verification for" in captured.out
    assert "Evidence guidance: Missing lifecycle brief" in captured.out
    assert "Evidence guidance: Live evidence: none recorded" in captured.out
    assert (
        "Dashboard: unavailable; run glassbox dashboard serve --cwd ." in captured.out
    )
    assert "No tests, staging, commit, push, PR, or merge was run." in captured.out


def test_cli_chat_plain_supports_review_fixup_shortcut(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "app.py").write_text("print('plain fixup')\n", encoding="utf-8")
    db_path, session_id = _run_baseline_session(tmp_path, prompt="prepare fixup")
    capsys.readouterr()
    create_exit = main(
        [
            "changeset",
            "create",
            "--from",
            "workspace-diff",
            "--session",
            str(session_id),
            "--objective",
            "Plain fixup parity",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    created = json.loads(capsys.readouterr().out)
    feedback_exit = main(
        [
            "changeset",
            "feedback",
            "add",
            created["changeset_id"],
            "--kind",
            "requested_change",
            "--summary",
            "Wire the plain review fixup shortcut",
            "--provenance",
            "reviewer",
            "--file",
            "app.py",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    feedback = json.loads(capsys.readouterr().out)
    feedback_id = feedback["feedback"]["feedback_id"]
    interactive_inputs = iter(
        [
            f"/review status {created['changeset_id']}",
            f"/review fixup {feedback_id}",
            "/exit",
        ]
    )

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    exit_code = main(
        [
            "session",
            "chat",
            "--plain",
            "--no-dashboard",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        inventories = repository.list_review_feedback_fixup_inventories(
            UUID(created["session_id"]),
            UUID(feedback_id),
        )
    finally:
        connection.close()

    assert create_exit == 0
    assert feedback_exit == 0
    assert exit_code == 0
    assert len(inventories) == 1
    assert "Evidence guidance: Missing fixup inventory" in captured.out
    assert f"glassbox changeset feedback fixup {feedback_id} --cwd ." in captured.out
    assert "Recorded fixup inventory for feedback" in captured.out
    assert "No tests, staging, commit, push, PR, or merge was run." in captured.out


def test_cli_chat_tui_flag_rejects_non_interactive_environment(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    exit_code = main(
        [
            "session",
            "chat",
            "--tui",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "full-screen TUI launch requires interactive stdin/stdout" in captured.err
    assert db_path.exists() is False


def test_cli_chat_tui_flag_launches_terminal_app(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    launched_session_ids: list[UUID] = []

    monkeypatch.setattr(
        "glassbox.cli.interactive_commands.interactive_launch_options_from_args",
        lambda args, *, tui_available: InteractiveLaunchOptions(
            requested_mode=InteractiveLaunchMode.TUI,
            default_mode=InteractiveLaunchMode.PLAIN,
            stdin_is_tty=True,
            stdout_is_tty=True,
            term="xterm-256color",
            ci=False,
            tui_available=tui_available,
        ),
    )

    async def fake_run_tui_app(app: Any) -> None:
        launched_session_ids.append(app.state.header.session_id)
        await app.close_client()

    monkeypatch.setattr(
        "glassbox.cli.interactive_commands.run_tui_app",
        fake_run_tui_app,
    )

    exit_code = main(
        [
            "session",
            "chat",
            "--tui",
            "--no-dashboard",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "hello from tui",
        ]
    )
    _ = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        sessions = repository.list_sessions()
    finally:
        connection.close()

    assert exit_code == 0
    assert len(sessions) == 1
    assert launched_session_ids == [sessions[0].session_id]


def test_cli_attach_tui_flag_launches_terminal_app_for_local_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    launched: list[tuple[UUID, str | None]] = []

    monkeypatch.setattr(
        "glassbox.cli.interactive_commands.interactive_launch_options_from_args",
        lambda args, *, tui_available: InteractiveLaunchOptions(
            requested_mode=InteractiveLaunchMode.TUI,
            default_mode=InteractiveLaunchMode.PLAIN,
            stdin_is_tty=True,
            stdout_is_tty=True,
            term="xterm-256color",
            ci=False,
            tui_available=tui_available,
        ),
    )

    async def fake_run_tui_app(app: Any) -> None:
        launched.append((app.state.header.session_id, app.state.header.runtime_owner))
        await app.close_client()

    monkeypatch.setattr(
        "glassbox.cli.interactive_commands.run_tui_app",
        fake_run_tui_app,
    )

    exit_code = main(
        [
            "session",
            "attach",
            str(session_id),
            "--tui",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert launched == [(session_id, "persisted local session")]


def test_cli_attach_tui_flag_presents_completed_session_as_historical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionCompleted(reason="done"),
            )
        )
    finally:
        connection.close()

    launched: list[tuple[TerminalMode, TerminalStreamStatus]] = []

    monkeypatch.setattr(
        "glassbox.cli.interactive_commands.interactive_launch_options_from_args",
        lambda args, *, tui_available: InteractiveLaunchOptions(
            requested_mode=InteractiveLaunchMode.TUI,
            default_mode=InteractiveLaunchMode.PLAIN,
            stdin_is_tty=True,
            stdout_is_tty=True,
            term="xterm-256color",
            ci=False,
            tui_available=tui_available,
        ),
    )

    async def fake_run_tui_app(app: Any) -> None:
        launched.append((app.state.header.mode, app.state.header.stream_status))
        await app.close_client()

    monkeypatch.setattr(
        "glassbox.cli.interactive_commands.run_tui_app",
        fake_run_tui_app,
    )

    exit_code = main(
        [
            "session",
            "attach",
            str(session_id),
            "--tui",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert launched == [
        (TerminalMode.HISTORICAL_ONLY, TerminalStreamStatus.HISTORICAL_ONLY)
    ]


def test_cli_run_uses_workspace_profile_runtime_defaults(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    _write_workspace_profile(
        tmp_path,
        runtime={
            "model_name": "anthropic:claude-sonnet-4",
            "approval_mode": "never",
        },
    )

    exit_code = main(
        [
            "session",
            "run",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()
    started_event = _single_session_started_event(db_path)

    assert exit_code == 0
    assert started_event.model_name == "anthropic:claude-sonnet-4"
    assert started_event.approval_mode == "never"


def test_cli_run_explicit_flags_override_workspace_profile_defaults(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    _write_workspace_profile(
        tmp_path,
        runtime={
            "model_name": "anthropic:claude-sonnet-4",
            "approval_mode": "never",
        },
    )

    exit_code = main(
        [
            "session",
            "run",
            "--model-name",
            "openai:gpt-5.4",
            "--approval-mode",
            "confirm",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()
    started_event = _single_session_started_event(db_path)

    assert exit_code == 0
    assert started_event.model_name == "openai:gpt-5.4"
    assert started_event.approval_mode == "confirm"


def test_cli_run_explicit_autonomy_flags_override_workspace_profile_defaults(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    _write_workspace_profile(
        tmp_path,
        runtime={
            "autonomy_mode": "inspect",
            "autonomy_budget_preset": "inspect",
        },
    )

    exit_code = main(
        [
            "session",
            "run",
            "--autonomy-mode",
            "test-driven",
            "--autonomy-budget-preset",
            "test-driven",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    started_event = _single_session_started_event(db_path)

    assert exit_code == 0
    assert "Autonomy: test-driven; budget test-driven" in captured.out
    assert started_event.autonomy_mode == "test-driven"
    assert started_event.autonomy_budget_preset == "test-driven"
    assert started_event.autonomy_budget is not None
    assert started_event.autonomy_budget.max_command_operations > 0


def test_cli_run_rejects_invalid_workspace_profile(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_workspace_profile(tmp_path, runtime={"approval_mode": "always"})

    exit_code = main(["session", "run", "--cwd", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "invalid workspace profile" in captured.err


def test_cli_attach_keeps_existing_idle_session_open_for_new_prompts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    interactive_inputs = iter(["Now summarize the tests.", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    _ = capsys.readouterr()
    exit_code = main(
        [
            "session",
            "attach",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert f"Attached to session {session_id}" in captured.out
    assert "Queued user message: Now summarize the tests." in captured.out
    assert (
        "Assistant: I received your request: Now summarize the tests." in captured.out
    )
    assert "Leaving interactive session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.current_turn_id is None
    assert transcript[-2].role == "user"
    assert transcript[-2].parts[0].text == "Now summarize the tests."
    assert transcript[-1].role == "assistant"
    assert transcript[-1].parts[0].text == (
        "I received your request: Now summarize the tests."
    )


def test_cli_attach_answers_pending_question_for_existing_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    interactive_inputs = iter(["blue", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    try:
        exit_code = main(
            [
                "session",
                "run",
                "Pick a colour.",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        _ = capsys.readouterr()

        repository = runtime_context.repositories.sessions
        session_id = repository.list_sessions()[0].session_id

        assert exit_code == 0

        exit_code = main(
            [
                "session",
                "attach",
                str(session_id),
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()

        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert f"Attached to session {session_id}" in captured.out
    assert "Pending question:" in captured.out
    assert "What colour should I use?" in captured.out
    assert "Answer submitted for question" in captured.out
    assert "Assistant: I will use: blue" in captured.out
    assert "Leaving interactive session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.pending_question_id is None
    assert transcript[-1].role == "assistant"
    assert transcript[-1].parts[0].text == "I will use: blue"


def test_cli_chat_routes_pending_question_answers_without_question_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    interactive_inputs = iter(["Pick a colour.", "blue", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    try:
        exit_code = main(
            [
                "session",
                "chat",
                "--no-dashboard",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()

        repository = runtime_context.repositories.sessions
        session_id = repository.list_sessions()[0].session_id
        transcript = repository.list_transcript_messages(session_id)
        state = repository.get_session_state(session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert "Interactive mode: type the next prompt" in captured.out
    assert "Question asked" in captured.out
    assert "Pending question:" in captured.out
    assert "Interactive mode: answer the pending question" in captured.out
    assert "Answer submitted for question" in captured.out
    assert "Assistant: I will use: blue" in captured.out
    assert "Leaving interactive session" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.pending_question_id is None
    assert transcript[-1].parts[0].text == "I will use: blue"


def test_cli_attach_approval_mode_requires_slash_commands_and_supports_status_help(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, approval_id = _seed_pending_approval(tmp_path)
    interactive_inputs = iter(["hello", "/status", "/help", "/approve", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    _ = capsys.readouterr()
    exit_code = main(
        [
            "session",
            "attach",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    persisted_events = _read_session_events(db_path, session_id)

    assert exit_code == 0
    assert f"Attached to session {session_id}" in captured.out
    assert f"{approval_id}" in captured.out
    assert "Freeform text is disabled until you use /approve or /deny." in captured.out
    assert f"Session {session_id}" in captured.out
    assert "Interactive commands:" in captured.out
    assert "Approval resolved: approved by user" in captured.out
    assert persisted_events[-1].event_type == "ApprovalResolved"


def test_cli_attach_supports_deny_slash_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, _approval_id = _seed_pending_approval(tmp_path)
    interactive_inputs = iter(["/deny", "/exit"])

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    _ = capsys.readouterr()
    exit_code = main(
        [
            "session",
            "attach",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    persisted_events = _read_session_events(db_path, session_id)

    assert exit_code == 0
    assert "Approval resolved: denied by user" in captured.out
    assert persisted_events[-1].event_type == "ApprovalResolved"
    assert isinstance(persisted_events[-1].payload, ApprovalResolved)
    assert persisted_events[-1].payload.decision == ApprovalDecision.DENIED


def test_cli_chat_redraws_prompt_and_routes_answer_after_question_arrives_mid_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_ask_user_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    read_count = 0

    async def fake_read_interactive_input(prompt: str) -> str:
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            session_id = runtime_context.repositories.sessions.list_sessions()[
                0
            ].session_id
            await runtime_context.services.session_service.submit_user_message(
                session_id,
                "Pick a colour.",
            )
            await asyncio.sleep(0)
            return "blue"
        return "/exit"

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input_async",
        fake_read_interactive_input,
    )

    try:
        exit_code = main(
            [
                "session",
                "chat",
                "--no-dashboard",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()

        session_id = runtime_context.repositories.sessions.list_sessions()[0].session_id
        state = runtime_context.repositories.sessions.get_session_state(session_id)
        transcript = runtime_context.repositories.sessions.list_transcript_messages(
            session_id
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert "Question asked (" in captured.out
    assert (
        "Interactive mode: type the next prompt, or use /status, /help, or /exit.\n"
        "prompt> "
    ) in captured.out
    assert "Answer submitted for question" in captured.out
    assert "Assistant: I will use: blue" in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.pending_question_id is None
    assert transcript[-1].parts[0].text == "I will use: blue"


def test_cli_cancel_reports_live_runtime_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from datetime import UTC
    from datetime import datetime

    from glassbox.runtime.daemon import RuntimeOwnerRecord
    from glassbox.runtime.daemon import RuntimeOwnerStatus

    db_path, session_id = _run_baseline_session(tmp_path)
    baseline_db_path = db_path

    monkeypatch.setattr(
        "glassbox.cli.interactive_commands.inspect_runtime_owner",
        lambda cwd, db_path=None: RuntimeOwnerStatus(
            state="running",
            record=RuntimeOwnerRecord(
                pid=12345,
                workspace_root=tmp_path,
                database_path=baseline_db_path,
                host="127.0.0.1",
                port=9999,
                dashboard_url="http://127.0.0.1:9999/",
                started_at=datetime(2025, 1, 1, tzinfo=UTC),
            ),
            health="unreachable",
        ),
    )

    exit_code = main(
        [
            "session",
            "cancel",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert (
        "live runtime unavailable at http://127.0.0.1:9999/; cannot cancel session"
    ) in captured.err


def test_cli_cancel_clears_stale_owner_before_local_attempt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    owner_path = tmp_path / ".glassbox" / "runtime-owner.json"
    owner_path.write_text(
        json.dumps(
            {
                "pid": 999999,
                "workspace_root": str(tmp_path),
                "database_path": str(db_path),
                "host": "127.0.0.1",
                "port": 8765,
                "dashboard_url": "http://127.0.0.1:8765/",
                "started_at": "2025-01-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "session",
            "cancel",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "has no cancellable active turn" in captured.err
    assert owner_path.exists() is False


def test_cli_chat_redraws_prompt_and_routes_approval_after_request_arrives_mid_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_context, connection = _make_approval_runtime_context(tmp_path)
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    read_count = 0

    async def fake_read_interactive_input(prompt: str) -> str:
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            session_id = runtime_context.repositories.sessions.list_sessions()[
                0
            ].session_id
            await runtime_context.services.session_service.submit_user_message(
                session_id,
                "Apply the patch.",
            )
            await asyncio.sleep(0)
            return "/approve"
        return "/exit"

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.open_runtime_context",
        lambda cwd, db_path=None: nullcontext(runtime_context),
    )
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input_async",
        fake_read_interactive_input,
    )

    try:
        exit_code = main(
            [
                "session",
                "chat",
                "--no-dashboard",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        captured = capsys.readouterr()

        session_id = runtime_context.repositories.sessions.list_sessions()[0].session_id
        state = runtime_context.repositories.sessions.get_session_state(session_id)
        persisted_events = runtime_context.repositories.sessions.read_session_events(
            session_id
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert "Approval requested: apply_patch (approval required:" in captured.out
    assert (
        "Interactive mode: type the next prompt, or use /status, /help, or /exit.\n"
        "prompt> "
    ) in captured.out
    assert "Approval resolved: approved by user" in captured.out
    assert "Assistant: Patch applied." in captured.out
    assert state is not None
    assert state.status == "running"
    assert state.pending_approval_id is None
    assert any(
        isinstance(event.payload, ApprovalResolved) for event in persisted_events
    )


def test_cli_chat_starts_dashboard_sidecar_and_records_live_dashboard_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    built_servers: list[FakeChatDashboardServer] = []

    def fake_build_web_server(runtime_context, *, host: str, port: int):
        server = FakeChatDashboardServer(host=host, port=port)
        built_servers.append(server)
        return server

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.build_web_server",
        fake_build_web_server,
    )
    monkeypatch.setattr(
        "glassbox.cli.runtime_runner._dashboard_port_available",
        lambda host, port: True,
    )
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: "/exit",
    )

    exit_code = main(
        [
            "session",
            "chat",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        sessions = repository.list_sessions()
        assert len(sessions) == 1
        session_id = sessions[0].session_id
        started_event = next(
            event.payload
            for event in repository.read_session_events(session_id)
            if isinstance(event.payload, SessionStarted)
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert len(built_servers) == 1
    assert built_servers[0].started is True
    assert built_servers[0].stopped is True
    assert (
        "Dashboard available at "
        f"http://127.0.0.1:8765/?session={session_id}" in captured.out
    )
    assert started_event.dashboard_url == "http://127.0.0.1:8765/"


def test_cli_chat_continues_without_dashboard_when_default_startup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    def fake_build_web_server(runtime_context, *, host: str, port: int):
        return FailingChatDashboardServer(host=host, port=port)

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.build_web_server",
        fake_build_web_server,
    )
    monkeypatch.setattr(
        "glassbox.cli.runtime_runner._dashboard_port_available",
        lambda host, port: True,
    )
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: "/exit",
    )

    exit_code = main(
        [
            "session",
            "chat",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        sessions = repository.list_sessions()
        assert len(sessions) == 1
        session_id = sessions[0].session_id
        started_event = next(
            event.payload
            for event in repository.read_session_events(session_id)
            if isinstance(event.payload, SessionStarted)
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert "Warning: dashboard unavailable at http://127.0.0.1:8765/" in captured.err
    assert "Dashboard available at " not in captured.out
    assert started_event.dashboard_url is None


@pytest.mark.parametrize("mode_args", [[], ["--tui"]])
def test_cli_chat_reports_default_dashboard_port_conflict_with_suggestion(
    mode_args: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    def fail_if_built(*args, **kwargs):
        raise AssertionError("dashboard sidecar should not start on a known busy port")

    def fail_if_prompted(prompt: str) -> Any:
        raise AssertionError(f"interactive prompt should not be reached: {prompt}")

    def fake_dashboard_port_available(host: str, port: int) -> bool:
        return port != 8765

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.build_web_server",
        fail_if_built,
    )
    monkeypatch.setattr(
        "glassbox.cli.runtime_runner._dashboard_port_available",
        fake_dashboard_port_available,
    )
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        fail_if_prompted,
    )

    if "--tui" in mode_args:
        monkeypatch.setattr(
            "glassbox.cli.interactive_commands.interactive_launch_options_from_args",
            lambda args, *, tui_available: InteractiveLaunchOptions(
                requested_mode=InteractiveLaunchMode.TUI,
                default_mode=InteractiveLaunchMode.PLAIN,
                stdin_is_tty=True,
                stdout_is_tty=True,
                term="xterm-256color",
                ci=False,
                tui_available=tui_available,
            ),
        )

        async def fail_if_tui_runs(app: Any) -> None:
            raise AssertionError("TUI should not run without a dashboard port decision")

        monkeypatch.setattr(
            "glassbox.cli.interactive_commands.run_tui_app",
            fail_if_tui_runs,
        )

    exit_code = main(
        [
            "session",
            "chat",
            *mode_args,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        sessions = SQLiteSessionRepository(connection).list_sessions()
    finally:
        connection.close()

    assert exit_code == 1
    assert captured.err.strip() == (
        "Dashboard port 8765 is already in use at http://127.0.0.1:8765/.\n"
        "Try a different dashboard port: "
        "glassbox session chat --dashboard-port 8766\n"
        "You can also pass --no-dashboard to start without the co-hosted dashboard."
    )
    assert sessions == []


def test_cli_chat_fails_when_explicit_dashboard_binding_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    def fail_if_prompted(prompt: str) -> Any:
        raise AssertionError(f"interactive prompt should not be reached: {prompt}")

    def fake_build_web_server(runtime_context, *, host: str, port: int):
        return FailingChatDashboardServer(host=host, port=port)

    monkeypatch.setattr(
        "glassbox.cli.runtime_runner.build_web_server",
        fake_build_web_server,
    )
    monkeypatch.setattr(
        "glassbox.cli.runtime_runner._dashboard_port_available",
        lambda host, port: True,
    )
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        fail_if_prompted,
    )

    exit_code = main(
        [
            "session",
            "chat",
            "--dashboard-port",
            "9876",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        sessions = SQLiteSessionRepository(connection).list_sessions()
    finally:
        connection.close()

    assert exit_code == 1
    assert (
        "dashboard startup failed at http://127.0.0.1:9876/: web server failed to start"
        == captured.err.strip()
    )
    assert sessions == []


def test_cli_chat_can_disable_dashboard_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    def fail_if_built(*args, **kwargs):
        raise AssertionError("dashboard sidecar should not be built")

    monkeypatch.setattr("glassbox.cli.runtime_runner.build_web_server", fail_if_built)
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: "/exit",
    )

    exit_code = main(
        [
            "session",
            "chat",
            "--no-dashboard",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        session_id = repository.list_sessions()[0].session_id
        started_event = next(
            event.payload
            for event in repository.read_session_events(session_id)
            if isinstance(event.payload, SessionStarted)
        )
    finally:
        connection.close()

    assert exit_code == 0
    assert "Dashboard available at " not in captured.out
    assert started_event.dashboard_url is None


def test_cli_attach_rejects_unknown_session_id(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    unknown_session_id = UUID("00000000-0000-0000-0000-000000000001")

    exit_code = main(
        [
            "session",
            "attach",
            str(unknown_session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == f"unknown session_id: {unknown_session_id}"


def test_cli_attach_rejects_completed_session(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionCompleted(reason="done"),
            )
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    exit_code = main(
        [
            "session",
            "attach",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == (
        f"cannot attach session {session_id} in status completed"
    )


def test_cli_attach_rejects_failed_session(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionFailed(
                    error_message="model backend unavailable",
                    retryable=True,
                ),
            )
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    exit_code = main(
        [
            "session",
            "attach",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == (
        f"cannot attach session {session_id} in status failed"
    )


def _single_session_started_event(db_path: Path) -> SessionStarted:
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        sessions = repository.list_sessions()
        assert len(sessions) == 1
        return next(
            event.payload
            for event in repository.read_session_events(sessions[0].session_id)
            if isinstance(event.payload, SessionStarted)
        )
    finally:
        connection.close()


def _write_workspace_profile(
    tmp_path: Path,
    *,
    runtime: dict[str, object],
) -> None:
    payload = {
        "profile_version": 1,
        "runtime": runtime,
    }
    (tmp_path / "glassbox.profile.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
