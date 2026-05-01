"""Record pytest duration output for local suite-speed review."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / ".glassbox" / "test-speed"


def build_pytest_command(
    pytest_args: Sequence[str],
    *,
    durations: int,
    durations_min: float,
) -> tuple[str, ...]:
    """Return the pytest command used for suite-speed evidence."""

    return (
        sys.executable,
        "-m",
        "pytest",
        *pytest_args,
        f"--durations={durations}",
        f"--durations-min={durations_min:g}",
        "-q",
    )


def default_output_path(now: datetime | None = None) -> Path:
    """Return the default timestamped duration-record path."""

    timestamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUTPUT_DIR / f"pytest-durations-{timestamp}.txt"


def write_duration_record(
    path: Path,
    *,
    command: Sequence[str],
    started_at: str,
    ended_at: str,
    exit_code: int,
    stdout: str,
    stderr: str,
) -> Path:
    """Write a human-readable pytest duration record."""

    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            "# Glassbox Pytest Duration Record",
            "",
            f"started_at: {started_at}",
            f"ended_at: {ended_at}",
            f"exit_code: {exit_code}",
            f"command: {shlex.join(command)}",
            "",
            "## stdout",
            "",
            stdout.rstrip(),
            "",
            "## stderr",
            "",
            stderr.rstrip(),
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run pytest with duration reporting and save the output.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "duration record path; defaults to "
            ".glassbox/test-speed/pytest-durations-<timestamp>.txt"
        ),
    )
    parser.add_argument(
        "--durations",
        type=int,
        default=100,
        help="number of slow tests to include in pytest duration output",
    )
    parser.add_argument(
        "--durations-min",
        type=float,
        default=0.05,
        help="minimum test duration, in seconds, included in pytest output",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="optional pytest arguments after --, for example -- tests/unit -m tui",
    )
    args = parser.parse_args(argv)

    pytest_args = tuple(args.pytest_args)
    if pytest_args[:1] == ("--",):
        pytest_args = pytest_args[1:]

    command = build_pytest_command(
        pytest_args,
        durations=args.durations,
        durations_min=args.durations_min,
    )
    started_at = _now_iso()
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    ended_at = _now_iso()

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    output_path = args.output or default_output_path()
    write_duration_record(
        output_path,
        command=command,
        started_at=started_at,
        ended_at=ended_at,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
    print(f"\nPytest duration record written to {output_path}")
    return result.returncode


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
