"""V14 release-gate summary and dry-run helpers."""

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts import v11_release_gate_helpers as gate_helpers
from scripts import v13_release_gate_helpers as v13_helpers
from scripts.validate_v6_release_gate import DEFAULT_EVIDENCE_ROOT
from scripts.validate_v6_release_gate import GateStage


def print_dry_run(
    stages: Sequence[GateStage],
    *,
    include_provider_canaries: bool,
) -> None:
    print("V14 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {gate_helpers.format_command(stage.command)}")
    if include_provider_canaries:
        print(
            "- v14 advisory provider evidence: "
            "uv run glassbox provider canary run --cwd . "
            "--output-dir <evidence>/provider-canary --json"
        )
    else:
        print("- v14 advisory provider evidence: skipped by default")
    print("- v14 advisory dashboard evidence: recorded from retained v14 summary")
    print("- v14 advisory accessibility evidence: recorded from retained v14 summary")
    print("- installed wheel smoke: latest dist/glassbox-*.whl")


def record_planned_stages(
    summary: dict[str, Any],
    stages: Sequence[GateStage],
) -> None:
    gate_helpers.record_planned_stages(summary, stages)


def record_installed_wheel_plan(summary: dict[str, Any]) -> None:
    gate_helpers.record_installed_wheel_plan(summary)


def resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    return DEFAULT_EVIDENCE_ROOT / f"{now_stamp()}-v14-gate"


def new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
) -> dict[str, Any]:
    summary = v13_helpers.new_evidence_summary(
        evidence_dir,
        include_provider_canaries=include_provider_canaries,
        dry_run=dry_run,
    )
    summary["gate"] = "v14-release"
    summary["artifacts"].update(
        {
            "v14_task_graph": "docs/tasks-v14.md",
            "v14_review_loop_maturity_contract": (
                "docs/v14-review-loop-maturity-contract.md"
            ),
            "v14_review_loop_maturity_audit": (
                "docs/v14-review-loop-maturity-audit.md"
            ),
            "v14_advisory_review_evidence": "docs/v14-advisory-review-evidence.md",
            "v14_advisory_dashboard_evidence": (
                "docs/v14-advisory-dashboard-evidence.md"
            ),
            "v14_advisory_accessibility_evidence": (
                "docs/v14-advisory-accessibility-evidence.md"
            ),
            "v14_eval_cases": "evals/README.md",
            "v14_publication_boundary": "docs/publication-boundary.md",
        }
    )
    summary["release_authority"]["blocking_evidence"].extend(
        [
            "inherited v13 deterministic release stages",
            "v14 deterministic eval release report",
            "v14 review-loop maturity profile",
            "v14 review-loop maturity eval smoke",
            "v14 review-loop CLI API coverage",
            "v14 dashboard maturity frontend coverage",
            "v14 eval coverage audit",
        ]
    )
    summary["release_authority"].setdefault("advisory_evidence", []).extend(
        [
            "v14 advisory dashboard evidence",
            "v14 advisory accessibility evidence",
        ]
    )
    return summary


def finish_summary(summary: dict[str, Any], status: str) -> None:
    gate_helpers.finish_summary(summary, status)
    if status == "passed":
        summary["next_actions"][-1] = (
            "attach v14 dogfooding, advisory UX, residual-risk, and release "
            "candidate evidence before RC signoff"
        )
    else:
        summary["next_actions"] = [
            action.replace("v11", "v14").replace("v12", "v14").replace("v13", "v14")
            for action in summary["next_actions"]
        ]


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
