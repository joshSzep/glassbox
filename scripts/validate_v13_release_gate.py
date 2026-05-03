"""Run the v13 review-loop release gate scaffold."""

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

from scripts import v11_release_gate_helpers as gate_helpers  # noqa: E402
from scripts.validate_v6_release_gate import DEFAULT_EVIDENCE_ROOT  # noqa: E402
from scripts.validate_v6_release_gate import REPO_ROOT  # noqa: E402
from scripts.validate_v6_release_gate import GateStage  # noqa: E402
from scripts.validate_v6_release_gate import _latest_glassbox_wheel  # noqa: E402
from scripts.validate_v6_release_gate import _run_installed_wheel_smoke  # noqa: E402
from scripts.validate_v11_release_gate import (  # noqa: E402
    load_provider_canary_evidence,
)
from scripts.validate_v12_release_gate import (  # noqa: E402
    build_gate_stages as build_v12_gate_stages,
)


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v13 gate."""

    resolved_evidence_dir = evidence_dir or Path(".glassbox/releases/v13-gate")
    eval_output_dir = _eval_evidence_dir(resolved_evidence_dir)
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Glassbox v13 review-loop release gate.",
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
        _record_v13_provider_evidence(
            summary,
            evidence_dir,
            include=args.include_provider_canaries,
            dry_run=True,
        )
        _record_v13_browser_accessibility_evidence(summary, evidence_dir)
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

    _record_v13_provider_evidence(
        summary,
        evidence_dir,
        include=args.include_provider_canaries,
        dry_run=False,
    )
    _record_v13_browser_accessibility_evidence(summary, evidence_dir)

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
        print("V13 release gate failed: built wheel not found", file=sys.stderr)
        return 1

    summary["artifacts"]["wheel_path"] = str(wheel_path.relative_to(REPO_ROOT))
    exit_code = _run_installed_wheel_smoke(summary, wheel_path)
    _finish_summary(summary, "passed" if exit_code == 0 else "failed")
    _write_evidence_summary(evidence_dir, summary)
    _print_summary(summary)
    return exit_code


def _record_v13_provider_evidence(
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


def _record_v13_browser_accessibility_evidence(
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
        print(f"\nV13 release gate failed: {stage.label}", file=sys.stderr)
    return result.returncode


def _print_dry_run(
    stages: Sequence[GateStage],
    *,
    include_provider_canaries: bool,
) -> None:
    print("V13 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {_format_command(stage.command)}")
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


def _record_planned_stages(
    summary: dict[str, Any],
    stages: Sequence[GateStage],
) -> None:
    gate_helpers.record_planned_stages(summary, stages)


def _record_installed_wheel_plan(summary: dict[str, Any]) -> None:
    gate_helpers.record_installed_wheel_plan(summary)


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
    if requested is not None:
        return requested
    return DEFAULT_EVIDENCE_ROOT / f"{_now_stamp()}-v13-gate"


def _eval_evidence_dir(evidence_dir: Path) -> Path:
    return gate_helpers.eval_evidence_dir(evidence_dir)


def _new_evidence_summary(
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


def _finish_summary(summary: dict[str, Any], status: str) -> None:
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


def _write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nV13 release evidence written to {summary_path}")
    return summary_path


def _print_summary(summary: dict[str, Any]) -> None:
    stage_counts = gate_helpers.count_statuses(summary["stages"])
    advisory_counts = gate_helpers.count_statuses(summary["advisory"])
    print("\nV13 release gate summary")
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


def _format_command(command: Sequence[str]) -> str:
    return gate_helpers.format_command(command)


def _now_iso() -> str:
    return gate_helpers.now_iso()


def _now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
