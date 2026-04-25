"""Integration tests for artifact retention and garbage collection."""

import json
import os
import time
from pathlib import Path

import pytest

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.sqlite import append_event
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database


def test_artifact_gc_dry_run_reports_without_deleting_protected_or_stale_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, protected_path, orphan_path, stale_eval_path, curated_bundle_path = (
        _seed_artifact_gc_workspace(tmp_path)
    )

    exit_code = main(
        [
            "artifacts",
            "gc",
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
    assert "Artifact GC: 1 protected, 2 stale, 2 would be deleted" in captured.out
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


def test_artifact_gc_deletes_only_unreferenced_and_managed_stale_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, protected_path, orphan_path, stale_eval_path, curated_bundle_path = (
        _seed_artifact_gc_workspace(tmp_path)
    )

    exit_code = main(
        [
            "artifacts",
            "gc",
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
    assert "Artifact GC: 1 protected, 2 stale, 2 deleted" in captured.out
    assert protected_path.exists()
    assert not orphan_path.exists()
    assert not stale_eval_path.exists()
    assert curated_bundle_path.exists()


def test_artifact_gc_json_reports_hashes_and_missing_references(
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
            "gc",
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
    assert {candidate["path"] for candidate in payload["candidates"]} == {
        orphan_path.relative_to(tmp_path).as_posix(),
        stale_eval_path.relative_to(tmp_path).as_posix(),
    }
    assert all(candidate["content_sha256"] for candidate in payload["candidates"])


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
