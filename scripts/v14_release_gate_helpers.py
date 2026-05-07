"""V14 release-gate stage and evidence summary helpers."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts import v11_release_gate_helpers as gate_helpers
from scripts import v13_release_gate_helpers as v13_helpers
from scripts.validate_v6_release_gate import DEFAULT_EVIDENCE_ROOT
from scripts.validate_v6_release_gate import REPO_ROOT
from scripts.validate_v6_release_gate import GateStage
from scripts.validate_v11_release_gate import load_provider_canary_evidence

V14_MATURITY_CASES = (
    "changeset.lifecycle-rich-evidence",
    "changeset.response-linked-fixup-inventory",
    "changeset.skipped-advisory-evidence-posture",
)


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v14 gate."""

    resolved_evidence_dir = evidence_dir or Path(".glassbox/releases/v14-gate")
    eval_output_dir = eval_evidence_dir(resolved_evidence_dir)
    return [
        *v13_helpers.build_gate_stages(resolved_evidence_dir),
        GateStage(
            "v14 deterministic eval release report",
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
                str(eval_output_dir / "v14-release-signoff"),
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v14 review-loop maturity profile",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                "--profile",
                "release-candidate",
                "--output-dir",
                str(eval_output_dir / "v14-review-loop-maturity-release"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v14 review-loop maturity eval smoke",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                *V14_MATURITY_CASES,
                "--output-dir",
                str(eval_output_dir / "v14-review-loop-maturity-smoke"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v14 review-loop CLI API coverage",
            (
                "uv",
                "run",
                "pytest",
                "tests/integration/test_cli_interactive_commands.py",
                "tests/integration/test_cli_tui_review_commands.py",
                "tests/integration/test_web_changeset_routes.py",
                "-k",
                "review or feedback or evidence or accessibility",
            ),
        ),
        GateStage(
            "v14 dashboard maturity frontend coverage",
            (
                "pnpm",
                "--dir",
                "frontend",
                "test",
                "--",
                "changeset-console.test.tsx",
                "operator-actions.component.test.tsx",
            ),
        ),
        GateStage(
            "v14 eval coverage audit",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "audit",
                "--profile",
                "release-candidate",
                "--cwd",
                ".",
            ),
        ),
    ]


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


def record_v14_provider_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
    *,
    include: bool,
    dry_run: bool,
) -> None:
    gate_helpers.record_v11_provider_evidence(
        summary,
        evidence_dir,
        include=include,
        dry_run=dry_run,
        run_command=lambda command: subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
        ),
        load_evidence=lambda summary_path: load_provider_canary_evidence(
            REPO_ROOT,
            summary_path=summary_path,
        ),
    )
    if summary["advisory"]:
        latest = summary["advisory"][-1]
        if latest.get("label") == "v11 advisory provider evidence":
            latest["label"] = "v14 advisory provider evidence"


def record_v14_advisory_ux_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
) -> None:
    advisory_entries = [
        (
            "v14 advisory dashboard evidence",
            "fresh dashboard/browser walkthrough retained from GBX-1451; "
            "advisory only and not deterministic release authority",
            "browser",
            "docs/v14-advisory-dashboard-evidence.md",
            ".glassbox/releases/v14-advisory-review-evidence/browser/summary.json",
        ),
        (
            "v14 advisory accessibility evidence",
            "fresh keyboard/focus/responsive pairing retained from GBX-1452; "
            "not certification or WCAG conformance",
            "accessibility",
            "docs/v14-advisory-accessibility-evidence.md",
            ".glassbox/releases/v14-advisory-review-evidence/accessibility/summary.json",
        ),
    ]
    for label, reason, directory_name, docs_path, retained_summary in advisory_entries:
        summary["advisory"].append(
            {
                "label": label,
                "status": "recorded",
                "reason": reason,
                "blocking": False,
                "freshness_status": "retained",
                "latest_status": "recorded",
                "evidence_dir": str(evidence_dir / directory_name),
                "retained_summary": retained_summary,
                "docs": docs_path,
                "required_for_release": False,
            }
        )


def resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    return DEFAULT_EVIDENCE_ROOT / f"{now_stamp()}-v14-gate"


def eval_evidence_dir(evidence_dir: Path) -> Path:
    return gate_helpers.eval_evidence_dir(evidence_dir)


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
            "v14_advisory_review_evidence": ("docs/v14-advisory-review-evidence.md"),
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
