"""Run the v5 terminal UX release gate."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"

FOCUSED_TUI_TESTS = [
    "tests/unit/test_tui_framework_smoke.py",
    "tests/unit/test_cli_tui_conversation.py",
    "tests/unit/test_cli_tui_widgets.py",
    "tests/unit/test_cli_tui_app.py",
    "tests/unit/test_cli_tui_commands.py",
    "tests/unit/test_cli_tui_workflows.py",
    "tests/unit/test_packaging_metadata.py",
    "tests/integration/test_cli_tui_launch_smoke.py",
    "tests/integration/test_cli_interactive_commands.py",
    "tests/integration/test_daemon_runtime.py",
]


def main() -> int:
    checks: list[tuple[str, Sequence[str]]] = [
        ("python format", ("uv", "run", "ruff", "format", "--check", ".")),
        ("python lint", ("uv", "run", "ruff", "check", ".")),
        ("python typecheck", ("uv", "run", "ty", "check")),
        (
            "focused terminal workflow suite",
            ("uv", "run", "pytest", *FOCUSED_TUI_TESTS),
        ),
        ("full python tests", ("uv", "run", "pytest")),
        ("deterministic eval smoke", ("uv", "run", "glassbox", "eval", "run")),
        ("package build", ("uv", "build", "--wheel", "--sdist")),
    ]

    for label, command in checks:
        exit_code = _run(label, command)
        if exit_code != 0:
            return exit_code

    wheel_path = _latest_glassbox_wheel()
    if wheel_path is None:
        print("V5 terminal release gate failed: built wheel not found", file=sys.stderr)
        return 1

    return _run_installed_wheel_smoke(wheel_path)


def _run(label: str, command: Sequence[str], *, input_text: str | None = None) -> int:
    print(f"\n==> {label}")
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=input_text,
        text=input_text is not None,
        check=False,
    )
    if result.returncode != 0:
        print(f"\nV5 terminal release gate failed: {label}", file=sys.stderr)
    return result.returncode


def _latest_glassbox_wheel() -> Path | None:
    wheels = sorted(
        DIST_DIR.glob("glassbox-*.whl"),
        key=lambda path: path.stat().st_mtime,
    )
    if not wheels:
        return None
    return wheels[-1]


def _run_installed_wheel_smoke(wheel_path: Path) -> int:
    print(f"\n==> installed wheel smoke ({wheel_path.name})")
    with tempfile.TemporaryDirectory(prefix="glassbox-v5-gate-") as temp_dir:
        smoke_checks: list[tuple[str, Sequence[str], str | None]] = [
            (
                "installed chat help",
                (
                    "uv",
                    "run",
                    "--isolated",
                    "--with",
                    str(wheel_path),
                    "glassbox",
                    "session",
                    "chat",
                    "--help",
                ),
                None,
            ),
            (
                "installed attach help",
                (
                    "uv",
                    "run",
                    "--isolated",
                    "--with",
                    str(wheel_path),
                    "glassbox",
                    "session",
                    "attach",
                    "--help",
                ),
                None,
            ),
            (
                "installed plain fallback",
                (
                    "uv",
                    "run",
                    "--isolated",
                    "--with",
                    str(wheel_path),
                    "glassbox",
                    "session",
                    "chat",
                    "--plain",
                    "--no-dashboard",
                    "--cwd",
                    temp_dir,
                ),
                "/exit\n",
            ),
        ]

        for label, command, input_text in smoke_checks:
            exit_code = _run(label, command, input_text=input_text)
            if exit_code != 0:
                return exit_code
    print("\nV5 terminal release gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
