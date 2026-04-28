"""Run the v6 release-hardening gate."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"

FOCUSED_CANCELLATION_TESTS = [
    "tests/unit/test_model_loop.py",
    "tests/integration/test_turn_engine.py",
    "tests/integration/test_command_tool.py",
    "tests/unit/test_subprocess_classification.py",
]

FOCUSED_TRANSPORT_DAEMON_TESTS = [
    "tests/unit/test_runtime_transport.py",
    "tests/integration/test_web_sse_events.py",
    "tests/integration/test_daemon_runtime.py",
    "tests/integration/test_cli_session_commands.py",
]

FOCUSED_TUI_DASHBOARD_TESTS = [
    "tests/unit/test_tui_framework_smoke.py",
    "tests/unit/test_cli_tui_conversation.py",
    "tests/unit/test_cli_tui_widgets.py",
    "tests/unit/test_cli_tui_app.py",
    "tests/unit/test_cli_tui_commands.py",
    "tests/unit/test_cli_tui_workflows.py",
    "tests/integration/test_cli_tui_launch_smoke.py",
    "tests/integration/test_cli_interactive_commands.py",
    "tests/integration/test_web_session_interaction.py",
    "tests/integration/test_web_spa_static.py",
    "tests/unit/test_packaging_metadata.py",
]


@dataclass(frozen=True, slots=True)
class GateStage:
    """One command stage in the v6 automated gate."""

    label: str
    command: tuple[str, ...]


def build_gate_stages() -> list[GateStage]:
    """Return the deterministic blocking stages for the v6 gate."""

    return [
        GateStage("python format", ("uv", "run", "ruff", "format", "--check", ".")),
        GateStage("python lint", ("uv", "run", "ruff", "check", ".")),
        GateStage("python typecheck", ("uv", "run", "ty", "check")),
        GateStage(
            "focused cancellation suite",
            ("uv", "run", "pytest", *FOCUSED_CANCELLATION_TESTS),
        ),
        GateStage(
            "focused transport and daemon suite",
            ("uv", "run", "pytest", *FOCUSED_TRANSPORT_DAEMON_TESTS),
        ),
        GateStage(
            "focused terminal and dashboard suite",
            ("uv", "run", "pytest", *FOCUSED_TUI_DASHBOARD_TESTS),
        ),
        GateStage("full python tests", ("uv", "run", "pytest")),
        GateStage("deterministic eval smoke", ("uv", "run", "glassbox", "eval", "run")),
        GateStage("frontend lint", ("pnpm", "--dir", "frontend", "lint")),
        GateStage("frontend typecheck", ("pnpm", "--dir", "frontend", "typecheck")),
        GateStage("frontend tests", ("pnpm", "--dir", "frontend", "test")),
        GateStage("frontend production build", ("pnpm", "--dir", "frontend", "build")),
        GateStage("package build", ("uv", "build", "--wheel", "--sdist")),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Glassbox v6 release-hardening gate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the gate stages without executing them",
    )
    parser.add_argument(
        "--include-provider-canaries",
        action="store_true",
        help="run advisory live-provider canaries when credentials are available",
    )
    args = parser.parse_args(argv)

    stages = build_gate_stages()
    if args.dry_run:
        _print_dry_run(stages, include_provider_canaries=args.include_provider_canaries)
        return 0

    for stage in stages:
        exit_code = _run(stage.label, stage.command)
        if exit_code != 0:
            return exit_code

    if args.include_provider_canaries:
        exit_code = _run(
            "advisory provider canaries",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                "--profile",
                "live-provider-canary",
            ),
        )
        if exit_code != 0:
            print(
                "\nV6 release gate failed: advisory provider canaries",
                file=sys.stderr,
            )
            return exit_code
    else:
        print("\n==> advisory provider canaries")
        print("skipped; pass --include-provider-canaries to run when configured")

    wheel_path = _latest_glassbox_wheel()
    if wheel_path is None:
        print("V6 release gate failed: built wheel not found", file=sys.stderr)
        return 1

    return _run_installed_wheel_smoke(wheel_path)


def _print_dry_run(
    stages: Sequence[GateStage],
    *,
    include_provider_canaries: bool,
) -> None:
    print("V6 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {_format_command(stage.command)}")
    if include_provider_canaries:
        print(
            "- advisory provider canaries: "
            "uv run glassbox eval run --profile live-provider-canary"
        )
    else:
        print("- advisory provider canaries: skipped by default")
    print("- installed wheel smoke: latest dist/glassbox-*.whl")


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
        print(f"\nV6 release gate failed: {label}", file=sys.stderr)
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
    with tempfile.TemporaryDirectory(prefix="glassbox-v6-gate-") as temp_dir:
        smoke_checks: list[tuple[str, tuple[str, ...], str | None]] = [
            (
                "installed command tree",
                (
                    "uv",
                    "run",
                    "--isolated",
                    "--with",
                    str(wheel_path),
                    "glassbox",
                    "command",
                    "tree",
                ),
                None,
            ),
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
    print("\nV6 release gate passed.")
    return 0


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)


if __name__ == "__main__":
    raise SystemExit(main())
