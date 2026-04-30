"""Integration tests for artifact retention and pruning."""

import json
import os
import time
from pathlib import Path

import pytest

from glassbox.cli import main
from glassbox.core import BackgroundJobFailed
from glassbox.core import BackgroundJobFailureKind
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_background_job_id
from glassbox.core import new_session_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.store.artifact_retention import inspect_artifact_state
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import append_event
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database


def test_artifact_prune_dry_run_reports_without_deleting_protected_or_stale_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, protected_path, orphan_path, stale_eval_path, curated_bundle_path = (
        _seed_artifact_gc_workspace(tmp_path)
    )

    exit_code = main(
        [
            "artifacts",
            "prune",
            "--dry-run",
            "--max-age-days",
            "7",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        "Artifact prune: 1 protected, 1 orphaned, 2 reclaimable, 2 would be deleted"
    ) in captured.out
    assert "Next actions:" in captured.out
    assert "glassbox artifacts prune --dry-run --cwd ." in captured.out
    assert (
        f"Would delete: {orphan_path.relative_to(tmp_path).as_posix()}" in captured.out
    )
    assert (
        f"Would delete: {stale_eval_path.relative_to(tmp_path).as_posix()}"
        in captured.out
    )
    assert protected_path.exists()
    assert orphan_path.exists()
    assert stale_eval_path.exists()
    assert curated_bundle_path.exists()


def test_artifact_inspect_reports_without_deleting_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, protected_path, orphan_path, stale_eval_path, curated_bundle_path = (
        _seed_artifact_gc_workspace(tmp_path)
    )

    exit_code = main(
        [
            "artifacts",
            "inspect",
            "--max-age-days",
            "7",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        "Artifact inspect: 1 protected, 1 event-referenced, 1 orphaned, 2 reclaimable"
    ) in captured.out
    assert "Artifact storage: 3 managed file(s)" in captured.out
    assert "Retention classes: event_referenced_artifact=1" in captured.out
    assert "orphan_session_artifact=1" in captured.out
    assert "stale_eval_artifact=1" in captured.out
    assert "Oldest managed artifact age:" in captured.out
    assert (
        f"Protected event-referenced: {protected_path.relative_to(tmp_path).as_posix()}"
        in captured.out
    )
    assert "kind tool_log" in captured.out
    assert (
        f"Orphaned reclaimable: {orphan_path.relative_to(tmp_path).as_posix()}"
        in captured.out
    )
    assert (
        f"Reclaimable: {stale_eval_path.relative_to(tmp_path).as_posix()}"
        in captured.out
    )
    assert "Next actions:" in captured.out
    assert protected_path.exists()
    assert orphan_path.exists()
    assert stale_eval_path.exists()
    assert curated_bundle_path.exists()


def test_artifact_inspect_json_reports_hashes_and_missing_references(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, protected_path, orphan_path, stale_eval_path, _curated_bundle_path = (
        _seed_artifact_gc_workspace(tmp_path)
    )
    protected_path.unlink()

    exit_code = main(
        [
            "artifacts",
            "inspect",
            "--json",
            "--max-age-days",
            "7",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["protected_count"] == 0
    assert payload["missing_reference_count"] == 1
    assert payload["candidate_count"] == 2
    assert payload["event_referenced_count"] == 0
    assert payload["orphaned_count"] == 1
    assert payload["reclaimable_count"] == 2
    assert payload["reported_count"] == 2
    assert payload["glassbox_size_bytes"] > 0
    assert payload["oldest_age_days"] >= 39
    assert payload["category_counts"] == {
        "orphan_session_artifact": 1,
        "stale_eval_artifact": 1,
    }
    assert payload["retention_state_counts"] == {
        "missing_reference": 1,
        "orphaned": 1,
        "reclaimable": 1,
    }
    assert payload["protected"] == []
    assert payload["next_actions"][0].startswith(
        "inspect missing event-referenced artifacts"
    )
    assert {candidate["path"] for candidate in payload["candidates"]} == {
        orphan_path.relative_to(tmp_path).as_posix(),
        stale_eval_path.relative_to(tmp_path).as_posix(),
    }
    assert {candidate["retention_state"] for candidate in payload["candidates"]} == {
        "orphaned",
        "reclaimable",
    }
    assert all(candidate["content_sha256"] for candidate in payload["candidates"])
    assert all(candidate["modified_at"] for candidate in payload["candidates"])
    assert all(candidate["age_days"] >= 0 for candidate in payload["candidates"])


def test_artifact_prune_deletes_only_unreferenced_and_managed_stale_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, protected_path, orphan_path, stale_eval_path, curated_bundle_path = (
        _seed_artifact_gc_workspace(tmp_path)
    )

    exit_code = main(
        [
            "artifacts",
            "prune",
            "--max-age-days",
            "7",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        "Artifact prune: 1 protected, 1 orphaned, 2 reclaimable, 2 deleted"
        in captured.out
    )
    assert protected_path.exists()
    assert not orphan_path.exists()
    assert not stale_eval_path.exists()
    assert curated_bundle_path.exists()


def test_artifact_prune_json_reports_hashes_and_missing_references(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, protected_path, orphan_path, stale_eval_path, _curated_bundle_path = (
        _seed_artifact_gc_workspace(tmp_path)
    )
    protected_path.unlink()

    exit_code = main(
        [
            "artifacts",
            "prune",
            "--dry-run",
            "--json",
            "--max-age-days",
            "7",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["protected_count"] == 0
    assert payload["missing_reference_count"] == 1
    assert payload["candidate_count"] == 2
    assert payload["orphaned_count"] == 1
    assert payload["reclaimable_count"] == 2
    assert {candidate["path"] for candidate in payload["candidates"]} == {
        orphan_path.relative_to(tmp_path).as_posix(),
        stale_eval_path.relative_to(tmp_path).as_posix(),
    }
    assert all(candidate["content_sha256"] for candidate in payload["candidates"])
    assert payload["next_actions"][1].startswith(
        "run `glassbox artifacts prune --dry-run --cwd .`"
    )


def test_artifact_inspect_reports_storage_pressure_thresholds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, *_paths = _seed_artifact_gc_workspace(tmp_path)

    exit_code = main(
        [
            "artifacts",
            "inspect",
            "--warning-threshold-mb",
            "1",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["storage_warning"] is None

    pressure_file = tmp_path / ".glassbox" / "large-pressure.bin"
    pressure_file.write_bytes(b"x" * 1024 * 1024)

    exit_code = main(
        [
            "artifacts",
            "inspect",
            "--warning-threshold-mb",
            "0",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["storage_warning"] is None

    exit_code = main(
        [
            "artifacts",
            "inspect",
            "--warning-threshold-mb",
            "1",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Artifact storage:" in output
    assert "Storage warning: .glassbox contains" in output
    assert "Next actions:" in output


def test_background_job_failure_artifacts_are_protected(tmp_path: Path) -> None:
    session_id = new_session_id()
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        append_event(
            connection,
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            ),
        )
        artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
        failure_artifact = artifact_repository.write_text_artifact(
            session_id,
            "traceback\n",
            suffix="background-job-failure.txt",
        )
        append_event(
            connection,
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BackgroundJobFailed(
                    job_id=new_background_job_id(),
                    failure_kind=BackgroundJobFailureKind.TOOL_ERROR,
                    message="tool exited",
                    retryable=True,
                    attempt=1,
                    artifact_id=failure_artifact.artifact_id,
                    artifact_path=failure_artifact.relative_path.as_posix(),
                ),
            ),
        )
        report = inspect_artifact_state(tmp_path, SQLiteSessionRepository(connection))
    finally:
        connection.close()

    assert [entry.relative_path for entry in report.protected] == [
        failure_artifact.relative_path
    ]
    assert report.candidates == []


def _seed_artifact_gc_workspace(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    session_id = new_session_id()
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    try:
        append_event(
            connection,
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            ),
        )
        artifact_repository = FilesystemArtifactRepository(connection, tmp_path)
        protected_artifact, _event = artifact_repository.record_text_artifact(
            session_id,
            new_turn_id(),
            new_tool_call_id(),
            "tool_log",
            "protected\n",
            suffix="log",
        )
    finally:
        connection.close()

    orphan_path = (
        tmp_path
        / ".glassbox"
        / "sessions"
        / str(session_id)
        / "artifacts"
        / "orphan.log"
    )
    orphan_path.write_text("orphan\n", encoding="utf-8")

    stale_eval_path = tmp_path / ".glassbox" / "evals" / "old" / "summary.json"
    stale_eval_path.parent.mkdir(parents=True, exist_ok=True)
    stale_eval_path.write_text('{"stale": true}\n', encoding="utf-8")

    curated_bundle_path = tmp_path / "evals" / "bundles" / "curated.json"
    curated_bundle_path.parent.mkdir(parents=True, exist_ok=True)
    curated_bundle_path.write_text('{"curated": true}\n', encoding="utf-8")

    stale_timestamp = time.time() - 40 * 24 * 60 * 60
    os.utime(stale_eval_path, (stale_timestamp, stale_timestamp))
    os.utime(curated_bundle_path, (stale_timestamp, stale_timestamp))

    return (
        db_path,
        protected_artifact.absolute_path,
        orphan_path,
        stale_eval_path,
        curated_bundle_path,
    )
