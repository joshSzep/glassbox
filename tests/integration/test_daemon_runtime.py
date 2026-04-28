"""Integration tests for the workspace-scoped daemon runtime owner."""

import json
import os
import socket
from datetime import UTC
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from glassbox.cli import main
from glassbox.cli.interactive_launch import InteractiveLaunchMode
from glassbox.cli.interactive_launch import InteractiveLaunchOptions
from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionCompleted
from glassbox.runtime.daemon import stop_runtime_owner
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import open_database
from tests.integration.cli_test_support import _run_baseline_session


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return int(handle.getsockname()[1])


def _runtime_owner_path(workspace_root: Path) -> Path:
    return workspace_root / ".glassbox" / "runtime-owner.json"


def _stop_daemon_if_running(workspace_root: Path) -> None:
    owner_path = _runtime_owner_path(workspace_root)
    if owner_path.exists():
        main(["daemon", "stop", "--cwd", str(workspace_root)])


def _write_owner_metadata(
    workspace_root: Path,
    *,
    pid: int,
    port: int = 8765,
    db_path: Path | None = None,
) -> None:
    owner_path = _runtime_owner_path(workspace_root)
    owner_path.parent.mkdir(parents=True, exist_ok=True)
    database_path = db_path or workspace_root / ".glassbox" / "glassbox.sqlite3"
    owner_path.write_text(
        json.dumps(
            {
                "pid": pid,
                "workspace_root": str(workspace_root),
                "database_path": str(database_path),
                "host": "127.0.0.1",
                "port": port,
                "dashboard_url": f"http://127.0.0.1:{port}/",
                "started_at": "2025-01-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_cli_help_lists_daemon_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "daemon" in captured.out


def test_daemon_status_help_lists_json_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["daemon", "status", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "--json" in captured.out


def test_daemon_help_hides_internal_run_owner_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["daemon", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "run-owner" not in captured.out


def test_daemon_start_status_duplicate_rejection_and_stop(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    port = _reserve_port()

    try:
        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--port",
                str(port),
            ]
        )
        start_capture = capsys.readouterr()

        assert exit_code == 0
        assert f"Daemon running at http://127.0.0.1:{port}/" in start_capture.out

        exit_code = main(["daemon", "status", "--cwd", str(tmp_path)])
        status_capture = capsys.readouterr()

        assert exit_code == 0
        assert "Status: running" in status_capture.out
        assert "Health: ok" in status_capture.out
        assert "Workspace:" in status_capture.out
        assert "Owner metadata:" in status_capture.out
        assert "Session index:" in status_capture.out
        assert "Attach: glassbox session attach SESSION_ID" in status_capture.out
        assert (
            "Cancel active turn: glassbox session cancel SESSION_ID"
            in status_capture.out
        )
        assert "Stop: glassbox daemon stop" in status_capture.out

        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--port",
                str(port),
            ]
        )
        duplicate_capture = capsys.readouterr()

        assert exit_code == 1
        assert "workspace runtime is owned by glassbox daemon" in duplicate_capture.err

        exit_code = main(
            [
                "session",
                "message",
                str(uuid4()),
                "hello",
                "--cwd",
                str(tmp_path),
            ]
        )
        guarded_capture = capsys.readouterr()

        assert exit_code == 1
        assert "cannot submit a message locally" in guarded_capture.err

        exit_code = main(["daemon", "stop", "--cwd", str(tmp_path)])
        stop_capture = capsys.readouterr()

        assert exit_code == 0
        assert "Stopped daemon pid" in stop_capture.out

        exit_code = main(["daemon", "status", "--cwd", str(tmp_path)])
        stopped_capture = capsys.readouterr()

        assert exit_code == 0
        assert "Status: not running" in stopped_capture.out
    finally:
        _stop_daemon_if_running(tmp_path)


def test_daemon_status_json_reports_discovery_and_health(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    port = _reserve_port()

    try:
        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--port",
                str(port),
            ]
        )
        _ = capsys.readouterr()

        assert exit_code == 0

        exit_code = main(["daemon", "status", "--cwd", str(tmp_path), "--json"])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert exit_code == 0
        assert payload["state"] == "running"
        assert payload["health"] == "ok"
        assert payload["workspace_root"] == str(tmp_path.resolve())
        assert payload["dashboard_url"] == f"http://127.0.0.1:{port}/"
        assert payload["health_url"] == f"http://127.0.0.1:{port}/healthz"
        assert payload["metadata_path"].endswith(".glassbox/runtime-owner.json")
        assert payload["stdout_log_path"].endswith(".glassbox/runtime-owner.stdout.log")
        assert payload["stderr_log_path"].endswith(".glassbox/runtime-owner.stderr.log")
        assert payload["commands"]["attach"].startswith(
            "glassbox session attach SESSION_ID --cwd "
        )
        assert payload["commands"]["cancel"].startswith(
            "glassbox session cancel SESSION_ID --cwd "
        )
        assert payload["commands"]["status_json"].endswith(" --json")
    finally:
        _stop_daemon_if_running(tmp_path)


def test_daemon_status_reports_not_running_discovery(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["daemon", "status", "--cwd", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Status: not running" in captured.out
    assert "Runtime owner: none" in captured.out
    assert "Start: glassbox daemon start" in captured.out
    assert "Owner metadata:" in captured.out


def test_daemon_start_recovers_stale_owner_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    port = _reserve_port()
    owner_path = _runtime_owner_path(tmp_path)
    owner_path.parent.mkdir(parents=True, exist_ok=True)
    owner_path.write_text(
        json.dumps(
            {
                "pid": 999999,
                "workspace_root": str(tmp_path),
                "database_path": str(tmp_path / ".glassbox" / "glassbox.sqlite3"),
                "host": "127.0.0.1",
                "port": port,
                "dashboard_url": f"http://127.0.0.1:{port}/",
                "started_at": "2025-01-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--port",
                str(port),
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "Recovered stale workspace daemon owner metadata." in captured.out

        exit_code = main(["daemon", "stop", "--cwd", str(tmp_path)])
        stop_capture = capsys.readouterr()

        assert exit_code == 0
        assert "Stopped daemon pid" in stop_capture.out
    finally:
        _stop_daemon_if_running(tmp_path)


def test_daemon_status_reports_stale_recovery_commands(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_owner_metadata(tmp_path, pid=999999)

    exit_code = main(["daemon", "status", "--cwd", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Status: stale" in captured.out
    assert "Health: unavailable (owner process is not running)" in captured.out
    assert "Recover: glassbox daemon start" in captured.out
    assert "Clear stale owner: glassbox daemon stop" in captured.out
    assert "Next: glassbox daemon stop" in captured.out
    assert "then glassbox daemon start" in captured.out


def test_daemon_start_reports_process_startup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _ExitedProcess:
        pid = 4242

        def poll(self) -> int:
            return 1

    monkeypatch.setattr(
        "glassbox.runtime.daemon.subprocess.Popen",
        lambda *args, **kwargs: _ExitedProcess(),
    )

    exit_code = main(
        [
            "daemon",
            "start",
            "--cwd",
            str(tmp_path),
            "--port",
            str(_reserve_port()),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "daemon failed to reach a healthy startup state" in captured.err
    assert "runtime-owner.stderr.log" in captured.err


def test_daemon_start_reports_port_conflict(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        handle.listen()
        port = int(handle.getsockname()[1])

        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--port",
                str(port),
            ]
        )
        captured = capsys.readouterr()

    assert exit_code == 1
    assert "requested host/port appears unavailable" in captured.err
    assert "runtime-owner.stderr.log" in captured.err
    assert not _runtime_owner_path(tmp_path).exists()


def test_daemon_status_reports_unreachable_health_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_owner_metadata(tmp_path, pid=os.getpid(), port=9999)
    monkeypatch.setattr(
        "glassbox.runtime.daemon._probe_healthz",
        lambda dashboard_url: "unreachable",
    )

    exit_code = main(["daemon", "status", "--cwd", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Status: running" in captured.out
    assert "Health: unreachable" in captured.out
    assert "Inspect health: http://127.0.0.1:9999/healthz" in captured.out
    assert "Recover: glassbox daemon stop" in captured.out
    assert "Next: inspect http://127.0.0.1:9999/healthz" in captured.out


def test_daemon_stop_timeout_reports_pid_and_keeps_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_owner_metadata(tmp_path, pid=12345)
    monkeypatch.setattr(
        "glassbox.runtime.daemon._process_is_alive",
        lambda pid: True,
    )
    monkeypatch.setattr("glassbox.runtime.daemon.os.kill", lambda pid, signum: None)

    with pytest.raises(ValueError, match="daemon pid 12345 did not shut down"):
        stop_runtime_owner(tmp_path, shutdown_timeout_seconds=0.01)

    assert _runtime_owner_path(tmp_path).exists()


def test_cli_attach_routes_live_session_through_daemon_and_can_reattach(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    port = _reserve_port()
    interactive_inputs = iter(
        [
            "Now summarize the tests.",
            "/exit",
            "Add one more note.",
            "/exit",
        ]
    )

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    try:
        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
                "--port",
                str(port),
            ]
        )
        _ = capsys.readouterr()

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
        first_capture = capsys.readouterr()

        assert exit_code == 0
        assert f"Attached to live session {session_id}" in first_capture.out
        assert "Queued user message: Now summarize the tests." in first_capture.out
        assert (
            "Assistant: I received your request: Now summarize the tests."
            in first_capture.out
        )
        assert "Leaving interactive session" in first_capture.out

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
        second_capture = capsys.readouterr()

        assert exit_code == 0
        assert f"Attached to live session {session_id}" in second_capture.out
        assert "Queued user message: Add one more note." in second_capture.out
        assert (
            "Assistant: I received your request: Add one more note."
            in second_capture.out
        )

        connection = open_database(db_path)
        try:
            repository = SQLiteSessionRepository(connection)
            transcript = repository.list_transcript_messages(session_id)
        finally:
            connection.close()

        assert transcript[-4].parts[0].text == "Now summarize the tests."
        assert transcript[-3].parts[0].text == (
            "I received your request: Now summarize the tests."
        )
        assert transcript[-2].parts[0].text == "Add one more note."
        assert transcript[-1].parts[0].text == (
            "I received your request: Add one more note."
        )
    finally:
        _stop_daemon_if_running(tmp_path)


def test_cli_attach_can_observe_daemon_session_without_mutating_transcript(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        initial_transcript = repository.list_transcript_messages(session_id)
    finally:
        connection.close()

    port = _reserve_port()
    interactive_inputs = iter(["/status", "/exit"])
    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

    try:
        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
                "--port",
                str(port),
            ]
        )
        _ = capsys.readouterr()
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

        assert exit_code == 0
        assert f"Attached to live session {session_id}" in captured.out
        assert "Leaving interactive session" in captured.out

        connection = open_database(db_path)
        try:
            repository = SQLiteSessionRepository(connection)
            transcript = repository.list_transcript_messages(session_id)
        finally:
            connection.close()

        assert [message.message_id for message in transcript] == [
            message.message_id for message in initial_transcript
        ]
    finally:
        _stop_daemon_if_running(tmp_path)


def test_cli_cancel_routes_to_daemon_and_reports_idle_conflict(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    port = _reserve_port()

    try:
        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
                "--port",
                str(port),
            ]
        )
        _ = capsys.readouterr()

        assert exit_code == 0

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
    finally:
        _stop_daemon_if_running(tmp_path)


def test_cli_attach_tui_routes_live_session_through_daemon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    dashboard_urls: list[str] = []

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

    async def fake_attach_tui_via_daemon(args, *, dashboard_url, launch_options) -> int:
        assert args.session_id == session_id
        assert launch_options.requested_mode == InteractiveLaunchMode.TUI
        dashboard_urls.append(dashboard_url)
        return 0

    monkeypatch.setattr(
        "glassbox.cli.interactive_commands.attach_tui_via_daemon",
        fake_attach_tui_via_daemon,
    )

    port = _reserve_port()
    try:
        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
                "--port",
                str(port),
            ]
        )
        _ = capsys.readouterr()
        assert exit_code == 0

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
        assert dashboard_urls == [f"http://127.0.0.1:{port}/"]
    finally:
        _stop_daemon_if_running(tmp_path)


def test_cli_attach_reports_live_runtime_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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
    assert (
        "live runtime unavailable at http://127.0.0.1:9999/; cannot attach session"
        in captured.err
    )
    assert "Inspect health: http://127.0.0.1:9999/healthz" in captured.err
    assert "Status: glassbox daemon status" in captured.err
    assert "Recover: glassbox daemon stop" in captured.err


def test_cli_attach_reports_historical_only_session_when_daemon_is_running(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    port = _reserve_port()

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

    try:
        exit_code = main(
            [
                "daemon",
                "start",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
                "--port",
                str(port),
            ]
        )
        _ = capsys.readouterr()

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

        assert exit_code == 1
        assert "is only historically inspectable in status completed" in captured.err
    finally:
        _stop_daemon_if_running(tmp_path)


def test_cli_attach_reports_stale_runtime_owner_then_falls_back_locally(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    interactive_inputs = iter(["Now summarize the tests.", "/exit"])
    owner_path = _runtime_owner_path(tmp_path)
    owner_path.parent.mkdir(parents=True, exist_ok=True)
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

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

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

    assert exit_code == 0
    assert "Workspace daemon owner metadata is stale" in captured.out
    assert f"Attached to session {session_id}" in captured.out


def test_cli_attach_uses_local_runtime_after_owner_metadata_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    _write_owner_metadata(tmp_path, pid=999999, db_path=db_path)
    interactive_inputs = iter(["Continue after cleanup.", "/exit"])

    exit_code = main(
        [
            "daemon",
            "stop",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    stop_capture = capsys.readouterr()

    assert exit_code == 0
    assert "Removed stale workspace daemon owner metadata." in stop_capture.out
    assert not _runtime_owner_path(tmp_path).exists()

    monkeypatch.setattr(
        "glassbox.cli.interactive_session._read_interactive_input",
        lambda prompt: next(interactive_inputs),
    )

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
    attach_capture = capsys.readouterr()

    assert exit_code == 0
    assert f"Attached to session {session_id}" in attach_capture.out
    assert "Attached to live session" not in attach_capture.out
    assert "Queued user message: Continue after cleanup." in attach_capture.out
