"""Integration tests for CLI replay commands."""

import json
from pathlib import Path

import pytest

from glassbox.cli import main
from glassbox.core.events import EventEnvelope, ReplayArtifactRecorded, SessionCompleted
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import open_database

from .cli_test_support import (
    _first_replay_artifact_path,
    _run_baseline_session,
)


def test_cli_replay_reports_exact_match_without_mutating_source_session(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        before_events = repository.read_session_events(session_id)
        before_paths = [
            event.payload.path
            for event in before_events
            if isinstance(event.payload, ReplayArtifactRecorded)
        ]
        before_state = repository.get_session_state(session_id)
        assert before_state is not None
        before_last_sequence = before_state.last_sequence
    finally:
        connection.close()

    exit_code = main(
        [
            "replay",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        after_events = repository.read_session_events(session_id)
        after_paths = [
            event.payload.path
            for event in after_events
            if isinstance(event.payload, ReplayArtifactRecorded)
        ]
        after_state = repository.get_session_state(session_id)
        assert after_state is not None
        after_last_sequence = after_state.last_sequence
    finally:
        connection.close()

    assert exit_code == 0
    assert f"Replay session {session_id}" in captured.out
    assert "Outcome: exact match" in captured.out
    assert before_last_sequence == after_last_sequence
    assert len(before_events) == len(after_events)
    assert before_paths == after_paths


def test_cli_replay_reports_behavioral_drift_and_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionCompleted(reason="forced complete for replay drift"),
            )
        )
    finally:
        connection.close()

    _ = capsys.readouterr()
    exit_code = main(
        [
            "replay",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 10


def test_cli_replay_reports_manifest_drift_and_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    artifact_path = _first_replay_artifact_path(db_path, session_id)
    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact_payload["prepared_turn"]["user_prompt"] = "Unexpected prompt"
    artifact_path.write_text(json.dumps(artifact_payload, indent=2), encoding="utf-8")

    exit_code = main(
        [
            "replay",
            str(session_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 11
    assert "Outcome: manifest drift" in captured.out
    assert "Summary:" in captured.out
    assert "Triage: prepared turn drifted before model execution" in captured.out
    assert (
        "First change: prepared turn no longer matches recorded manifest"
        in captured.out
    )
    assert "Next inspect: Inspect the recorded prepared turn manifest" in captured.out


def test_cli_replay_missing_bundle_reports_replay_failure_and_next_inspection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_bundle = tmp_path / "missing-bundle.json"

    exit_code = main(
        [
            "replay",
            "--bundle",
            str(missing_bundle),
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 13
    assert "Outcome: replay failure" in captured.out
    assert "Summary: missing replay bundle file" in captured.out
    assert "Next inspect:" in captured.out


def test_cli_replay_json_output_contains_structured_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "replay",
            str(session_id),
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["outcome"] == "exact_match"
    assert payload["source_session_id"] == str(session_id)
    assert payload["exit_code"] == 0
    assert payload["baseline"] == payload["replay"]


def test_cli_replay_export_writes_bundle_and_bundle_replay_succeeds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    bundle_path = tmp_path / "exports" / "baseline.json"
    portable_root = tmp_path / "portable-workspace"
    portable_root.mkdir()
    _ = capsys.readouterr()

    export_exit_code = main(
        [
            "replay-export",
            str(session_id),
            str(bundle_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    export_capture = capsys.readouterr()

    replay_exit_code = main(
        [
            "replay",
            "--bundle",
            str(bundle_path),
            "--cwd",
            str(portable_root),
        ]
    )
    replay_capture = capsys.readouterr()

    assert export_exit_code == 0
    assert bundle_path.exists()
    assert (
        f"Exported replay bundle for session {session_id}: {bundle_path.resolve()}"
        in export_capture.out
    )
    assert replay_exit_code == 0
    assert f"Replay session {session_id}" in replay_capture.out
    assert "Outcome: exact match" in replay_capture.out


def test_cli_replay_requires_exactly_one_session_or_bundle_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    bundle_path = tmp_path / "baseline.json"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "replay",
            str(session_id),
            "--bundle",
            str(bundle_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.strip() == "specify exactly one of session_id or --bundle"
