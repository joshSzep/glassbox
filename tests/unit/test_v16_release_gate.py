"""Tests for the v16 operator-flow release gate."""

import json
import subprocess
import sys
from pathlib import Path

from scripts import validate_v16_release_gate as v16_gate

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v16_release_gate.py"


def test_v16_release_gate_dry_run_records_operator_flow_evidence(
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
    assert "V16 release gate dry run" in result.stdout
    assert "v16 operator flow release profile" in result.stdout
    assert "v16 operator flow eval smoke" in result.stdout
    assert "v16 operator queue smoke" in result.stdout
    assert "v16 evidence graph smoke" in result.stdout
    assert "v16 verification plan smoke" in result.stdout
    assert "v16 operator flow runtime coverage" in result.stdout
    assert "v16 operator flow CLI API coverage" in result.stdout
    assert "v16 operator flow frontend smoke" in result.stdout
    assert "v16 package contents validation" in result.stdout
    assert "v16 advisory provider evidence" in result.stdout
    assert "v16 advisory dashboard browser evidence" in result.stdout
    assert "v16 advisory accessibility evidence" in result.stdout
    assert "v16 dogfooding evidence" in result.stdout
    assert "v16 manual release evidence" in result.stdout

    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    labels = [stage["label"] for stage in summary["stages"]]
    advisory_labels = [entry["label"] for entry in summary["advisory"]]
    authority = summary["release_authority"]["blocking_evidence"]

    assert summary["gate"] == "v16-release"
    assert summary["status"] == "dry_run"
    assert "v15 repository intelligence release profile" in labels
    assert "v16 deterministic eval release report" in labels
    assert "v16 operator flow release profile" in labels
    assert "v16 operator flow eval smoke" in labels
    assert "v16 operator queue smoke" in labels
    assert "v16 evidence graph smoke" in labels
    assert "v16 verification plan smoke" in labels
    assert "v16 operator flow runtime coverage" in labels
    assert "v16 operator flow CLI API coverage" in labels
    assert "v16 operator flow frontend smoke" in labels
    assert "v16 package contents validation" in labels
    assert "v16 release docs" in labels
    assert "v16 eval coverage audit" in labels
    assert summary["blocking"] == summary["stages"]
    assert advisory_labels[-5:] == [
        "v16 advisory provider evidence",
        "v16 advisory dashboard browser evidence",
        "v16 advisory accessibility evidence",
        "v16 dogfooding evidence",
        "v16 manual release evidence",
    ]
    assert summary["advisory"][-5]["status"] == "planned"
    assert summary["advisory"][-4]["status"] == "recorded"
    assert summary["advisory"][-3]["required_for_release"] is False
    assert summary["advisory"][-2]["status"] == "recorded"
    assert summary["advisory"][-1]["status"] == "recorded"
    assert summary["artifacts"]["v16_task_graph"] == "docs/tasks-v16.md"
    assert summary["artifacts"]["v16_release_gate"] == "docs/v16-release-gate.md"
    assert summary["artifacts"]["v16_flow_cockpit_evidence"] == (
        "docs/v16-flow-cockpit-evidence.md"
    )
    assert "inherited v15 deterministic release stages" in authority
    assert "v16 operator flow eval smoke" in authority
    assert "v16 package contents validation" in authority


def test_v16_gate_stage_plan_adds_operator_flow_checks(
    tmp_path: Path,
) -> None:
    stages = v16_gate.build_gate_stages(tmp_path / "evidence")
    labels = [stage.label for stage in stages]

    assert labels[-12:] == [
        "v16 deterministic eval release report",
        "v16 operator flow release profile",
        "v16 operator flow eval smoke",
        "v16 operator queue smoke",
        "v16 evidence graph smoke",
        "v16 verification plan smoke",
        "v16 operator flow runtime coverage",
        "v16 operator flow CLI API coverage",
        "v16 operator flow frontend smoke",
        "v16 package contents validation",
        "v16 release docs",
        "v16 eval coverage audit",
    ]
    assert any(
        all(case_id in stage.command for case_id in v16_gate.V16_OPERATOR_FLOW_CASES)
        for stage in stages
    )
    assert any(
        stage.label == "v16 operator queue smoke"
        and stage.command[-4:] == ("list", "--json", "--cwd", ".")
        for stage in stages
    )
    assert any(
        stage.label == "v16 evidence graph smoke"
        and stage.command[-2:] == ("evidence-graph", "--help")
        for stage in stages
    )
    assert any(
        stage.label == "v16 verification plan smoke"
        and "docs/tasks-v16.md" in stage.command
        for stage in stages
    )
    assert any(
        "tests/unit/test_session_query_derivation.py" in stage.command
        and "tests/unit/test_evidence_graph.py" in stage.command
        for stage in stages
    )
    assert any(
        "tests/integration/test_cli_changeset_commands.py" in stage.command
        and "tests/integration/test_web_changeset_routes.py" in stage.command
        for stage in stages
    )
    assert any(
        "workspace-overview.test.ts" in stage.command
        and "session-inspector.test.ts" in stage.command
        for stage in stages
    )
