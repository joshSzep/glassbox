"""Smoke tests for the minimal Glassbox CLI entrypoint."""

import runpy
import sys
from pathlib import Path

import pytest

from glassbox.cli import main
from glassbox.store import SQLiteSessionRepository, open_database


def test_cli_help_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "usage: glassbox" in captured.out
    assert "Run the Glassbox local-first CLI agent" in captured.out
    assert "run" in captured.out


def test_python_module_entrypoint_prints_help(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["glassbox", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("glassbox", run_name="__main__")

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "usage: glassbox" in captured.out
    assert "serve" in captured.out


def test_cli_run_creates_a_baseline_session_and_initial_prompt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    exit_code = main(
        [
            "run",
            "Inspect the repository",
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
        persisted_events = repository.read_session_events(sessions[0].session_id)
    finally:
        connection.close()

    assert exit_code == 0
    assert "Started session" in captured.out
    assert "Queued user message: Inspect the repository" in captured.out
    assert "Assistant: I received your request: Inspect the repository" in captured.out
    assert [event.event_type for event in persisted_events] == [
        "SessionStarted",
        "UserMessageReceived",
        "TurnStarted",
        "TurnStatusChanged",
        "TurnStatusChanged",
        "ModelCallStarted",
        "AssistantMessageStarted",
        "AssistantMessageDelta",
        "AssistantMessageDelta",
        "ModelCallCompleted",
        "TurnStatusChanged",
        "AssistantMessageCompleted",
        "TurnStatusChanged",
        "TurnCompleted",
    ]
