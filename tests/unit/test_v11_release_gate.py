"""Tests for the v11 release gate provider-evidence scaffold."""

import json
import subprocess
import sys
from pathlib import Path

from scripts import validate_v11_release_gate as v11_gate

from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v11_release_gate.py"


def test_v11_release_gate_dry_run_records_provider_evidence_plan(
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
    assert "v11 advisory provider evidence" in result.stdout
    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))

    assert summary["gate"] == "v11-release"
    assert summary["status"] == "dry_run"
    assert summary["provider_evidence"]["blocking"] is False
    assert summary["provider_evidence"]["opt_in"] is True
    assert summary["advisory"][0]["status"] == "planned"
    assert summary["advisory"][0]["freshness_status"] == "planned"
    assert summary["advisory"][0]["blocking"] is False
    assert summary["advisory"][0]["summary_path"] == str(
        evidence_dir / "provider-canary" / "provider-canary-summary.json"
    )


def test_v11_provider_evidence_skip_is_structured(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    summary = v11_gate._new_evidence_summary(
        evidence_dir,
        include_provider_canaries=False,
        dry_run=True,
    )

    v11_gate._record_v11_provider_evidence(
        summary,
        evidence_dir,
        include=False,
        dry_run=True,
    )

    assert summary["advisory"] == [
        {
            "label": "v11 advisory provider evidence",
            "status": "skipped",
            "reason": "pass --include-provider-canaries to collect advisory evidence",
            "blocking": False,
            "freshness_status": "not_collected",
            "latest_status": "not_collected",
            "missing_scenarios": [],
            "evidence_dir": str(evidence_dir / "provider-canary"),
        }
    ]


def test_v11_provider_evidence_records_freshness_for_skipped_run(
    tmp_path: Path,
    monkeypatch,
) -> None:
    evidence_dir = tmp_path / "evidence"
    summary = v11_gate._new_evidence_summary(
        evidence_dir,
        include_provider_canaries=True,
        dry_run=False,
    )

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0)

    def fake_evidence(*args, **kwargs):
        return ProviderCanaryEvidenceSummary(
            summary_count=1,
            latest_summary_path=str(
                evidence_dir / "provider-canary" / "provider-canary-summary.json"
            ),
            latest_status="skipped",
            freshness_status="credentialless",
            provider="openai",
            model_name="openai:gpt-5.4",
            scenario_count=2,
            matrix_entry_count=2,
            missing_scenarios=["tool-call"],
            skipped_count=2,
            next_actions=["set OPENAI_API_KEY before rerunning provider canaries"],
        )

    monkeypatch.setattr(v11_gate.subprocess, "run", fake_run)
    monkeypatch.setattr(v11_gate, "load_provider_canary_evidence", fake_evidence)

    v11_gate._record_v11_provider_evidence(
        summary,
        evidence_dir,
        include=True,
        dry_run=False,
    )

    [advisory] = summary["advisory"]
    assert advisory["status"] == "passed"
    assert advisory["blocking"] is False
    assert advisory["latest_status"] == "skipped"
    assert advisory["freshness_status"] == "credentialless"
    assert advisory["missing_scenarios"] == ["tool-call"]
    assert advisory["provider"] == "openai"
    assert advisory["matrix_entry_count"] == 2
    assert "OPENAI_API_KEY" in advisory["next_actions"][0]
