"""Smoke tests for the minimal Glassbox CLI entrypoint."""

import runpy
import sys
from pathlib import Path

import pytest

from glassbox.cli import main
from glassbox.cli.parser import CommandTreeColorTheme
from glassbox.cli.parser import build_parser
from glassbox.cli.parser import format_command_tree
from glassbox.store import SQLiteSessionRepository
from glassbox.store import open_database


def test_cli_help_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "usage: glassbox" in captured.out
    assert "Run the Glassbox local-first CLI agent" in captured.out
    assert "command" in captured.out
    assert "session" in captured.out
    assert "replay" in captured.out
    assert "command tree:" not in captured.out
    assert "|-- session" not in captured.out


def test_cli_command_tree_prints_command_tree(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["command", "tree"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.startswith("glassbox  Run the Glassbox local-first CLI agent")
    assert "|-- command" in captured.out
    assert "inspect the Glassbox command surface" in captured.out
    assert "|   `-- tree  print the command tree" in captured.out
    assert "|-- observability" in captured.out
    assert "summarize runtime, projection, and verification health" in captured.out
    assert "|-- performance" in captured.out
    assert "inspect larger-session performance expectations" in captured.out
    assert "|-- session" in captured.out
    assert "work with sessions" in captured.out
    assert "|   |-- run" in captured.out
    assert "start a new session" in captured.out
    assert "|   `-- bundle" in captured.out
    assert "work with portable replay bundles" in captured.out
    assert "|       |-- export" in captured.out
    assert "|   |-- profile" in captured.out
    assert "|   |   |-- list" in captured.out
    assert "|   `-- case" in captured.out
    assert "|       |-- promote" in captured.out
    assert "`-- daemon" in captured.out
    assert "    `-- status" in captured.out
    assert "run-owner" not in captured.out


def test_cli_command_tree_can_color_command_names() -> None:
    command_tree = format_command_tree(
        build_parser(),
        color_theme=CommandTreeColorTheme(
            prog="\x1b[1;35m",
            action="\x1b[1;32m",
            reset="\x1b[0m",
        ),
    )

    assert "\x1b[1;35mglassbox\x1b[0m" in command_tree
    assert "\x1b[1;32mcommand" in command_tree
    assert "\x1b[1;32msession" in command_tree
    assert "Run the Glassbox local-first CLI agent" in command_tree


def test_cli_command_help_lists_tree_subcommand(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["command", "--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "usage: glassbox command" in captured.out
    assert "tree" in captured.out


def test_cli_performance_budgets_prints_guidance(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["performance", "budgets"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.startswith("Glassbox performance budgets")
    assert "event-stream append: 2000 ms" in captured.out
    assert "projection rebuild: 2000 ms" in captured.out
    assert "operator console aggregate: 3000 ms" in captured.out
    assert "session snapshot build: 3000 ms" in captured.out
    assert "session snapshot payload: 1500000 bytes" in captured.out
    assert "dashboard render-critical payload: 300000 bytes" in captured.out
    assert "Guidance:" in captured.out


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
