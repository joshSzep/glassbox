"""Tests for the v10 release gate script."""

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_v6_release_gate import GateStage
from scripts.validate_v10_release_gate import _new_evidence_summary
from scripts.validate_v10_release_gate import _record_provider_canary
from scripts.validate_v10_release_gate import _run_stage
from scripts.validate_v10_release_gate import build_gate_stages

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v10_release_gate.py"


def test_v10_release_gate_stage_composition_inherits_v9_and_adds_long_run(
    tmp_path: Path,
) -> None:
    stages = build_gate_stages(tmp_path / "evidence")
    labels = [stage.label for stage in stages]

    assert "v9 deterministic eval release report" in labels
    assert "package build" in labels
    assert "installed wheel smoke" not in labels
    assert "v10 marked process-boundary pytest suite" in labels
    assert "v10 deterministic eval release report" in labels
    assert "v10 long-run release profile" in labels
    assert "v10 checkpoint/compaction smoke" in labels
    assert "v10 tool-attempt recovery smoke" in labels
    assert "v10 long-run cockpit smoke" in labels
    assert "v10 provider recovery policy check" in labels

    expected_evidence_paths = {
        "v10 deterministic eval release report": (
            ".glassbox/evals/evidence/v10-release-signoff"
        ),
        "v10 long-run release profile": ".glassbox/evals/evidence/long-run-release",
        "v10 checkpoint/compaction smoke": (
            ".glassbox/evals/evidence/checkpoint-compaction-smoke"
        ),
        "v10 tool-attempt recovery smoke": (
            ".glassbox/evals/evidence/tool-attempt-recovery-smoke"
        ),
        "v10 long-run cockpit smoke": ".glassbox/evals/evidence/long-run-cockpit-smoke",
    }
    for label, evidence_path in expected_evidence_paths.items():
        stage = next(stage for stage in stages if stage.label == label)
        assert evidence_path in stage.command

    marker_stage = next(
        stage
        for stage in stages
        if stage.label == "v10 marked process-boundary pytest suite"
    )
    assert marker_stage.command == (
        "uv",
        "run",
        "pytest",
        "-m",
        "daemon or subprocess or timeout or tui",
        "-q",
    )


def test_v10_release_gate_dry_run_lists_stages_and_writes_summary(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence"
    result = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--dry-run",
            "--evidence-dir",
            str(evidence_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "V10 release gate dry run" in result.stdout
    assert "v10 marked process-boundary pytest suite" in result.stdout
    assert "v10 checkpoint/compaction smoke" in result.stdout
    assert "v10 provider recovery policy check" in result.stdout
    assert "advisory provider canaries: skipped by default" in result.stdout
    assert "V10 release gate summary" in result.stdout

    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["schema_version"] == 1
    assert summary["gate"] == "v10-release"
    assert summary["status"] == "dry_run"
    assert summary["options"]["dry_run"] is True
    assert summary["artifacts"]["eval_evidence_root"] == ".glassbox/evals/evidence"
    assert summary["artifacts"]["v10_release_gate"] == "docs/v10-release-gate.md"
    assert summary["artifacts"]["v10_task_graph"] == "docs/tasks-v10.md"
    assert summary["advisory"] == [
        {
            "label": "advisory provider canaries",
            "status": "skipped",
            "reason": "pass --include-provider-canaries to run when configured",
            "blocking": False,
        }
    ]
    assert any(stage["label"] == "installed wheel smoke" for stage in summary["stages"])
    assert (
        "v10 marked process-boundary pytest suite"
        in summary["long_run_readiness"]["blocking_evidence"]
    )
    assert (
        "v10 checkpoint/compaction smoke"
        in summary["long_run_readiness"]["blocking_evidence"]
    )
    assert (
        "v10 marked process-boundary pytest suite"
        in summary["release_authority"]["blocking_evidence"]
    )
    assert (
        "v10 deterministic eval release report"
        in summary["release_authority"]["blocking_evidence"]
    )
    assert summary["long_run_readiness"]["proves_recoverability"] is True
    assert summary["long_run_readiness"]["proves_compaction_provenance"] is True
    assert summary["release_authority"]["provider_evidence_authoritative"] is False
    assert summary["next_actions"] == ["rerun without --dry-run to execute the gate"]


def test_v10_release_gate_dry_run_records_provider_canary_plan(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence"
    result = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--dry-run",
            "--include-provider-canaries",
            "--evidence-dir",
            str(evidence_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))

    assert summary["advisory"][0]["status"] == "planned"
    assert summary["advisory"][0]["reason"] == "dry run requested"
    assert summary["advisory"][0]["blocking"] is False
    assert summary["advisory"][0]["evidence_dir"] == str(
        evidence_dir / "provider-canary"
    )


def test_v10_release_gate_run_stage_records_failure(
    tmp_path: Path,
    capsys,
) -> None:
    summary = _new_evidence_summary(
        tmp_path / "evidence",
        include_provider_canaries=False,
        dry_run=False,
    )
    stage = GateStage(
        "intentional failure",
        (sys.executable, "-c", "raise SystemExit(3)"),
    )

    exit_code = _run_stage(summary, stage)

    assert exit_code == 3
    assert summary["stages"] == [
        {
            "label": "intentional failure",
            "command": list(stage.command),
            "status": "failed",
            "exit_code": 3,
            "started_at": summary["stages"][0]["started_at"],
            "ended_at": summary["stages"][0]["ended_at"],
        }
    ]
    assert "V10 release gate failed: intentional failure" in capsys.readouterr().err


def test_v10_release_gate_provider_canary_skip_is_explicit(tmp_path: Path) -> None:
    summary = _new_evidence_summary(
        tmp_path / "evidence",
        include_provider_canaries=False,
        dry_run=True,
    )

    _record_provider_canary(
        summary,
        tmp_path / "evidence",
        include=False,
        dry_run=True,
    )

    assert summary["advisory"] == [
        {
            "label": "advisory provider canaries",
            "status": "skipped",
            "reason": "pass --include-provider-canaries to run when configured",
            "blocking": False,
        }
    ]
