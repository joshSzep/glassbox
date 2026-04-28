"""Run the v6 release-hardening gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
DEFAULT_EVIDENCE_ROOT = REPO_ROOT / ".glassbox" / "releases"

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
        GateStage(
            "frontend API generation",
            ("pnpm", "--dir", "frontend", "api:generate"),
        ),
        GateStage(
            "frontend generated API freshness",
            (
                "git",
                "--no-pager",
                "diff",
                "--exit-code",
                "--",
                "frontend/generated/openapi.json",
                "frontend/generated/api-types.ts",
            ),
        ),
        GateStage("frontend production build", ("pnpm", "--dir", "frontend", "build")),
        GateStage(
            "frontend static asset validation",
            ("uv", "run", "python", "scripts/validate_frontend_release_assets.py"),
        ),
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
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help=(
            "directory for the retained gate summary; defaults under .glassbox/releases"
        ),
    )
    args = parser.parse_args(argv)

    stages = build_gate_stages()
    evidence_dir = _resolve_evidence_dir(args.evidence_dir)
    summary = _new_evidence_summary(
        evidence_dir,
        include_provider_canaries=args.include_provider_canaries,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        _print_dry_run(stages, include_provider_canaries=args.include_provider_canaries)
        _record_planned_stages(summary, stages)
        _finish_summary(summary, "dry_run")
        _write_evidence_summary(evidence_dir, summary)
        return 0

    for stage in stages:
        exit_code = _run_stage(summary, stage)
        if exit_code != 0:
            _finish_summary(summary, "failed")
            _write_evidence_summary(evidence_dir, summary)
            return exit_code

    if args.include_provider_canaries:
        exit_code = _run_stage(
            summary,
            GateStage(
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
            ),
        )
        if exit_code != 0:
            print(
                "\nV6 release gate failed: advisory provider canaries",
                file=sys.stderr,
            )
            _finish_summary(summary, "failed")
            _write_evidence_summary(evidence_dir, summary)
            return exit_code
    else:
        print("\n==> advisory provider canaries")
        print("skipped; pass --include-provider-canaries to run when configured")
        _record_advisory_skip(
            summary,
            label="advisory provider canaries",
            reason="pass --include-provider-canaries to run when configured",
        )

    wheel_path = _latest_glassbox_wheel()
    if wheel_path is None:
        print("V6 release gate failed: built wheel not found", file=sys.stderr)
        _record_stage_result(
            summary,
            label="resolve built wheel",
            command=("find", "dist", "-name", "glassbox-*.whl"),
            status="failed",
            exit_code=1,
            started_at=_now_iso(),
            ended_at=_now_iso(),
        )
        _finish_summary(summary, "failed")
        _write_evidence_summary(evidence_dir, summary)
        return 1

    summary["artifacts"]["wheel_path"] = str(wheel_path.relative_to(REPO_ROOT))
    exit_code = _run_installed_wheel_smoke(summary, wheel_path)
    _finish_summary(summary, "passed" if exit_code == 0 else "failed")
    _write_evidence_summary(evidence_dir, summary)
    return exit_code


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


def _run_stage(summary: dict[str, Any], stage: GateStage) -> int:
    started_at = _now_iso()
    exit_code = _run(stage.label, stage.command)
    ended_at = _now_iso()
    _record_stage_result(
        summary,
        label=stage.label,
        command=stage.command,
        status="passed" if exit_code == 0 else "failed",
        exit_code=exit_code,
        started_at=started_at,
        ended_at=ended_at,
    )
    return exit_code


def _latest_glassbox_wheel() -> Path | None:
    wheels = sorted(
        DIST_DIR.glob("glassbox-*.whl"),
        key=lambda path: path.stat().st_mtime,
    )
    if not wheels:
        return None
    return wheels[-1]


def _run_installed_wheel_smoke(summary: dict[str, Any], wheel_path: Path) -> int:
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
            started_at = _now_iso()
            exit_code = _run(label, command, input_text=input_text)
            ended_at = _now_iso()
            _record_stage_result(
                summary,
                label=label,
                command=command,
                status="passed" if exit_code == 0 else "failed",
                exit_code=exit_code,
                started_at=started_at,
                ended_at=ended_at,
            )
            if exit_code != 0:
                return exit_code
    print("\nV6 release gate passed.")
    return 0


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)


def _resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_EVIDENCE_ROOT / f"{timestamp}-v6-gate"


def _new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "gate": "v6-release",
        "status": "dry_run" if dry_run else "running",
        "started_at": _now_iso(),
        "ended_at": None,
        "evidence_dir": str(evidence_dir),
        "command": list(sys.argv),
        "environment": {
            "cwd": str(REPO_ROOT),
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        },
        "options": {
            "include_provider_canaries": include_provider_canaries,
            "dry_run": dry_run,
        },
        "stages": [],
        "advisory": [],
        "artifacts": {
            "dist_dir": str(DIST_DIR.relative_to(REPO_ROOT)),
            "eval_summary_hint": ".glassbox/evals/",
            "manual_evidence_hint": "docs/v6-release-evidence.md",
        },
        "next_actions": [],
    }


def _record_planned_stages(
    summary: dict[str, Any],
    stages: Sequence[GateStage],
) -> None:
    for stage in stages:
        _record_stage_result(
            summary,
            label=stage.label,
            command=stage.command,
            status="planned",
            exit_code=None,
            started_at=None,
            ended_at=None,
        )


def _record_stage_result(
    summary: dict[str, Any],
    *,
    label: str,
    command: Sequence[str],
    status: str,
    exit_code: int | None,
    started_at: str | None,
    ended_at: str | None,
) -> None:
    summary["stages"].append(
        {
            "label": label,
            "command": list(command),
            "status": status,
            "exit_code": exit_code,
            "started_at": started_at,
            "ended_at": ended_at,
        }
    )


def _record_advisory_skip(
    summary: dict[str, Any],
    *,
    label: str,
    reason: str,
) -> None:
    summary["advisory"].append(
        {
            "label": label,
            "status": "skipped",
            "reason": reason,
        }
    )


def _finish_summary(summary: dict[str, Any], status: str) -> None:
    summary["status"] = status
    summary["ended_at"] = _now_iso()
    if status == "failed":
        summary["next_actions"].append("inspect failed stage output above")
    elif status == "dry_run":
        summary["next_actions"].append("rerun without --dry-run to execute the gate")
    elif status == "passed":
        summary["next_actions"].append(
            "attach manual release evidence before RC signoff"
        )


def _write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nV6 release evidence written to {summary_path}")
    return summary_path


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
