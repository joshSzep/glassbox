"""Reusable release-gate entrypoint runner."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path

from scripts import v11_release_gate_helpers as gate_helpers
from scripts.release_gate_models import EvidenceSummary
from scripts.release_gate_models import MilestoneReleaseGate
from scripts.validate_v6_release_gate import REPO_ROOT
from scripts.validate_v6_release_gate import GateStage
from scripts.validate_v6_release_gate import _latest_glassbox_wheel
from scripts.validate_v6_release_gate import _run_installed_wheel_smoke


def run_release_gate(
    config: MilestoneReleaseGate,
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=config.description)
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

    evidence_dir = config.resolve_evidence_dir(args.evidence_dir)
    stages = config.build_gate_stages(evidence_dir)
    summary = config.new_evidence_summary(
        evidence_dir,
        include_provider_canaries=args.include_provider_canaries,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        return _run_dry_gate(config, summary, stages, evidence_dir, args)

    for stage in stages:
        exit_code = _run_stage(config, summary, stage)
        if exit_code != 0:
            config.finish_summary(summary, "failed")
            config.write_evidence_summary(evidence_dir, summary)
            config.print_summary(summary)
            return exit_code

    config.record_provider_evidence(
        summary,
        evidence_dir,
        include=args.include_provider_canaries,
        dry_run=False,
    )
    config.record_advisory_evidence(summary, evidence_dir)

    wheel_path = _latest_glassbox_wheel()
    if wheel_path is None:
        gate_helpers.record_stage_result(
            summary,
            label="resolve built wheel",
            command=("find", "dist", "-name", "glassbox-*.whl"),
            status="failed",
            exit_code=1,
            started_at=_now_iso(),
            ended_at=_now_iso(),
        )
        config.finish_summary(summary, "failed")
        config.write_evidence_summary(evidence_dir, summary)
        config.print_summary(summary)
        print(
            f"{config.label} release gate failed: built wheel not found",
            file=sys.stderr,
        )
        return 1

    summary["artifacts"]["wheel_path"] = str(wheel_path.relative_to(REPO_ROOT))
    exit_code = _run_installed_wheel_smoke(summary, wheel_path)
    config.finish_summary(summary, "passed" if exit_code == 0 else "failed")
    config.write_evidence_summary(evidence_dir, summary)
    config.print_summary(summary)
    return exit_code


def _run_dry_gate(
    config: MilestoneReleaseGate,
    summary: EvidenceSummary,
    stages: Sequence[GateStage],
    evidence_dir: Path,
    args: argparse.Namespace,
) -> int:
    config.print_dry_run(
        stages,
        include_provider_canaries=args.include_provider_canaries,
    )
    config.record_planned_stages(summary, stages)
    config.record_installed_wheel_plan(summary)
    config.record_provider_evidence(
        summary,
        evidence_dir,
        include=args.include_provider_canaries,
        dry_run=True,
    )
    config.record_advisory_evidence(summary, evidence_dir)
    config.finish_summary(summary, "dry_run")
    config.write_evidence_summary(evidence_dir, summary)
    config.print_summary(summary)
    return 0


def _run_stage(
    config: MilestoneReleaseGate,
    summary: EvidenceSummary,
    stage: GateStage,
) -> int:
    started_at = _now_iso()
    print(f"\n==> {stage.label}")
    result = subprocess.run(stage.command, cwd=REPO_ROOT, check=False)
    ended_at = _now_iso()
    gate_helpers.record_stage_result(
        summary,
        label=stage.label,
        command=stage.command,
        status="passed" if result.returncode == 0 else "failed",
        exit_code=result.returncode,
        started_at=started_at,
        ended_at=ended_at,
    )
    if result.returncode != 0:
        print(f"\n{config.label} release gate failed: {stage.label}", file=sys.stderr)
    return result.returncode


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
