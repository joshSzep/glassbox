"""V16 release-gate summary and dry-run helpers."""

import json
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts import v11_release_gate_helpers as gate_helpers
from scripts import validate_v15_release_gate as v15_gate
from scripts.validate_v6_release_gate import DEFAULT_EVIDENCE_ROOT
from scripts.validate_v6_release_gate import GateStage


def print_dry_run(
    stages: Sequence[GateStage],
    *,
    include_provider_canaries: bool,
) -> None:
    print("V16 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {gate_helpers.format_command(stage.command)}")
    if include_provider_canaries:
        print(
            "- v16 advisory provider evidence: "
            "uv run glassbox provider canary run --cwd . "
            "--output-dir <evidence>/provider-canary --json"
        )
    else:
        print("- v16 advisory provider evidence: skipped by default")
    print("- v16 advisory dashboard browser evidence: recorded from retained summary")
    print("- v16 advisory accessibility evidence: recorded from retained summary")
    print("- v16 dogfooding evidence: recorded GBX-1682 advisory summary")
    print("- v16 manual release evidence: recorded v16 release-candidate guide")
    print("- installed wheel smoke: latest dist/glassbox-*.whl")


def record_planned_stages(
    summary: dict[str, Any],
    stages: Sequence[GateStage],
) -> None:
    v15_gate._record_planned_stages(summary, stages)  # noqa: SLF001


def record_installed_wheel_plan(summary: dict[str, Any]) -> None:
    v15_gate._record_installed_wheel_plan(summary)  # noqa: SLF001


def resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    return DEFAULT_EVIDENCE_ROOT / f"{now_stamp()}-v16-gate"


def new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
) -> dict[str, Any]:
    summary = v15_gate._new_evidence_summary(  # noqa: SLF001
        evidence_dir,
        include_provider_canaries=include_provider_canaries,
        dry_run=dry_run,
    )
    summary["gate"] = "v16-release"
    summary["artifacts"].update(
        {
            "v16_task_graph": "docs/tasks-v16.md",
            "v16_operator_flow_contract": (
                "docs/v16-operator-flow-compression-contract.md"
            ),
            "v16_operator_flow_audit": "docs/v16-operator-flow-audit.md",
            "v16_flow_cockpit_evidence": "docs/v16-flow-cockpit-evidence.md",
            "v16_release_gate": "docs/v16-release-gate.md",
            "v16_eval_cases": "evals/README.md",
            "v16_replay_evals": "docs/replay-evals.md",
        }
    )
    summary["release_authority"]["blocking_evidence"].extend(
        [
            "inherited v15 deterministic release stages",
            "v16 deterministic eval release report",
            "v16 operator flow release profile",
            "v16 operator flow eval smoke",
            "v16 operator queue smoke",
            "v16 evidence graph smoke",
            "v16 verification plan smoke",
            "v16 operator flow runtime coverage",
            "v16 operator flow CLI API coverage",
            "v16 operator flow frontend smoke",
            "v16 package contents validation",
            "v16 release docs",
            "v16 eval coverage audit",
        ]
    )
    summary["release_authority"].setdefault("advisory_evidence", []).extend(
        [
            "v16 advisory provider evidence",
            "v16 advisory dashboard browser evidence",
            "v16 advisory accessibility evidence",
            "v16 dogfooding evidence",
            "v16 manual release evidence",
        ]
    )
    return summary


def finish_summary(summary: dict[str, Any], status: str) -> None:
    gate_helpers.finish_summary(summary, status)
    if status == "passed":
        summary["next_actions"][-1] = (
            "attach v16 dogfooding, advisory cockpit, residual-risk, and release "
            "candidate evidence before RC signoff"
        )
    else:
        summary["next_actions"] = [
            action.replace("v11", "v16").replace("v14", "v16").replace("v15", "v16")
            for action in summary["next_actions"]
        ]


def write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nV16 release evidence written to {summary_path}")
    return summary_path


def print_summary(summary: dict[str, Any]) -> None:
    stage_counts = gate_helpers.count_statuses(summary["stages"])
    advisory_counts = gate_helpers.count_statuses(summary["advisory"])
    print("\nV16 release gate summary")
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
        "Release authority: "
        + ", ".join(summary["release_authority"]["blocking_evidence"])
    )
    for action in summary["next_actions"]:
        print(f"Next: {action}")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
