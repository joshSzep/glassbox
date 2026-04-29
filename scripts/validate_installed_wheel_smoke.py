"""Run installed-wheel smoke checks against a built Glassbox wheel."""

from __future__ import annotations

import argparse
import json
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
from scripts.validate_v6_release_gate import REPO_ROOT  # noqa: E402
from scripts.validate_v6_release_gate import _latest_glassbox_wheel  # noqa: E402
from scripts.validate_v6_release_gate import _run_installed_wheel_smoke  # noqa: E402
from scripts.validate_v6_release_gate import (  # noqa: E402
    build_installed_wheel_smoke_checks,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run installed-wheel smoke checks against a built Glassbox wheel.",
    )
    parser.add_argument(
        "--wheel",
        type=Path,
        help="wheel to smoke; defaults to newest dist/glassbox-*.whl",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print installed smoke checks without executing them",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="directory for retained smoke summary",
    )
    args = parser.parse_args(argv)

    wheel_path = _resolve_wheel_path(args.wheel)
    if wheel_path is None:
        print("Installed wheel smoke failed: built wheel not found", file=sys.stderr)
        return 1

    evidence_dir = _resolve_evidence_dir(args.evidence_dir)
    summary = _new_evidence_summary(evidence_dir, wheel_path, dry_run=args.dry_run)
    if args.dry_run:
        _print_dry_run(wheel_path)
        _record_planned_checks(summary, wheel_path)
        _finish_summary(summary, "dry_run")
        _write_evidence_summary(evidence_dir, summary)
        return 0

    exit_code = _run_installed_wheel_smoke(summary, wheel_path)
    _finish_summary(summary, "passed" if exit_code == 0 else "failed")
    _write_evidence_summary(evidence_dir, summary)
    return exit_code


def _resolve_wheel_path(requested: Path | None) -> Path | None:
    if requested is not None:
        return requested.resolve()
    return _latest_glassbox_wheel()


def _resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_EVIDENCE_ROOT / f"{timestamp}-installed-wheel-smoke"


def _new_evidence_summary(
    evidence_dir: Path,
    wheel_path: Path,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "gate": "installed-wheel-smoke",
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
        "options": {"dry_run": dry_run},
        "stages": [],
        "artifacts": {"wheel_path": str(wheel_path)},
        "next_actions": [],
    }


def _print_dry_run(wheel_path: Path) -> None:
    print("Installed wheel smoke dry run")
    for check in build_installed_wheel_smoke_checks(
        wheel_path,
        Path("<temporary-smoke-root>"),
    ):
        print(f"- {check.label}: {' '.join(check.command)}")
    print("- installed dashboard: static routes")


def _record_planned_checks(summary: dict[str, Any], wheel_path: Path) -> None:
    for check in build_installed_wheel_smoke_checks(
        wheel_path,
        Path("<temporary-smoke-root>"),
    ):
        _record_stage_result(
            summary,
            label=check.label,
            command=check.command,
            status="planned",
            exit_code=None,
            started_at=None,
            ended_at=None,
        )
    _record_stage_result(
        summary,
        label="installed dashboard: static routes",
        command=("glassbox", "dashboard", "serve"),
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
        summary["next_actions"].append("inspect failed installed smoke output above")
    elif status == "dry_run":
        summary["next_actions"].append("rerun without --dry-run to execute smoke")
    elif status == "passed":
        summary["next_actions"].append(
            "attach installed smoke summary to release evidence"
        )


def _write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nInstalled wheel smoke evidence written to {summary_path}")
    return summary_path


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
