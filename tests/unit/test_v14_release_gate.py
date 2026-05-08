"""Tests for the v14 review-loop maturity release gate."""

import json
import subprocess
import sys
from pathlib import Path

from scripts import v14_release_gate_advisory as v14_advisory
from scripts import v14_release_gate_helpers as v14_helpers
from scripts import v14_release_gate_stages as v14_stages
from scripts import v14_release_gate_summary as v14_summary
from scripts import validate_v14_release_gate as v14_gate

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v14_release_gate.py"


def test_v14_release_gate_dry_run_records_maturity_evidence(
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
    assert "V14 release gate dry run" in result.stdout
    assert "v13 review-loop release profile" in result.stdout
    assert "v14 review-loop maturity profile" in result.stdout
    assert "v14 advisory provider evidence" in result.stdout
    assert "v14 advisory dashboard evidence" in result.stdout
    assert "v14 advisory accessibility evidence" in result.stdout
    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    labels = [stage["label"] for stage in summary["stages"]]
    advisory_labels = [entry["label"] for entry in summary["advisory"]]
    authority = summary["release_authority"]["blocking_evidence"]

    assert summary["gate"] == "v14-release"
    assert summary["status"] == "dry_run"
    assert "v13 review-loop release profile" in labels
    assert "v14 deterministic eval release report" in labels
    assert "v14 review-loop maturity profile" in labels
    assert "v14 review-loop maturity eval smoke" in labels
    assert "v14 review-loop CLI API coverage" in labels
    assert "v14 dashboard maturity frontend coverage" in labels
    assert "v14 eval coverage audit" in labels
    assert summary["blocking"] == summary["stages"]
    assert advisory_labels == [
        "v14 advisory provider evidence",
        "v14 advisory dashboard evidence",
        "v14 advisory accessibility evidence",
    ]
    assert summary["advisory"][0]["status"] == "planned"
    assert summary["advisory"][1]["status"] == "recorded"
    assert summary["advisory"][2]["status"] == "recorded"
    assert summary["advisory"][1]["blocking"] is False
    assert summary["advisory"][2]["required_for_release"] is False
    assert summary["artifacts"]["v14_task_graph"] == "docs/tasks-v14.md"
    assert summary["artifacts"]["v14_advisory_dashboard_evidence"] == (
        "docs/v14-advisory-dashboard-evidence.md"
    )
    assert summary["artifacts"]["v14_advisory_accessibility_evidence"] == (
        "docs/v14-advisory-accessibility-evidence.md"
    )
    assert "inherited v13 deterministic release stages" in authority
    assert "v14 review-loop maturity eval smoke" in authority
    assert "v14 dashboard maturity frontend coverage" in authority


def test_v14_gate_stage_plan_adds_maturity_checks(tmp_path: Path) -> None:
    stages = v14_gate.build_gate_stages(tmp_path / "evidence")
    labels = [stage.label for stage in stages]

    assert v14_helpers.V14_MATURITY_CASES == v14_stages.V14_MATURITY_CASES
    assert labels[-6:] == [
        "v14 deterministic eval release report",
        "v14 review-loop maturity profile",
        "v14 review-loop maturity eval smoke",
        "v14 review-loop CLI API coverage",
        "v14 dashboard maturity frontend coverage",
        "v14 eval coverage audit",
    ]
    assert any(
        all(case_id in stage.command for case_id in v14_stages.V14_MATURITY_CASES)
        for stage in stages
    )
    assert any(
        "tests/integration/test_web_changeset_routes.py" in stage.command
        and "review or feedback or evidence or accessibility" in stage.command
        for stage in stages
    )
    assert any(
        "changeset-console.test.tsx" in stage.command
        and "operator-actions.component.test.tsx" in stage.command
        for stage in stages
    )


def test_v14_advisory_ux_evidence_is_structured(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    summary = v14_gate._new_evidence_summary(
        evidence_dir,
        include_provider_canaries=False,
        dry_run=True,
    )

    v14_advisory.record_v14_advisory_ux_evidence(summary, evidence_dir)

    assert summary["advisory"] == [
        {
            "label": "v14 advisory dashboard evidence",
            "status": "recorded",
            "reason": (
                "fresh dashboard/browser walkthrough retained from GBX-1451; "
                "advisory only and not deterministic release authority"
            ),
            "blocking": False,
            "freshness_status": "retained",
            "latest_status": "recorded",
            "evidence_dir": str(evidence_dir / "browser"),
            "retained_summary": (
                ".glassbox/releases/v14-advisory-review-evidence/browser/summary.json"
            ),
            "docs": "docs/v14-advisory-dashboard-evidence.md",
            "required_for_release": False,
        },
        {
            "label": "v14 advisory accessibility evidence",
            "status": "recorded",
            "reason": (
                "fresh keyboard/focus/responsive pairing retained from GBX-1452; "
                "not certification or WCAG conformance"
            ),
            "blocking": False,
            "freshness_status": "retained",
            "latest_status": "recorded",
            "evidence_dir": str(evidence_dir / "accessibility"),
            "retained_summary": (
                ".glassbox/releases/v14-advisory-review-evidence/accessibility/summary.json"
            ),
            "docs": "docs/v14-advisory-accessibility-evidence.md",
            "required_for_release": False,
        },
    ]


def test_v14_helper_summary_metadata_marks_maturity_authority(
    tmp_path: Path,
) -> None:
    summary = v14_summary.new_evidence_summary(
        tmp_path / "evidence",
        include_provider_canaries=False,
        dry_run=True,
    )

    assert summary["gate"] == "v14-release"
    assert summary["artifacts"]["v14_review_loop_maturity_contract"] == (
        "docs/v14-review-loop-maturity-contract.md"
    )
    assert (
        "v14 review-loop maturity profile"
        in (summary["release_authority"]["blocking_evidence"])
    )
    assert (
        "v14 advisory dashboard evidence"
        in (summary["release_authority"]["advisory_evidence"])
    )
