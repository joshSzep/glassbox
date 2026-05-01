"""Subprocess smoke tests for terminal workflow launch boundaries."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.subprocess, pytest.mark.tui, pytest.mark.release_gate]


def test_session_chat_implicit_non_tty_subprocess_falls_back_to_plain(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    source_path = Path(__file__).resolve().parents[2] / "src"
    python_path = os.environ.get("PYTHONPATH")
    cli_invocation = (
        "import sys; "
        "from glassbox.cli import main; "
        "raise SystemExit(main(sys.argv[1:]))"
    )
    env = {
        **os.environ,
        "PYTHONPATH": (
            str(source_path)
            if not python_path
            else os.pathsep.join((str(source_path), python_path))
        ),
    }

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            cli_invocation,
            "session",
            "chat",
            "--no-dashboard",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ],
        input="/exit\n",
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
        env=env,
    )

    assert result.returncode == 0
    assert "Glassbox chat ready" in result.stdout
    assert "Model: openai:gpt-5.4" in result.stdout
    assert "Approval: confirm:" in result.stdout
    assert f"Workspace: {tmp_path}" in result.stdout
    assert f"Database: {db_path}" in result.stdout
    assert "Dashboard: disabled by --no-dashboard" in result.stdout
    assert "Provider:" in result.stdout
    assert "Attached to session" in result.stdout
    assert "Interactive mode: type the next prompt" in result.stdout
    assert "Leaving interactive session" in result.stdout
    assert "full-screen TUI launch" not in result.stderr
