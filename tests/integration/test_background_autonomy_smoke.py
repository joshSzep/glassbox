"""Integration coverage for the v8 background autonomy release smoke."""

import json
from pathlib import Path

from scripts.background_autonomy_smoke import main


def test_background_autonomy_smoke_writes_release_evidence(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    evidence_dir = tmp_path / "evidence" / "background-jobs"

    exit_code = main(
        [
            "--workspace",
            str(workspace),
            "--evidence-dir",
            str(evidence_dir),
            "--json",
        ]
    )

    summary_path = evidence_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    scenarios = {scenario["name"]: scenario for scenario in summary["scenarios"]}

    assert exit_code == 0
    assert summary["status"] == "passed"
    assert summary["release_gate_recommendation"]["blocking"] is True
    assert (
        summary["release_gate_recommendation"]["provider_credentials_required"] is False
    )
    assert set(scenarios) == {
        "read_only_completion",
        "cancellation_acknowledgement",
        "failure_retry_and_abandon",
        "stale_owner_cleanup",
        "task_continuation_budget_pause",
        "retained_projection_snapshot",
    }
    assert scenarios["failure_retry_and_abandon"]["failure_artifact_path"]
    assert scenarios["stale_owner_cleanup"]["recovered_stale_count"] == 1
    assert (workspace / ".glassbox" / "background-autonomy-smoke.sqlite3").is_file()


def test_background_autonomy_smoke_dry_run_lists_planned_scenarios(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "dry-run" / "background-jobs"

    exit_code = main(["--evidence-dir", str(evidence_dir), "--dry-run"])

    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert summary["status"] == "dry_run"
    assert [scenario["status"] for scenario in summary["scenarios"]] == [
        "planned",
        "planned",
        "planned",
        "planned",
        "planned",
    ]
