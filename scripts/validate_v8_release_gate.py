"""Run the v8 auditable-autonomy release gate."""

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
from scripts.validate_v7_release_gate import (  # noqa: E402
    build_gate_stages as build_v7_gate_stages,
)


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v8 gate."""

    resolved_evidence_dir = evidence_dir or Path(".glassbox/releases/v8-gate")
    eval_output_dir = resolved_evidence_dir / "evals"
    background_output_dir = resolved_evidence_dir / "background-jobs"
    return [
        *build_v7_gate_stages(),
        GateStage(
            "v8 deterministic eval release report",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "report",
                "commit-smoke",
                "push-confirmation",
                "release-candidate",
                "--output-dir",
                str(eval_output_dir / "release-signoff"),
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v8 autonomy advisory eval profile",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                "--profile",
                "v8-autonomy-advisory",
                "--output-dir",
                str(eval_output_dir / "autonomy-advisory"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v8 eval coverage audit",
            ("uv", "run", "glassbox", "eval", "audit", "--cwd", "."),
        ),
        GateStage(
            "v8 background job smoke",
            (
                "uv",
                "run",
                "python",
                "scripts/background_autonomy_smoke.py",
                "--evidence-dir",
                str(background_output_dir),
                "--json",
            ),
        ),
        GateStage(
            "v8 task inspection smoke",
            ("uv", "run", "glassbox", "task", "list", "--json", "--cwd", "."),
        ),
        GateStage(
            "v8 memory smoke",
            ("uv", "run", "glassbox", "memory", "list", "--json", "--cwd", "."),
        ),
        GateStage(
            "v8 repository index smoke",
            (
                "uv",
                "run",
                "glassbox",
                "repo",
                "index",
                "status",
                "--json",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v8 background job status smoke",
            ("uv", "run", "glassbox", "job", "list", "--json", "--cwd", "."),
        ),
        GateStage(
            "v8 branch-search smoke",
            (
                "uv",
                "run",
                "glassbox",
                "branch-search",
                "list",
                "--json",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v8 observability autonomy summary",
            (
                "uv",
                "run",
                "glassbox",
                "observability",
                "status",
                "--json",
                "--cwd",
                ".",
            ),
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Glassbox v8 auditable-autonomy release gate.",
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

    evidence_dir = _resolve_evidence_dir(args.evidence_dir)
    stages = build_gate_stages(evidence_dir)
    summary = _new_evidence_summary(
        evidence_dir,
        include_provider_canaries=args.include_provider_canaries,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        _print_dry_run(stages, include_provider_canaries=args.include_provider_canaries)
        _record_planned_stages(summary, stages)
        _record_installed_wheel_plan(summary)
        _record_provider_canary(
            summary,
            evidence_dir,
            include=args.include_provider_canaries,
            dry_run=True,
        )
        _finish_summary(summary, "dry_run")
        _write_evidence_summary(evidence_dir, summary)
        _print_summary(summary)
        return 0

    for stage in stages:
        exit_code = _run_stage(summary, stage)
        if exit_code != 0:
            _finish_summary(summary, "failed")
            _write_evidence_summary(evidence_dir, summary)
            _print_summary(summary)
            return exit_code

    _record_provider_canary(
        summary,
        evidence_dir,
        include=args.include_provider_canaries,
        dry_run=False,
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
        _print_summary(summary)
        print("V8 release gate failed: built wheel not found", file=sys.stderr)
        return 1

    summary["artifacts"]["wheel_path"] = str(wheel_path.relative_to(REPO_ROOT))
    exit_code = _run_installed_wheel_smoke(summary, wheel_path)
    _finish_summary(summary, "passed" if exit_code == 0 else "failed")
    _write_evidence_summary(evidence_dir, summary)
    _print_summary(summary)
    return exit_code


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
        print(f"\nV8 release gate failed: {stage.label}", file=sys.stderr)
    return result.returncode


def _record_provider_canary(
    summary: dict[str, Any],
    evidence_dir: Path,
    *,
    include: bool,
    dry_run: bool,
) -> None:
    if not include:
        summary["advisory"].append(
            {
                "label": "advisory provider canaries",
                "status": "skipped",
                "reason": "pass --include-provider-canaries to run when configured",
                "blocking": False,
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
    if dry_run:
        summary["advisory"].append(
            {
                "label": "advisory provider canaries",
                "command": list(command),
                "status": "planned",
                "reason": "dry run requested",
                "blocking": False,
                "evidence_dir": str(output_dir),
            }
        )
        return

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


def _print_dry_run(
    stages: Sequence[GateStage],
    *,
    include_provider_canaries: bool,
) -> None:
    print("V8 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {_format_command(stage.command)}")
    if include_provider_canaries:
        print(
            "- advisory provider canaries: "
            "uv run glassbox provider canary run --cwd . "
            "--output-dir <evidence>/provider-canary --json"
        )
    else:
        print("- advisory provider canaries: skipped by default")
    print("- installed wheel smoke: latest dist/glassbox-*.whl")


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


def _resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_EVIDENCE_ROOT / f"{timestamp}-v8-gate"


def _new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "gate": "v8-release",
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
            "eval_evidence_root": str(evidence_dir / "evals"),
            "background_job_evidence": str(evidence_dir / "background-jobs"),
            "provider_canary_evidence": str(evidence_dir / "provider-canary"),
            "packaging_docs": "docs/release-packaging.md",
            "recovery_review": "docs/recovery-maintenance-review-v8.md",
            "dashboard_accessibility_review": (
                "docs/dashboard-accessibility-review-v8.md"
            ),
            "v8_contract": "docs/v8-auditable-autonomy-contract.md",
        },
        "autonomy_boundedness": {
            "blocking_evidence": [
                "v8 deterministic eval release report",
                "v8 eval coverage audit",
                "v8 background job smoke",
                "v8 task inspection smoke",
                "v8 memory smoke",
                "v8 repository index smoke",
                "v8 observability autonomy summary",
                "installed wheel smoke",
            ],
            "advisory_evidence": [
                "v8 autonomy advisory eval profile",
                "advisory provider canaries",
            ],
            "provider_credentials_required": False,
        },
        "next_actions": [],
    }


def _finish_summary(summary: dict[str, Any], status: str) -> None:
    summary["status"] = status
    summary["ended_at"] = _now_iso()
    if status == "failed":
        summary["next_actions"].append("inspect failed stage output above")
    elif status == "dry_run":
        summary["next_actions"].append("rerun without --dry-run to execute the gate")
    elif status == "passed":
        summary["next_actions"].append(
            "attach manual v8 evidence and residual-risk decision before RC signoff"
        )


def _write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nV8 release evidence written to {summary_path}")
    return summary_path


def _print_summary(summary: dict[str, Any]) -> None:
    stage_counts = _count_statuses(summary["stages"])
    advisory_counts = _count_statuses(summary["advisory"])
    print("\nV8 release gate summary")
    print(f"Status: {summary['status']}")
    print(f"Evidence: {summary['evidence_dir']}")
    print(
        "Stages: "
        + ", ".join(f"{status}={count}" for status, count in stage_counts.items())
    )
    if advisory_counts:
        print(
            "Advisory: "
            + ", ".join(
                f"{status}={count}" for status, count in advisory_counts.items()
            )
        )
    print(
        "Autonomy boundedness: "
        + ", ".join(summary["autonomy_boundedness"]["blocking_evidence"])
    )
    for action in summary["next_actions"]:
        print(f"Next: {action}")


def _count_statuses(items: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
