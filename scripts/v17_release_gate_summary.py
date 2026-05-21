"""V17 release-gate summary and dry-run helpers."""

import json
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts import v11_release_gate_helpers as gate_helpers
from scripts import v16_release_gate_helpers as v16_helpers
from scripts import v17_release_gate_advisory as advisory_helpers
from scripts.validate_v6_release_gate import DEFAULT_EVIDENCE_ROOT
from scripts.validate_v6_release_gate import GateStage


def print_dry_run(
    stages: Sequence[GateStage],
    *,
    include_provider_canaries: bool,
) -> None:
    print("V17 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {gate_helpers.format_command(stage.command)}")
    print(
        advisory_helpers.provider_dry_run_line(
            include_provider_canaries=include_provider_canaries,
        )
    )
    for line in advisory_helpers.advisory_dry_run_lines():
        print(line)
    print("- installed wheel smoke: latest dist/glassbox-*.whl")


def record_planned_stages(
    summary: dict[str, Any],
    stages: Sequence[GateStage],
) -> None:
    v16_helpers.record_planned_stages(summary, stages)


def record_installed_wheel_plan(summary: dict[str, Any]) -> None:
    v16_helpers.record_installed_wheel_plan(summary)


def resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    return DEFAULT_EVIDENCE_ROOT / f"{now_stamp()}-v17-gate"


def new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
) -> dict[str, Any]:
    summary = v16_helpers.new_evidence_summary(
        evidence_dir,
        include_provider_canaries=include_provider_canaries,
        dry_run=dry_run,
    )
    summary["gate"] = "v17-release"
    summary["artifacts"].update(
        {
            "v17_task_graph": "docs/tasks-v17.md",
            "v17_local_handoff_contract": "docs/v17-local-handoff-contract.md",
            "v17_local_handoff_audit": "docs/v17-local-handoff-audit.md",
            "v17_local_handoff_guide": "docs/local-handoff.md",
            "v17_release_gate": "docs/v17-release-gate.md",
            "v17_eval_cases": "evals/README.md",
            "v17_replay_evals": "docs/replay-evals.md",
        }
    )
    summary["release_authority"]["blocking_evidence"].extend(
        [
            "inherited v16 deterministic release stages",
            "v17 deterministic eval release report",
            "v17 local handoff release profile",
            "v17 local handoff eval smoke",
            "v17 handoff package smoke",
            "v17 redaction preview smoke",
            "v17 import triage smoke",
            "v17 custody smoke",
            "v17 local handoff CLI API coverage",
            "v17 local handoff frontend smoke",
            "v17 package contents validation",
            "v17 release docs",
            "v17 eval coverage audit",
        ]
    )
    summary["release_authority"].setdefault("advisory_evidence", []).extend(
        [
            "v17 advisory provider evidence",
            "v17 advisory dashboard browser evidence",
            "v17 advisory accessibility evidence",
            "v17 dogfooding evidence",
            "v17 manual release evidence",
        ]
    )
    return summary


def finish_summary(summary: dict[str, Any], status: str) -> None:
    gate_helpers.finish_summary(summary, status)
    if status == "passed":
        summary["next_actions"][-1] = (
            "attach v17 dogfooding, advisory handoff cockpit, residual-risk, "
            "and release-candidate evidence before RC signoff"
        )
    else:
        summary["next_actions"] = [
            action.replace("v11", "v17")
            .replace("v14", "v17")
            .replace("v15", "v17")
            .replace("v16", "v17")
            for action in summary["next_actions"]
        ]


def write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nV17 release evidence written to {summary_path}")
    return summary_path


def print_summary(summary: dict[str, Any]) -> None:
    stage_counts = gate_helpers.count_statuses(summary["stages"])
    advisory_counts = gate_helpers.count_statuses(summary["advisory"])
    print("\nV17 release gate summary")
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
