"""Run the v16 operator-flow release gate scaffold."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_REPO_ROOT))

from scripts import v11_release_gate_helpers as gate_helpers  # noqa: E402
from scripts import v16_release_gate_helpers as v16_helpers  # noqa: E402
from scripts.validate_v6_release_gate import REPO_ROOT  # noqa: E402
from scripts.validate_v6_release_gate import GateStage  # noqa: E402
from scripts.validate_v6_release_gate import _latest_glassbox_wheel  # noqa: E402
from scripts.validate_v6_release_gate import _run_installed_wheel_smoke  # noqa: E402

V16_OPERATOR_FLOW_CASES = v16_helpers.V16_OPERATOR_FLOW_CASES


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v16 gate."""

    return v16_helpers.build_gate_stages(evidence_dir)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Glassbox v16 operator-flow release gate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the gate stages without executing them",
    )
    parser.add_argument(
        "--include-provider-canaries",
        action="store_true",
        help="run advisory provider canaries and retain freshness evidence",
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
        _record_v16_provider_evidence(
            summary,
            evidence_dir,
            include=args.include_provider_canaries,
            dry_run=True,
        )
        _record_v16_advisory_evidence(summary, evidence_dir)
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

    _record_v16_provider_evidence(
        summary,
        evidence_dir,
        include=args.include_provider_canaries,
        dry_run=False,
    )
    _record_v16_advisory_evidence(summary, evidence_dir)

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
        print("V16 release gate failed: built wheel not found", file=sys.stderr)
        return 1

    summary["artifacts"]["wheel_path"] = str(wheel_path.relative_to(REPO_ROOT))
    exit_code = _run_installed_wheel_smoke(summary, wheel_path)
    _finish_summary(summary, "passed" if exit_code == 0 else "failed")
    _write_evidence_summary(evidence_dir, summary)
    _print_summary(summary)
    return exit_code


def _record_v16_provider_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
    *,
    include: bool,
    dry_run: bool,
) -> None:
    v16_helpers.record_provider_evidence(
        summary,
        evidence_dir,
        include=include,
        dry_run=dry_run,
    )


def _record_v16_advisory_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
) -> None:
    v16_helpers.record_advisory_evidence(summary, evidence_dir)


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
        print(f"\nV16 release gate failed: {stage.label}", file=sys.stderr)
    return result.returncode


def _print_dry_run(
    stages: Sequence[GateStage],
    *,
    include_provider_canaries: bool,
) -> None:
    v16_helpers.print_dry_run(
        stages,
        include_provider_canaries=include_provider_canaries,
    )


def _record_planned_stages(
    summary: dict[str, Any],
    stages: Sequence[GateStage],
) -> None:
    v16_helpers.record_planned_stages(summary, stages)


def _record_installed_wheel_plan(summary: dict[str, Any]) -> None:
    v16_helpers.record_installed_wheel_plan(summary)


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
    gate_helpers.record_stage_result(
        summary,
        label=label,
        command=command,
        status=status,
        exit_code=exit_code,
        started_at=started_at,
        ended_at=ended_at,
    )


def _resolve_evidence_dir(requested: Path | None) -> Path:
    return v16_helpers.resolve_evidence_dir(requested)


def _new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
) -> dict[str, Any]:
    return v16_helpers.new_evidence_summary(
        evidence_dir,
        include_provider_canaries=include_provider_canaries,
        dry_run=dry_run,
    )


def _finish_summary(summary: dict[str, Any], status: str) -> None:
    v16_helpers.finish_summary(summary, status)


def _write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    return v16_helpers.write_evidence_summary(evidence_dir, summary)


def _print_summary(summary: dict[str, Any]) -> None:
    v16_helpers.print_summary(summary)


def _now_iso() -> str:
    return v16_helpers.now_iso()


def _now_stamp() -> str:
    return v16_helpers.now_stamp()


if __name__ == "__main__":
    raise SystemExit(main())
