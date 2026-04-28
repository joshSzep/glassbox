"""Run the v7 release-candidate gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_REPO_ROOT))

from scripts.validate_v6_release_gate import DEFAULT_EVIDENCE_ROOT  # noqa: E402
from scripts.validate_v6_release_gate import DIST_DIR  # noqa: E402
from scripts.validate_v6_release_gate import REPO_ROOT  # noqa: E402
from scripts.validate_v6_release_gate import GateStage  # noqa: E402
from scripts.validate_v6_release_gate import _latest_glassbox_wheel  # noqa: E402
from scripts.validate_v6_release_gate import _run_installed_wheel_smoke  # noqa: E402
from scripts.validate_v6_release_gate import (  # noqa: E402
    build_gate_stages as build_v6_gate_stages,
)

V7_ADDITIONAL_STAGES = [
    GateStage(
        "v7 deterministic eval release profile",
        (
            "uv",
            "run",
            "glassbox",
            "eval",
            "run",
            "--profile",
            "release-candidate",
            "--cwd",
            ".",
        ),
    ),
    GateStage(
        "v7 workflow advisory eval profile",
        (
            "uv",
            "run",
            "glassbox",
            "eval",
            "run",
            "--profile",
            "v7-workflow-advisory",
            "--cwd",
            ".",
        ),
    ),
    GateStage(
        "v7 scale performance budgets",
        ("uv", "run", "glassbox", "performance", "budgets"),
    ),
    GateStage(
        "v7 provider diagnostics onboarding",
        ("uv", "run", "glassbox", "provider", "diagnostics", "--cwd", ".", "--json"),
    ),
    GateStage(
        "v7 dashboard evidence cue tests",
        (
            "pnpm",
            "--dir",
            "frontend",
            "exec",
            "vitest",
            "run",
            "tests/verification-cues.test.ts",
        ),
    ),
    GateStage(
        "v7 release evidence docs",
        (
            "uv",
            "run",
            "python",
            "scripts/validate_package_contents.py",
        ),
    ),
]


def build_gate_stages() -> list[GateStage]:
    """Return the deterministic blocking stages for the v7 gate."""

    return [*build_v6_gate_stages(), *V7_ADDITIONAL_STAGES]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Glassbox v7 release-candidate gate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the gate stages without executing them",
    )
    parser.add_argument(
        "--include-provider-canaries",
        action="store_true",
        help=(
            "run advisory provider canaries and retain matrix evidence when configured"
        ),
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
        _record_installed_wheel_plan(summary)
        _finish_summary(summary, "dry_run")
        _write_evidence_summary(evidence_dir, summary)
        return 0

    for stage in stages:
        exit_code = _run_stage(summary, stage)
        if exit_code != 0:
            _finish_summary(summary, "failed")
            _write_evidence_summary(evidence_dir, summary)
            return exit_code

    _record_provider_canary(
        summary, evidence_dir, include=args.include_provider_canaries
    )

    wheel_path = _latest_glassbox_wheel()
    if wheel_path is None:
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
        print("V7 release gate failed: built wheel not found", file=sys.stderr)
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
    print("V7 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {_format_command(stage.command)}")
    if include_provider_canaries:
        print(
            "- advisory provider canaries: "
            "uv run glassbox provider canary run --cwd . "
            "--output-dir <evidence>/provider-canary"
        )
    else:
        print("- advisory provider canaries: skipped by default")
    print("- installed wheel smoke: latest dist/glassbox-*.whl")


def _run_stage(summary: dict[str, Any], stage: GateStage) -> int:
    started_at = _now_iso()
    print(f"\n==> {stage.label}")
    result = subprocess.run(stage.command, cwd=REPO_ROOT, check=False)
    ended_at = _now_iso()
    _record_stage_result(
        summary,
        label=stage.label,
        command=stage.command,
        status="passed" if result.returncode == 0 else "failed",
        exit_code=result.returncode,
        started_at=started_at,
        ended_at=ended_at,
    )
    if result.returncode != 0:
        print(f"\nV7 release gate failed: {stage.label}", file=sys.stderr)
    return result.returncode


def _record_provider_canary(
    summary: dict[str, Any],
    evidence_dir: Path,
    *,
    include: bool,
) -> None:
    if not include:
        summary["advisory"].append(
            {
                "label": "advisory provider canaries",
                "status": "skipped",
                "reason": "pass --include-provider-canaries to run when configured",
            }
        )
        return

    output_dir = evidence_dir / "provider-canary"
    command = (
        "uv",
        "run",
        "glassbox",
        "provider",
        "canary",
        "run",
        "--cwd",
        ".",
        "--output-dir",
        str(output_dir),
        "--json",
    )
    started_at = _now_iso()
    print("\n==> advisory provider canaries")
    result = subprocess.run(command, cwd=REPO_ROOT, check=False)
    summary["advisory"].append(
        {
            "label": "advisory provider canaries",
            "command": list(command),
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "started_at": started_at,
            "ended_at": _now_iso(),
            "evidence_dir": str(output_dir),
            "blocking": False,
        }
    )


def _record_installed_wheel_plan(summary: dict[str, Any]) -> None:
    _record_stage_result(
        summary,
        label="installed wheel smoke",
        command=("latest", "dist/glassbox-*.whl"),
        status="planned",
        exit_code=None,
        started_at=None,
        ended_at=None,
    )


def _resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_EVIDENCE_ROOT / f"{timestamp}-v7-gate"


def _new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "gate": "v7-release",
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
            "manual_evidence_hint": "docs/manual-qa-evidence-v7.md",
            "accessibility_terminal_review": "docs/terminal-accessibility-review-v7.md",
            "accessibility_dashboard_review": (
                "docs/dashboard-accessibility-review-v7.md"
            ),
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


def _finish_summary(summary: dict[str, Any], status: str) -> None:
    summary["status"] = status
    summary["ended_at"] = _now_iso()
    if status == "failed":
        summary["next_actions"].append("inspect failed stage output above")
    elif status == "dry_run":
        summary["next_actions"].append("rerun without --dry-run to execute the gate")
    elif status == "passed":
        summary["next_actions"].append(
            "attach manual v7 evidence and release decision notes before RC signoff"
        )


def _write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nV7 release evidence written to {summary_path}")
    return summary_path


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
