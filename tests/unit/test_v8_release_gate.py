"""Tests for the v8 release gate script."""

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_v6_release_gate import GateStage
from scripts.validate_v8_release_gate import _new_evidence_summary
from scripts.validate_v8_release_gate import _run_stage
from scripts.validate_v8_release_gate import build_gate_stages

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v8_release_gate.py"


def test_v8_release_gate_stage_composition_inherits_v7_and_adds_autonomy(
    tmp_path: Path,
) -> None:
    stages = build_gate_stages(tmp_path / "evidence")
    labels = [stage.label for stage in stages]

    assert "v7 deterministic eval release profile" in labels
    assert "package build" in labels
    assert "v8 deterministic eval release report" in labels
    assert "v8 autonomy advisory eval profile" in labels
    assert "v8 background job smoke" in labels
    assert "v8 memory smoke" in labels
    assert "v8 repository index smoke" in labels
    assert "v8 observability autonomy summary" in labels

    background_stage = next(
        stage for stage in stages if stage.label == "v8 background job smoke"
    )
    autonomy_eval_stage = next(
        stage for stage in stages if stage.label == "v8 autonomy advisory eval profile"
    )
    assert str(tmp_path / "evidence" / "background-jobs") in background_stage.command
    assert ".glassbox/evals/evidence/autonomy-advisory" in autonomy_eval_stage.command


def test_v8_release_gate_dry_run_lists_stages_and_writes_summary(
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
    assert "V8 release gate dry run" in result.stdout
    assert "v8 background job smoke" in result.stdout
    assert "advisory provider canaries: skipped by default" in result.stdout
    assert "V8 release gate summary" in result.stdout

    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["schema_version"] == 1
    assert summary["gate"] == "v8-release"
    assert summary["status"] == "dry_run"
    assert summary["options"]["dry_run"] is True
    assert summary["artifacts"]["background_job_evidence"] == str(
        evidence_dir / "background-jobs"
    )
    assert summary["artifacts"]["eval_evidence_root"] == ".glassbox/evals/evidence"
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
        "v8 background job smoke"
        in summary["autonomy_boundedness"]["blocking_evidence"]
    )
    assert summary["next_actions"] == ["rerun without --dry-run to execute the gate"]


def test_v8_release_gate_dry_run_records_provider_canary_plan(
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


def test_v8_release_gate_run_stage_records_failure(
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
    assert "V8 release gate failed: intentional failure" in capsys.readouterr().err
