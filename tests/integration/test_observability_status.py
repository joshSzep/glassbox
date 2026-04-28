"""Integration coverage for workspace observability summaries."""

import json
from pathlib import Path

import pytest

from glassbox.cli import main
from tests.integration.fault_test_support import append_representative_completed_session
from tests.integration.fault_test_support import open_initialized_database


def test_observability_status_json_reports_health_lag_and_verification(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    connection = open_initialized_database(tmp_path)
    db_path = tmp_path / "glassbox.sqlite3"
    try:
        ids = append_representative_completed_session(connection, tmp_path)
        with connection:
            connection.execute(
                "delete from session_state where session_id = ?",
                (str(ids.session_id),),
            )
        _write_eval_summary(tmp_path, exit_code=13, failed_case_count=1)
    finally:
        connection.close()

    exit_code = main(
        [
            "observability",
            "status",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["runtime"]["state"] == "not_running"
    assert payload["runtime"]["event_transport"]["state"] == "healthy"
    assert payload["runtime"]["event_transport"]["dropped_events"] == 0
    assert payload["runtime"]["event_transport"]["queue_capacity"] == 64
    assert payload["runtime"]["event_transport"]["queue_pressure"] == 0.0
    assert payload["runtime"]["event_transport"]["last_published_sequence"] is None
    assert payload["runtime"]["event_transport"]["reconnect_mode"].startswith(
        "resume with"
    )
    assert (
        "last observed sequence"
        in payload["runtime"]["event_transport"]["reconnect_hint"]
    )
    assert payload["projections"]["session_count"] == 1
    assert payload["projections"]["degraded_count"] == 1
    assert payload["projections"]["max_lag"] > 0
    assert str(ids.session_id) in payload["projections"]["degraded_sessions"]
    assert payload["verification"]["latest_suite_status"] == "failed"
    assert payload["verification"]["latest_exit_code"] == 13
    assert payload["verification"]["latest_failed_case_count"] == 1
    assert "glassbox projection rebuild --all" in payload["next_actions"]


def test_observability_status_text_reports_next_actions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_initialized_database(tmp_path)
    connection.close()

    exit_code = main(
        [
            "observability",
            "status",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Runtime: not_running" in captured.out
    assert "Event transport: healthy" in captured.out
    assert "queue peak 0/64" in captured.out
    assert "Reconnect hint:" in captured.out
    assert "Projections:" in captured.out
    assert "Verification: not run" in captured.out
    assert "glassbox eval run" in captured.out


def _write_eval_summary(
    workspace_root: Path,
    *,
    exit_code: int,
    failed_case_count: int,
) -> None:
    output_dir = workspace_root / ".glassbox" / "evals" / "20260425T120000Z"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "profile_id": "push-smoke",
                "selected_case_count": 2,
                "passed_case_count": 1,
                "failed_case_count": failed_case_count,
                "exit_code": exit_code,
            }
        ),
        encoding="utf-8",
    )
