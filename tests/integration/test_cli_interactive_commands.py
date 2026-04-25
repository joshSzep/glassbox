"""Integration tests for interactive CLI chat and attach commands."""

import asyncio
import json
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from glassbox.cli import main
from glassbox.core.events import ApprovalResolved
from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionStarted
from glassbox.core.types import ApprovalDecision
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


def test_cli_run_rejects_invalid_workspace_profile(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_workspace_profile(tmp_path, runtime={"approval_mode": "always"})

    exit_code = main(["run", "--cwd", str(tmp_path)])
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
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: "/exit",
    )

    exit_code = main(
        [
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
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: "/exit",
    )

    exit_code = main(
        [
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
        "glassbox.cli.interactive_session._read_interactive_input",
        fail_if_prompted,
    )

    exit_code = main(
        [
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
