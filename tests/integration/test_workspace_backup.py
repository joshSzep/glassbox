"""Integration tests for workspace backup and restore commands."""

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from glassbox.cli import main
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import open_database
from tests.integration.cli_test_support import _read_session_events
from tests.integration.cli_test_support import _run_baseline_session


def test_backup_create_writes_manifest_database_and_referenced_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    curated_bundle = tmp_path / "evals" / "bundles" / "curated.json"
    curated_bundle.parent.mkdir(parents=True, exist_ok=True)
    curated_bundle.write_text('{"curated": true}\n', encoding="utf-8")
    backup_path = tmp_path / "backups" / "state.zip"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "backup",
            "create",
            str(backup_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    manifest = _read_backup_manifest(backup_path)
    archive_names = set(_archive_names(backup_path))
    replay_artifact_paths = _replay_artifact_paths(db_path, session_id)

    assert exit_code == 0
    assert "Created workspace backup:" in captured.out
    assert backup_path.is_file()
    assert manifest["format"] == "glassbox.workspace-backup"
    assert manifest["session_count"] == 1
    assert manifest["artifact_count"] == len(replay_artifact_paths)
    assert "glassbox-backup.json" in archive_names
    assert ".glassbox/glassbox.sqlite3" in archive_names
    assert {path.as_posix() for path in replay_artifact_paths}.issubset(archive_names)
    assert "evals/bundles/curated.json" not in archive_names
    assert all(file_payload["content_sha256"] for file_payload in manifest["files"])


def test_backup_restore_into_clean_workspace_preserves_discovery_and_replay(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    backup_path = tmp_path / "state.zip"
    _ = capsys.readouterr()
    assert (
        main(
            [
                "backup",
                "create",
                str(backup_path),
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        == 0
    )
    _ = capsys.readouterr()

    restored_root = tmp_path / "restored-workspace"
    restored_db_path = restored_root / ".glassbox" / "glassbox.sqlite3"
    restore_exit_code = main(
        [
            "backup",
            "restore",
            str(backup_path),
            "--cwd",
            str(restored_root),
            "--db-path",
            str(restored_db_path),
        ]
    )
    restore_capture = capsys.readouterr()

    connection = open_database(restored_db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        restored_sessions = repository.list_sessions()
    finally:
        connection.close()
    replay_exit_code = main(
        [
            "replay",
            str(session_id),
            "--cwd",
            str(restored_root),
            "--db-path",
            str(restored_db_path),
        ]
    )
    replay_capture = capsys.readouterr()

    assert restore_exit_code == 0
    assert "Restored workspace backup:" in restore_capture.out
    assert [session.session_id for session in restored_sessions] == [session_id]
    assert replay_exit_code == 0
    assert "Outcome: exact match" in replay_capture.out


def test_backup_restore_refuses_existing_files_without_force(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, _session_id = _run_baseline_session(tmp_path, prompt="Inspect")
    backup_path = tmp_path / "state.zip"
    _ = capsys.readouterr()
    assert (
        main(
            [
                "backup",
                "create",
                str(backup_path),
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        == 0
    )
    _ = capsys.readouterr()

    exit_code = main(
        [
            "backup",
            "restore",
            str(backup_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "restore target already exists" in captured.err


def test_backup_create_fails_when_referenced_artifact_is_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(
        tmp_path,
        prompt="Inspect the repository",
    )
    missing_artifact = _replay_artifact_paths(db_path, session_id)[0]
    (tmp_path / missing_artifact).unlink()
    _ = capsys.readouterr()

    exit_code = main(
        [
            "backup",
            "create",
            str(tmp_path / "state.zip"),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert (
        f"referenced artifact is missing: {missing_artifact.as_posix()}" in captured.err
    )


def _read_backup_manifest(backup_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(backup_path) as archive:
        return json.loads(archive.read("glassbox-backup.json").decode("utf-8"))


def _archive_names(backup_path: Path) -> list[str]:
    with zipfile.ZipFile(backup_path) as archive:
        return archive.namelist()


def _replay_artifact_paths(db_path: Path, session_id) -> list[Path]:
    return [
        Path(event.payload.path)
        for event in _read_session_events(db_path, session_id)
        if isinstance(event.payload, ReplayArtifactRecorded)
        and event.payload.path is not None
    ]
