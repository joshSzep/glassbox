"""Tests for the v15 repository-intelligence release gate."""

import json
import subprocess
import sys
from pathlib import Path

from scripts import validate_v15_release_gate as v15_gate

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v15_release_gate.py"


def test_v15_release_gate_dry_run_records_repository_intelligence_evidence(
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
    assert "V15 release gate dry run" in result.stdout
    assert "v15 repository intelligence release profile" in result.stdout
    assert "v15 repository intelligence eval smoke" in result.stdout
    assert "v15 repository intelligence runtime coverage" in result.stdout
    assert "v15 repository intelligence CLI API coverage" in result.stdout
    assert "v15 frontend generated API freshness" in result.stdout
    assert "v15 package contents validation" in result.stdout
    assert "v15 advisory provider evidence" in result.stdout
    assert "v15 advisory dashboard browser evidence" in result.stdout
    assert "v15 advisory accessibility evidence" in result.stdout
    assert "v15 dogfooding evidence" in result.stdout

    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    labels = [stage["label"] for stage in summary["stages"]]
    advisory_labels = [entry["label"] for entry in summary["advisory"]]
    authority = summary["release_authority"]["blocking_evidence"]

    assert summary["gate"] == "v15-release"
    assert summary["status"] == "dry_run"
    assert "v14 review-loop maturity profile" in labels
    assert "v15 deterministic eval release report" in labels
    assert "v15 repository intelligence release profile" in labels
    assert "v15 repository intelligence eval smoke" in labels
    assert "v15 repository intelligence runtime coverage" in labels
    assert "v15 repository intelligence CLI API coverage" in labels
    assert "v15 repository intelligence frontend tests" in labels
    assert "v15 frontend generated API freshness" in labels
    assert "v15 package contents validation" in labels
    assert "v15 release docs" in labels
    assert "v15 eval coverage audit" in labels
    assert summary["blocking"] == summary["stages"]
    assert advisory_labels[-4:] == [
        "v15 advisory provider evidence",
        "v15 advisory dashboard browser evidence",
        "v15 advisory accessibility evidence",
        "v15 dogfooding evidence",
    ]
    assert summary["advisory"][-4]["status"] == "planned"
    assert summary["advisory"][-3]["status"] == "recorded"
    assert summary["advisory"][-2]["required_for_release"] is False
    assert summary["advisory"][-1]["status"] == "pending"
    assert summary["artifacts"]["v15_task_graph"] == "docs/tasks-v15.md"
    assert summary["artifacts"]["v15_release_gate"] == "docs/v15-release-gate.md"
    assert summary["artifacts"]["v15_repository_intelligence_evidence"] == (
        "docs/v15-repository-intelligence-evidence.md"
    )
    assert "inherited v14 deterministic release stages" in authority
    assert "v15 repository intelligence eval smoke" in authority
    assert "v15 package contents validation" in authority


def test_v15_gate_stage_plan_adds_repository_intelligence_checks(
    tmp_path: Path,
) -> None:
    stages = v15_gate.build_gate_stages(tmp_path / "evidence")
    labels = [stage.label for stage in stages]

    assert labels[-13:] == [
        "v15 deterministic eval release report",
        "v15 repository intelligence release profile",
        "v15 repository intelligence eval smoke",
        "v15 repository intelligence runtime coverage",
        "v15 repository intelligence CLI API coverage",
        "v15 repository intelligence frontend tests",
        "v15 frontend generated API freshness",
        "v15 frontend lint",
        "v15 frontend typecheck",
        "v15 frontend build",
        "v15 package contents validation",
        "v15 release docs",
        "v15 eval coverage audit",
    ]
    assert any(
        all(
            case_id in stage.command
            for case_id in v15_gate.V15_REPOSITORY_INTELLIGENCE_CASES
        )
        for stage in stages
    )
    assert any(
        "tests/unit/test_repository_index.py" in stage.command
        and "tests/unit/test_eval_recommendations.py" in stage.command
        for stage in stages
    )
    assert any(
        "tests/integration/test_cli_repository_commands.py" in stage.command
        and "tests/integration/test_web_repository_index_routes.py" in stage.command
        for stage in stages
    )
    assert any(
        "knowledge-autonomy-console.test.tsx" in stage.command
        and "generated-api-types.test.ts" in stage.command
        for stage in stages
    )
