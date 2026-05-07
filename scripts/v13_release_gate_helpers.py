"""V13 release-gate stage and evidence summary helpers."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts import v11_release_gate_helpers as gate_helpers
from scripts.validate_v6_release_gate import DEFAULT_EVIDENCE_ROOT
from scripts.validate_v6_release_gate import REPO_ROOT
from scripts.validate_v6_release_gate import GateStage
from scripts.validate_v11_release_gate import load_provider_canary_evidence
from scripts.validate_v12_release_gate import build_gate_stages as build_v12_gate_stages


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v13 gate."""

    resolved_evidence_dir = evidence_dir or Path(".glassbox/releases/v13-gate")
    eval_output_dir = eval_evidence_dir(resolved_evidence_dir)
    return [
        *build_v12_gate_stages(resolved_evidence_dir),
        GateStage(
            "v13 deterministic eval release report",
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
                str(eval_output_dir / "v13-release-signoff"),
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v13 review-loop release profile",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                "--profile",
                "release-candidate",
                "--output-dir",
                str(eval_output_dir / "v13-review-loop-release"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v13 review-loop eval smoke",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                "changeset.review-loop-lifecycle",
                "changeset.in-session-review-ux",
                "--output-dir",
                str(eval_output_dir / "v13-review-loop-smoke"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v13 review-loop command coverage",
            (
                "uv",
                "run",
                "pytest",
                "tests/unit/test_cli_interactive_session.py",
                "tests/integration/test_cli_tui_review_commands.py",
                "tests/integration/test_cli_interactive_commands.py",
                "-k",
                "review",
            ),
        ),
        GateStage(
            "v13 eval coverage audit",
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
    print("V13 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {gate_helpers.format_command(stage.command)}")
    if include_provider_canaries:
        print(
            "- v13 advisory provider evidence: "
            "uv run glassbox provider canary run --cwd . "
            "--output-dir <evidence>/provider-canary --json"
        )
    else:
        print("- v13 advisory provider evidence: skipped by default")
    print("- v13 advisory browser evidence: skipped by default")
    print("- v13 advisory accessibility evidence: skipped by default")
    print("- installed wheel smoke: latest dist/glassbox-*.whl")


def record_planned_stages(
    summary: dict[str, Any],
    stages: Sequence[GateStage],
) -> None:
    gate_helpers.record_planned_stages(summary, stages)


def record_installed_wheel_plan(summary: dict[str, Any]) -> None:
    gate_helpers.record_installed_wheel_plan(summary)


def record_v13_provider_evidence(
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
            latest["label"] = "v13 advisory provider evidence"


def record_v13_browser_accessibility_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
) -> None:
    advisory_entries = [
        (
            "v13 advisory browser evidence",
            "manual browser/dashboard evidence is collected during dogfooding "
            "or release-candidate review, not by this deterministic gate",
            "browser-dashboard",
            "docs/browser-accessibility-evidence.md",
        ),
        (
            "v13 advisory accessibility evidence",
            "accessibility pairing evidence is manual/advisory until a "
            "deterministic fixture-backed contract is promoted",
            "accessibility",
            "docs/browser-accessibility-evidence.md",
        ),
    ]
    for label, reason, directory_name, docs_path in advisory_entries:
        summary["advisory"].append(
            {
                "label": label,
                "status": "skipped",
                "reason": reason,
                "blocking": False,
                "freshness_status": "not_collected",
                "latest_status": "not_collected",
                "evidence_dir": str(evidence_dir / directory_name),
                "docs": docs_path,
                "required_for_release": False,
            }
        )


def resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    return DEFAULT_EVIDENCE_ROOT / f"{now_stamp()}-v13-gate"


def eval_evidence_dir(evidence_dir: Path) -> Path:
    return gate_helpers.eval_evidence_dir(evidence_dir)


def new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
) -> dict[str, Any]:
    summary = gate_helpers.new_evidence_summary(
        evidence_dir,
        include_provider_canaries=include_provider_canaries,
        dry_run=dry_run,
    )
    summary["gate"] = "v13-release"
    summary["artifacts"].update(
        {
            "v13_task_graph": "docs/tasks-v13.md",
            "v13_review_loop_contract": "docs/v13-review-loop-contract.md",
            "v13_review_loop_ux_audit": "docs/v13-review-loop-ux-audit.md",
            "v13_release_gate": "docs/v13-release-gate.md",
            "v13_eval_cases": "evals/README.md",
            "v13_replay_evals": "docs/replay-evals.md",
            "v13_browser_accessibility_evidence": (
                "docs/browser-accessibility-evidence.md"
            ),
            "v13_publication_boundary": "docs/publication-boundary.md",
        }
    )
    summary["release_authority"]["blocking_evidence"].extend(
        [
            "inherited v12 deterministic release stages",
            "v12 deterministic eval release report",
            "v12 reviewable-change release profile",
            "v12 changeset lifecycle smoke",
            "v12 eval coverage audit",
            "v13 deterministic eval release report",
            "v13 review-loop release profile",
            "v13 review-loop eval smoke",
            "v13 review-loop command coverage",
            "v13 eval coverage audit",
        ]
    )
    return summary


def finish_summary(summary: dict[str, Any], status: str) -> None:
    gate_helpers.finish_summary(summary, status)
    if status == "passed":
        summary["next_actions"][-1] = (
            "attach v13 dogfooding, browser/dashboard, accessibility, provider, "
            "and residual-risk evidence before RC signoff"
        )
    else:
        summary["next_actions"] = [
            action.replace("v11", "v13").replace("v12", "v13")
            for action in summary["next_actions"]
        ]


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
