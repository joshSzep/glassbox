"""Smoke tests for the minimal Glassbox CLI entrypoint."""

import runpy
import sys
from pathlib import Path

import pytest

from glassbox.cli import main
from glassbox.store import SQLiteSessionRepository
from glassbox.store import open_database


def test_cli_help_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "usage: glassbox" in captured.out
    assert "Run the Glassbox local-first CLI agent" in captured.out
    assert "session" in captured.out
    assert "replay" in captured.out


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
    assert "dashboard" in captured.out


def test_cli_unknown_command_exits_with_parser_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["not-a-command"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert "usage: glassbox" in captured.err
    assert "invalid choice: 'not-a-command'" in captured.err


@pytest.mark.parametrize(
    ("argv", "usage"),
    [
        (["session"], "usage: glassbox session"),
        (["eval", "profile"], "usage: glassbox eval profile"),
        (["eval", "case"], "usage: glassbox eval case"),
        (["backup"], "usage: glassbox backup"),
    ],
)
def test_cli_missing_nested_subcommand_exits_with_parser_error(
    argv: list[str],
    usage: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert usage in captured.err
    assert "the following arguments are required" in captured.err


def test_cli_invalid_port_exits_with_parser_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["dashboard", "serve", "--port", "70000"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert "usage: glassbox dashboard serve" in captured.err
    assert "invalid port: 70000" in captured.err


def test_cli_session_run_creates_a_baseline_session_and_initial_prompt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"

    exit_code = main(
        [
            "session",
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
        primary_events = [
            event.event_type
            for event in persisted_events
            if event.event_type != "ReplayArtifactRecorded"
        ]
    finally:
        connection.close()

    assert exit_code == 0
    assert "Started session" in captured.out
    assert "Queued user message: Inspect the repository" in captured.out
    assert "Assistant: I received your request: Inspect the repository" in captured.out
    assert primary_events == [
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
