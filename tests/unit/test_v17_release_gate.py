"""Tests for the v17 local-handoff release gate."""

import json
import subprocess
import sys
from pathlib import Path

from scripts import validate_v17_release_gate as v17_gate

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v17_release_gate.py"


def test_v17_release_gate_dry_run_records_local_handoff_evidence(
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
    assert "V17 release gate dry run" in result.stdout
    assert "v17 local handoff release profile" in result.stdout
    assert "v17 local handoff eval smoke" in result.stdout
    assert "v17 handoff package smoke" in result.stdout
    assert "v17 redaction preview smoke" in result.stdout
    assert "v17 import triage smoke" in result.stdout
    assert "v17 custody smoke" in result.stdout
    assert "v17 local handoff CLI API coverage" in result.stdout
    assert "v17 local handoff frontend smoke" in result.stdout
    assert "v17 package contents validation" in result.stdout
    assert "v17 advisory provider evidence" in result.stdout
    assert "v17 advisory dashboard browser evidence" in result.stdout
    assert "v17 advisory accessibility evidence" in result.stdout
    assert "v17 dogfooding evidence" in result.stdout
    assert "v17 manual release evidence" in result.stdout

    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    labels = [stage["label"] for stage in summary["stages"]]
    advisory_labels = [entry["label"] for entry in summary["advisory"]]
    authority = summary["release_authority"]["blocking_evidence"]

    assert summary["gate"] == "v17-release"
    assert summary["status"] == "dry_run"
    assert "v16 operator flow release profile" in labels
    assert "v17 deterministic eval release report" in labels
    assert "v17 local handoff release profile" in labels
    assert "v17 local handoff eval smoke" in labels
    assert "v17 handoff package smoke" in labels
    assert "v17 redaction preview smoke" in labels
    assert "v17 import triage smoke" in labels
    assert "v17 custody smoke" in labels
    assert "v17 local handoff CLI API coverage" in labels
    assert "v17 local handoff frontend smoke" in labels
    assert "v17 package contents validation" in labels
    assert "v17 release docs" in labels
    assert "v17 eval coverage audit" in labels
    assert summary["blocking"] == summary["stages"]
    assert advisory_labels[-5:] == [
        "v17 advisory provider evidence",
        "v17 advisory dashboard browser evidence",
        "v17 advisory accessibility evidence",
        "v17 dogfooding evidence",
        "v17 manual release evidence",
    ]
    assert summary["advisory"][-5]["status"] == "planned"
    assert summary["advisory"][-4]["status"] == "planned"
    assert summary["advisory"][-3]["required_for_release"] is False
    assert summary["advisory"][-2]["status"] == "planned"
    assert summary["advisory"][-1]["status"] == "planned"
    assert summary["artifacts"]["v17_task_graph"] == "docs/tasks-v17.md"
    assert summary["artifacts"]["v17_release_gate"] == "docs/v17-release-gate.md"
    assert summary["artifacts"]["v17_local_handoff_guide"] == "docs/local-handoff.md"
    assert "inherited v16 deterministic release stages" in authority
    assert "v17 local handoff eval smoke" in authority
    assert "v17 package contents validation" in authority


def test_v17_gate_stage_plan_adds_local_handoff_checks(
    tmp_path: Path,
) -> None:
    stages = v17_gate.build_gate_stages(tmp_path / "evidence")
    labels = [stage.label for stage in stages]

    assert labels[-12:] == [
        "v17 deterministic eval release report",
        "v17 local handoff release profile",
        "v17 local handoff eval smoke",
        "v17 handoff package smoke",
        "v17 redaction preview smoke",
        "v17 import triage smoke",
        "v17 custody smoke",
        "v17 local handoff CLI API coverage",
        "v17 local handoff frontend smoke",
        "v17 package contents validation",
        "v17 release docs",
        "v17 eval coverage audit",
    ]
    assert any(
        all(case_id in stage.command for case_id in v17_gate.V17_LOCAL_HANDOFF_CASES)
        for stage in stages
    )
    assert any(
        stage.label == "v17 handoff package smoke"
        and stage.command[-2:] == ("inspect", "--help")
        for stage in stages
    )
    assert any(
        stage.label == "v17 redaction preview smoke"
        and "tests/unit/test_handoff_redaction_preview.py" in stage.command
        for stage in stages
    )
    assert any(
        stage.label == "v17 import triage smoke"
        and "tests/unit/test_handoff_import_triage.py" in stage.command
        for stage in stages
    )
    assert any(
        stage.label == "v17 custody smoke"
        and "tests/unit/test_handoff_decisions.py" in stage.command
        for stage in stages
    )
    assert any(
        "tests/integration/test_cli_handoff_commands.py" in stage.command
        and "tests/integration/test_web_handoff_routes.py" in stage.command
        for stage in stages
    )
    assert any(
        "handoff-cockpit.test.tsx" in stage.command
        and "generated-api-types.test.ts" in stage.command
        for stage in stages
    )
