"""Reusable helpers for the v11 release-gate script."""

import json
import sys
from collections.abc import Callable
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

from scripts.validate_v6_release_gate import DEFAULT_EVIDENCE_ROOT
from scripts.validate_v6_release_gate import DIST_DIR
from scripts.validate_v6_release_gate import REPO_ROOT
from scripts.validate_v6_release_gate import GateStage

from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary

type RunCommand = Callable[[Sequence[str]], CompletedProcess[Any]]
type LoadProviderEvidence = Callable[[Path], ProviderCanaryEvidenceSummary]


def resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_EVIDENCE_ROOT / f"{timestamp}-v11-gate"


def eval_evidence_dir(evidence_dir: Path) -> Path:
    return Path(".glassbox/evals") / evidence_dir.name


def new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
    argv: Sequence[str] | None = None,
) -> dict[str, Any]:
    command = list(sys.argv if argv is None else argv)
    return {
        "schema_version": 1,
        "gate": "v11-release",
        "status": "dry_run" if dry_run else "running",
        "started_at": now_iso(),
        "ended_at": None,
        "evidence_dir": str(evidence_dir),
        "command": command,
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
        "blocking": [],
        "advisory": [],
        "artifacts": {
            "dist_dir": str(DIST_DIR.relative_to(REPO_ROOT)),
            "eval_evidence_root": str(eval_evidence_dir(evidence_dir)),
            "provider_canary_evidence": str(evidence_dir / "provider-canary"),
            "packaging_docs": "docs/release-packaging.md",
            "providers_docs": "docs/providers.md",
            "v10_release_gate": "docs/v10-release-gate.md",
            "v11_task_graph": "docs/tasks-v11.md",
            "v11_confidence_contract": "docs/v11-confidence-adoption-contract.md",
            "v11_release_gate": "docs/v11-release-gate.md",
            "v11_eval_cases": "evals/README.md",
            "v11_replay_evals": "docs/replay-evals.md",
            "v11_live_cockpit_evidence": "docs/live-cockpit-evidence-v11.md",
            "v11_accessibility_review": "docs/accessibility-review-v11.md",
            "v11_reviewer_evidence": "docs/reviewer-evidence-bundles.md",
        },
        "provider_evidence": {
            "blocking": False,
            "opt_in": True,
            "freshness_aligned_with_recommendations": True,
            "required_for_release": False,
        },
        "release_authority": {
            "blocking_evidence": [
                "inherited v10 deterministic release stages",
                "v11 package version metadata",
                "v11 deterministic eval release report",
                "v11 confidence release profile",
                "v11 recommendation and recovery guidance smoke",
                "v11 knowledge and branch-search smoke",
                "v11 eval coverage audit",
                "package contents validation",
                "installed wheel smoke",
            ],
            "provider_evidence_authoritative": False,
        },
        "next_actions": [],
    }


def record_v11_provider_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
    *,
    include: bool,
    dry_run: bool,
    run_command: RunCommand,
    load_evidence: LoadProviderEvidence,
) -> None:
    output_dir = evidence_dir / "provider-canary"
    summary_path = output_dir / "provider-canary-summary.json"
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
    if not include:
        summary["advisory"].append(
            {
                "label": "v11 advisory provider evidence",
                "status": "skipped",
                "reason": (
                    "pass --include-provider-canaries to collect advisory evidence"
                ),
                "blocking": False,
                "freshness_status": "not_collected",
                "latest_status": "not_collected",
                "missing_scenarios": [],
                "evidence_dir": str(output_dir),
            }
        )
        return

    if dry_run:
        summary["advisory"].append(
            {
                "label": "v11 advisory provider evidence",
                "command": list(command),
                "status": "planned",
                "reason": "dry run requested",
                "blocking": False,
                "freshness_status": "planned",
                "latest_status": "planned",
                "missing_scenarios": [],
                "evidence_dir": str(output_dir),
                "summary_path": str(summary_path),
            }
        )
        return

    started_at = now_iso()
    print("\n==> v11 advisory provider evidence")
    result = run_command(command)
    evidence = load_evidence(summary_path)
    summary["advisory"].append(
        {
            "label": "v11 advisory provider evidence",
            "command": list(command),
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "started_at": started_at,
            "ended_at": now_iso(),
            "blocking": False,
            "evidence_dir": str(output_dir),
            "summary_path": str(summary_path),
            "latest_status": evidence.latest_status,
            "freshness_status": evidence.freshness_status,
            "missing_scenarios": evidence.missing_scenarios,
            "provider": evidence.provider,
            "model_name": evidence.model_name,
            "scenario_count": evidence.scenario_count,
            "matrix_entry_count": evidence.matrix_entry_count,
            "next_actions": evidence.next_actions,
        }
    )


def print_dry_run(
    stages: Sequence[GateStage],
    *,
    include_provider_canaries: bool,
) -> None:
    print("V11 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {format_command(stage.command)}")
    if include_provider_canaries:
        print(
            "- v11 advisory provider evidence: "
            "uv run glassbox provider canary run --cwd . "
            "--output-dir <evidence>/provider-canary --json"
        )
    else:
        print("- v11 advisory provider evidence: skipped by default")
    print("- installed wheel smoke: latest dist/glassbox-*.whl")


def record_planned_stages(
    summary: dict[str, Any],
    stages: Sequence[GateStage],
) -> None:
    for stage in stages:
        record_stage_result(
            summary,
            label=stage.label,
            command=stage.command,
            status="planned",
            exit_code=None,
            started_at=None,
            ended_at=None,
        )


def record_installed_wheel_plan(summary: dict[str, Any]) -> None:
    record_stage_result(
        summary,
        label="installed wheel smoke",
        command=("latest", "dist/glassbox-*.whl"),
        status="planned",
        exit_code=None,
        started_at=None,
        ended_at=None,
    )


def record_stage_result(
    summary: dict[str, Any],
    *,
    label: str,
    command: Sequence[str],
    status: str,
    exit_code: int | None,
    started_at: str | None,
    ended_at: str | None,
) -> None:
    stage_result = {
        "label": label,
        "command": list(command),
        "status": status,
        "exit_code": exit_code,
        "started_at": started_at,
        "ended_at": ended_at,
    }
    summary["stages"].append(stage_result)
    summary["blocking"].append(stage_result)


def finish_summary(summary: dict[str, Any], status: str) -> None:
    summary["status"] = status
    summary["ended_at"] = now_iso()
    if status == "failed":
        summary["next_actions"].append("inspect failed stage output above")
    elif status == "dry_run":
        summary["next_actions"].append("rerun without --dry-run to execute the gate")
    elif status == "passed":
        summary["next_actions"].append(
            "attach v11 dogfooding, live cockpit, accessibility, and residual-risk "
            "evidence before RC signoff"
        )


def write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nV11 release evidence written to {summary_path}")
    return summary_path


def print_summary(summary: dict[str, Any]) -> None:
    stage_counts = count_statuses(summary["stages"])
    advisory_counts = count_statuses(summary["advisory"])
    print("\nV11 release gate summary")
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


def count_statuses(items: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def format_command(command: Sequence[str]) -> str:
    return " ".join(command)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
