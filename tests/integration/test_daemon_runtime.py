"""Integration tests for the workspace-scoped daemon runtime owner."""

import json
import socket
from pathlib import Path
from uuid import uuid4

import pytest

from glassbox.cli import main


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


def test_cli_help_lists_daemon_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "daemon" in captured.out


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
