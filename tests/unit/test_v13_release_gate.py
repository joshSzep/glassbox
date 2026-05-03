"""Tests for the v13 review-loop release gate."""

import json
import subprocess
import sys
from pathlib import Path

from scripts import validate_v13_release_gate as v13_gate

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v13_release_gate.py"


def test_v13_release_gate_dry_run_records_review_loop_evidence(
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
    assert "V13 release gate dry run" in result.stdout
    assert "v12 reviewable-change release profile" in result.stdout
    assert "v13 review-loop release profile" in result.stdout
    assert "v13 advisory provider evidence" in result.stdout
    assert "v13 advisory browser evidence" in result.stdout
    assert "v13 advisory accessibility evidence" in result.stdout
    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    labels = [stage["label"] for stage in summary["stages"]]
    advisory_labels = [entry["label"] for entry in summary["advisory"]]
    authority = summary["release_authority"]["blocking_evidence"]

    assert summary["gate"] == "v13-release"
    assert summary["status"] == "dry_run"
    assert "v12 deterministic eval release report" in labels
    assert "v12 reviewable-change release profile" in labels
    assert "v13 deterministic eval release report" in labels
    assert "v13 review-loop release profile" in labels
    assert "v13 review-loop eval smoke" in labels
    assert "v13 review-loop command coverage" in labels
    assert "v13 eval coverage audit" in labels
    assert summary["blocking"] == summary["stages"]
    assert summary["provider_evidence"]["blocking"] is False
    assert summary["provider_evidence"]["opt_in"] is True
    assert advisory_labels == [
        "v13 advisory provider evidence",
        "v13 advisory browser evidence",
        "v13 advisory accessibility evidence",
    ]
    assert summary["advisory"][0]["status"] == "planned"
    assert summary["advisory"][1]["status"] == "skipped"
    assert summary["advisory"][2]["status"] == "skipped"
    assert summary["artifacts"]["v13_release_gate"] == "docs/v13-release-gate.md"
    assert "inherited v12 deterministic release stages" in authority
    assert "v12 changeset lifecycle smoke" in authority
    assert "v13 review-loop eval smoke" in authority
    assert "v13 review-loop command coverage" in authority


def test_v13_gate_stage_plan_adds_review_loop_checks(tmp_path: Path) -> None:
    stages = v13_gate.build_gate_stages(tmp_path / "evidence")
    labels = [stage.label for stage in stages]

    assert labels[-5:] == [
        "v13 deterministic eval release report",
        "v13 review-loop release profile",
        "v13 review-loop eval smoke",
        "v13 review-loop command coverage",
        "v13 eval coverage audit",
    ]
    assert any(
        "changeset.review-loop-lifecycle" in stage.command
        and "changeset.in-session-review-ux" in stage.command
        for stage in stages
    )
    assert any(
        "tests/integration/test_cli_tui_review_commands.py" in stage.command
        and "tests/integration/test_cli_interactive_commands.py" in stage.command
        for stage in stages
    )
    assert any(
        "release-candidate" in stage.command
        and any("v13-review-loop-release" in arg for arg in stage.command)
        for stage in stages
    )


def test_v13_advisory_browser_and_accessibility_evidence_is_structured(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence"
    summary = v13_gate._new_evidence_summary(
        evidence_dir,
        include_provider_canaries=False,
        dry_run=True,
    )

    v13_gate._record_v13_browser_accessibility_evidence(summary, evidence_dir)

    assert summary["advisory"] == [
        {
            "label": "v13 advisory browser evidence",
            "status": "skipped",
            "reason": (
                "manual browser/dashboard evidence is collected during dogfooding "
                "or release-candidate review, not by this deterministic gate"
            ),
            "blocking": False,
            "freshness_status": "not_collected",
            "latest_status": "not_collected",
            "evidence_dir": str(evidence_dir / "browser-dashboard"),
            "docs": "docs/browser-accessibility-evidence.md",
            "required_for_release": False,
        },
        {
            "label": "v13 advisory accessibility evidence",
            "status": "skipped",
            "reason": (
                "accessibility pairing evidence is manual/advisory until a "
                "deterministic fixture-backed contract is promoted"
            ),
            "blocking": False,
            "freshness_status": "not_collected",
            "latest_status": "not_collected",
            "evidence_dir": str(evidence_dir / "accessibility"),
            "docs": "docs/browser-accessibility-evidence.md",
            "required_for_release": False,
        },
    ]
