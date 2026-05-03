"""Tests for the v12 reviewable-change release gate."""

import json
import subprocess
import sys
from pathlib import Path

from scripts import validate_v12_release_gate as v12_gate

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v12_release_gate.py"


def test_v12_release_gate_dry_run_records_inherited_and_v12_evidence(
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
    assert "V12 release gate dry run" in result.stdout
    assert "v11 confidence release profile" in result.stdout
    assert "v12 reviewable-change release profile" in result.stdout
    assert "v12 advisory provider evidence" in result.stdout
    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    labels = [stage["label"] for stage in summary["stages"]]
    authority = summary["release_authority"]["blocking_evidence"]

    assert summary["gate"] == "v12-release"
    assert summary["status"] == "dry_run"
    assert "v11 deterministic eval release report" in labels
    assert "v11 confidence release profile" in labels
    assert "v12 deterministic eval release report" in labels
    assert "v12 reviewable-change release profile" in labels
    assert "v12 changeset lifecycle smoke" in labels
    assert "v12 eval coverage audit" in labels
    assert summary["blocking"] == summary["stages"]
    assert summary["provider_evidence"]["blocking"] is False
    assert summary["provider_evidence"]["opt_in"] is True
    assert summary["advisory"][0]["label"] == "v12 advisory provider evidence"
    assert summary["advisory"][0]["status"] == "planned"
    assert summary["advisory"][0]["freshness_status"] == "planned"
    assert summary["artifacts"]["v12_release_gate"] == "docs/v12-release-gate.md"
    assert "v12 changeset lifecycle smoke" in authority


def test_v12_gate_stage_plan_adds_changeset_release_checks(tmp_path: Path) -> None:
    stages = v12_gate.build_gate_stages(tmp_path / "evidence")
    labels = [stage.label for stage in stages]

    assert labels[-4:] == [
        "v12 deterministic eval release report",
        "v12 reviewable-change release profile",
        "v12 changeset lifecycle smoke",
        "v12 eval coverage audit",
    ]
    assert any(
        "changeset.reviewable-lifecycle" in stage.command
        and "changeset.branch-candidate-adoption" in stage.command
        for stage in stages
    )
    assert any(
        "release-candidate" in stage.command
        and any("v12-reviewable-change-release" in arg for arg in stage.command)
        for stage in stages
    )


def test_v12_provider_evidence_skip_is_structured(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    summary = v12_gate._new_evidence_summary(
        evidence_dir,
        include_provider_canaries=False,
        dry_run=True,
    )

    v12_gate._record_v12_provider_evidence(
        summary,
        evidence_dir,
        include=False,
        dry_run=True,
    )

    assert summary["advisory"] == [
        {
            "label": "v12 advisory provider evidence",
            "status": "skipped",
            "reason": "pass --include-provider-canaries to collect advisory evidence",
            "blocking": False,
            "freshness_status": "not_collected",
            "latest_status": "not_collected",
            "missing_scenarios": [],
            "evidence_dir": str(evidence_dir / "provider-canary"),
        }
    ]
