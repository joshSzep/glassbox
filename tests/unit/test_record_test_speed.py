"""Tests for the pytest duration recording helper."""

import subprocess
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path

from scripts import record_test_speed


def test_build_pytest_command_appends_duration_flags() -> None:
    command = record_test_speed.build_pytest_command(
        ("tests/unit", "-m", "not tui"),
        durations=25,
        durations_min=0.1,
    )

    assert command == (
        sys.executable,
        "-m",
        "pytest",
        "tests/unit",
        "-m",
        "not tui",
        "--durations=25",
        "--durations-min=0.1",
        "-q",
    )


def test_default_output_path_uses_timestamped_test_speed_directory() -> None:
    path = record_test_speed.default_output_path(
        datetime(2026, 5, 1, 12, 30, 45, tzinfo=UTC),
    )

    assert path == (
        record_test_speed.DEFAULT_OUTPUT_DIR / "pytest-durations-20260501T123045Z.txt"
    )


def test_write_duration_record_includes_command_output_and_exit_code(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "duration.txt"

    record_test_speed.write_duration_record(
        output_path,
        command=("python", "-m", "pytest", "--durations=5"),
        started_at="2026-05-01T12:00:00Z",
        ended_at="2026-05-01T12:00:01Z",
        exit_code=1,
        stdout="slowest durations\n1.00s test_example.py::test_case\n",
        stderr="warning\n",
    )

    content = output_path.read_text(encoding="utf-8")
    assert "exit_code: 1" in content
    assert "command: python -m pytest --durations=5" in content
    assert "1.00s test_example.py::test_case" in content
    assert "warning" in content


def test_main_runs_pytest_and_writes_record(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    output_path = tmp_path / "duration.txt"
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert cwd == record_test_speed.REPO_ROOT
        assert capture_output is True
        assert text is True
        assert check is False
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="1 passed\nslowest durations\n",
            stderr="",
        )

    monkeypatch.setattr(record_test_speed.subprocess, "run", fake_run)

    exit_code = record_test_speed.main(
        [
            "--output",
            str(output_path),
            "--durations",
            "10",
            "--durations-min",
            "0.2",
            "--",
            "tests/unit",
        ]
    )

    assert exit_code == 0
    assert calls == [
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/unit",
            "--durations=10",
            "--durations-min=0.2",
            "-q",
        )
    ]
    assert "1 passed" in capsys.readouterr().out
    assert "slowest durations" in output_path.read_text(encoding="utf-8")
