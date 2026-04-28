"""Tests for the v7 release gate script."""

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_v7_release_gate import V7_ADDITIONAL_STAGES

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v7_release_gate.py"
GATE_DOC = REPO_ROOT / "docs" / "v7-release-gate.md"


def test_v7_release_gate_script_runs_expected_checks() -> None:
    script = GATE_SCRIPT.read_text(encoding="utf-8")

    for fragment in [
        "build_v6_gate_stages",
        "v7 deterministic eval release profile",
        "v7 workflow advisory eval profile",
        "v7 scale performance budgets",
        "v7 provider diagnostics onboarding",
        "v7 dashboard evidence cue tests",
        "v7 release evidence docs",
        "advisory provider canaries",
        "provider canary run",
        "_run_installed_wheel_smoke",
        "v7-gate",
        "summary.json",
        "--dry-run",
    ]:
        assert fragment in script


def test_v7_release_gate_dry_run_lists_stages(tmp_path: Path) -> None:
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
    assert "V7 release gate dry run" in result.stdout
    assert "python format" in result.stdout
    assert "v7 deterministic eval release profile" in result.stdout
    assert "v7 dashboard evidence cue tests" in result.stdout
    assert "advisory provider canaries: skipped by default" in result.stdout
    assert "installed wheel smoke" in result.stdout


def test_v7_release_gate_dry_run_writes_summary(tmp_path: Path) -> None:
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
    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))

    assert summary["schema_version"] == 1
    assert summary["gate"] == "v7-release"
    assert summary["status"] == "dry_run"
    assert summary["options"]["dry_run"] is True
    assert (
        summary["artifacts"]["manual_evidence_hint"] == "docs/manual-qa-evidence-v7.md"
    )
    assert summary["stages"]
    assert summary["stages"][0]["status"] == "planned"
    assert any(stage["label"] == "installed wheel smoke" for stage in summary["stages"])
    assert summary["next_actions"] == ["rerun without --dry-run to execute the gate"]


def test_v7_release_gate_doc_maps_script_stages() -> None:
    doc = GATE_DOC.read_text(encoding="utf-8")

    for stage in V7_ADDITIONAL_STAGES:
        assert f"`{stage.label}`" in doc

    for phrase in [
        "Provider-canary evidence remains advisory",
        "manual-qa-evidence-v7.md",
        "installed-wheel smoke",
        "summary.json",
    ]:
        assert phrase in doc
