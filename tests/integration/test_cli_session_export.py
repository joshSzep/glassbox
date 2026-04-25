"""Integration tests for portable session handoff export."""

import json
from pathlib import Path
from uuid import UUID

import pytest

from glassbox.cli import main
from glassbox.runtime.session_export import SESSION_EXPORT_KIND
from glassbox.runtime.session_export import SESSION_EXPORT_VERSION
from glassbox.runtime.session_export import SessionExportPayload
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import open_database
from tests.integration.cli_test_support import _completed_turn_ids
from tests.integration.cli_test_support import _run_baseline_session
from tests.integration.cli_test_support import _seed_pending_approval


def test_cli_session_export_writes_redacted_live_handoff_package(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = f"Inspect {tmp_path} with OPENAI_API_KEY=sk-secret-session-export"
    db_path, session_id = _run_baseline_session(tmp_path, prompt=prompt)
    output_path = tmp_path / "exports" / "live-session.json"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--exported-by",
            "alice",
            "--expected-custodian",
            "bob",
            "--note",
            f"handoff from {tmp_path}",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    raw_package = output_path.read_text(encoding="utf-8")
    payload = SessionExportPayload.model_validate_json(raw_package)

    assert exit_code == 0
    assert f"Exported session handoff package for {session_id}" in captured.out
    assert payload.export_kind == SESSION_EXPORT_KIND
    assert payload.export_version == SESSION_EXPORT_VERSION
    assert payload.metadata.session_id == session_id
    assert payload.metadata.status == "running"
    assert payload.metadata.workspace.cwd == "<workspace-root>"
    assert payload.handoff.exported_by == "alice"
    assert payload.handoff.expected_custodian == "bob"
    assert payload.handoff.live_actionable is True
    assert payload.handoff.historical_only is False
    assert payload.artifact_references
    assert str(tmp_path) not in raw_package
    assert "sk-secret-session-export" not in raw_package
    assert "OPENAI_API_KEY=<redacted>" in raw_package


def test_cli_session_export_captures_paused_approval_handoff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, approval_id = _seed_pending_approval(tmp_path)
    output_path = tmp_path / "paused-session.json"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--note",
            "approval handoff ANTHROPIC_API_KEY=secret-value",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    command_payload = json.loads(captured.out)
    raw_package = output_path.read_text(encoding="utf-8")
    payload = SessionExportPayload.model_validate_json(raw_package)

    assert exit_code == 0
    assert command_payload == {
        "path": str(output_path.resolve()),
        "session_id": str(session_id),
    }
    assert payload.metadata.status == "awaiting_approval"
    assert payload.handoff.pending_approval_id == str(approval_id)
    assert payload.handoff.next_action_summary == "Resolve pending approval"
    assert payload.pending_approvals[0].approval_id == approval_id
    assert payload.pending_approvals[0].subject == "run shell command"
    assert "secret-value" not in raw_package
    assert "ANTHROPIC_API_KEY=<redacted>" in raw_package


def test_cli_session_export_captures_branched_session_lineage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, parent_session_id = _run_baseline_session(
        tmp_path,
        prompt="Prepare a handoff branch",
    )
    fork_turn_id = _completed_turn_ids(db_path, parent_session_id)[0]
    _ = capsys.readouterr()

    fork_exit_code = main(
        [
            "fork",
            str(parent_session_id),
            "--turn",
            str(fork_turn_id),
            "--branch-label",
            "handoff branch",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()
    child_session_id = _single_child_session_id(db_path, parent_session_id)
    output_path = tmp_path / "branched-session.json"

    export_exit_code = main(
        [
            "session",
            "export",
            str(child_session_id),
            str(output_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    payload = SessionExportPayload.model_validate_json(
        output_path.read_text(encoding="utf-8")
    )

    assert fork_exit_code == 0
    assert export_exit_code == 0
    assert payload.metadata.session_id == child_session_id
    assert payload.lineage.parent_session_id == parent_session_id
    assert payload.lineage.forked_from_turn_id == str(fork_turn_id)
    assert payload.lineage.branch_label == "handoff branch"
    assert payload.lineage.child_sessions == []
    assert payload.transcript
    assert payload.event_count >= len(payload.events)


def _single_child_session_id(db_path: Path, parent_session_id: UUID) -> UUID:
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        child_sessions = [
            session
            for session in repository.list_sessions()
            if session.parent_session_id == parent_session_id
        ]
    finally:
        connection.close()

    assert len(child_sessions) == 1
    return child_sessions[0].session_id
