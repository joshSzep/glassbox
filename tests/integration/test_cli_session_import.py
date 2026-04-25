"""Integration tests for portable session handoff import."""

import json
from pathlib import Path
from uuid import UUID

import pytest

from glassbox.cli import main
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import open_database
from tests.integration.cli_test_support import _completed_turn_ids
from tests.integration.cli_test_support import _run_baseline_session


def test_cli_session_import_rehydrates_export_for_inspection_in_clean_workspace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_root = tmp_path / "source"
    import_root = tmp_path / "imported"
    source_root.mkdir()
    import_root.mkdir()
    package_path, source_session_id = _export_session_package(
        source_root,
        tmp_path / "handoff.json",
        capsys,
        prompt="Prepare a portable handoff",
    )
    import_db_path = import_root / ".glassbox" / "glassbox.sqlite3"

    exit_code = main(
        [
            "session",
            "import",
            str(package_path),
            "--json",
            "--cwd",
            str(import_root),
            "--db-path",
            str(import_db_path),
        ]
    )
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    imported_session_id = UUID(result["imported_session_id"])

    assert exit_code == 0
    assert result["source_session_id"] == str(source_session_id)
    assert result["import_mode"] == "inspect"
    assert result["resumable"] is False
    assert result["imported_status"] == "completed"
    assert result["transcript_message_count"] == 2

    connection = open_database(import_db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        session = repository.get_session(imported_session_id)
        transcript = repository.list_transcript_messages(imported_session_id)
        state = repository.get_session_state(imported_session_id)
    finally:
        connection.close()

    assert session is not None
    assert session.status == "completed"
    assert session.cwd == import_root.resolve()
    assert state is not None
    assert state.status == "completed"
    assert [message.role for message in transcript] == ["user", "assistant"]
    assert transcript[0].parts[0].text == "Prepare a portable handoff"

    status_exit_code = main(
        [
            "session",
            "status",
            str(imported_session_id),
            "--cwd",
            str(import_root),
            "--db-path",
            str(import_db_path),
        ]
    )
    status_capture = capsys.readouterr()

    assert status_exit_code == 0
    assert "Status: completed" in status_capture.out
    assert "Transcript messages: 2" in status_capture.out
    assert "Imported for inspection" in status_capture.out


def test_cli_session_import_preserves_branch_lineage_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_root = tmp_path / "source"
    import_root = tmp_path / "imported"
    source_root.mkdir()
    import_root.mkdir()
    db_path, parent_session_id = _run_baseline_session(
        source_root,
        prompt="Create branchable handoff",
    )
    fork_turn_id = _completed_turn_ids(db_path, parent_session_id)[0]
    _ = capsys.readouterr()

    fork_exit_code = main(
        [
            "session",
            "fork",
            str(parent_session_id),
            "--turn",
            str(fork_turn_id),
            "--branch-label",
            "handoff-import",
            "--cwd",
            str(source_root),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()
    child_session_id = _single_child_session_id(db_path, parent_session_id)
    package_path = tmp_path / "branched-handoff.json"
    export_exit_code = main(
        [
            "session",
            "export",
            str(child_session_id),
            str(package_path),
            "--cwd",
            str(source_root),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()
    import_db_path = import_root / ".glassbox" / "glassbox.sqlite3"

    import_exit_code = main(
        [
            "session",
            "import",
            str(package_path),
            "--json",
            "--cwd",
            str(import_root),
            "--db-path",
            str(import_db_path),
        ]
    )
    result = json.loads(capsys.readouterr().out)
    imported_session_id = UUID(result["imported_session_id"])

    connection = open_database(import_db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        imported_session = repository.get_session(imported_session_id)
    finally:
        connection.close()

    assert fork_exit_code == 0
    assert export_exit_code == 0
    assert import_exit_code == 0
    assert imported_session is not None
    assert imported_session.parent_session_id == parent_session_id
    assert imported_session.forked_from_turn_id == fork_turn_id
    assert imported_session.branch_label == "handoff-import"


def test_cli_session_import_rejects_resumable_mode(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_root = tmp_path / "source"
    import_root = tmp_path / "imported"
    source_root.mkdir()
    import_root.mkdir()
    package_path, _source_session_id = _export_session_package(
        source_root,
        tmp_path / "handoff.json",
        capsys,
    )

    exit_code = main(
        [
            "session",
            "import",
            str(package_path),
            "--mode",
            "resumable",
            "--cwd",
            str(import_root),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "resumable session import is not supported" in captured.err


def test_cli_session_import_rejects_unsupported_package_version(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_root = tmp_path / "source"
    import_root = tmp_path / "imported"
    source_root.mkdir()
    import_root.mkdir()
    package_path, _source_session_id = _export_session_package(
        source_root,
        tmp_path / "handoff.json",
        capsys,
    )
    payload = json.loads(package_path.read_text(encoding="utf-8"))
    payload["export_version"] = 999
    package_path.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = main(
        [
            "session",
            "import",
            str(package_path),
            "--cwd",
            str(import_root),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "unsupported session export version: 999" in captured.err


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("not json", "invalid session export package"),
        (
            '{"export_kind":"glassbox_session_export","export_version":1,'
            '"handoff":{"note":"OPENAI_API_KEY=secret-value"}}',
            "unredacted secret material",
        ),
    ],
)
def test_cli_session_import_rejects_invalid_packages(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    payload: str,
    message: str,
) -> None:
    package_path = tmp_path / "bad-package.json"
    package_path.write_text(payload + "\n", encoding="utf-8")

    exit_code = main(
        [
            "session",
            "import",
            str(package_path),
            "--cwd",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert message in captured.err


def _export_session_package(
    source_root: Path,
    package_path: Path,
    capsys: pytest.CaptureFixture[str],
    *,
    prompt: str = "Prepare a portable handoff",
) -> tuple[Path, UUID]:
    db_path, session_id = _run_baseline_session(source_root, prompt=prompt)
    _ = capsys.readouterr()
    exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(package_path),
            "--cwd",
            str(source_root),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert package_path.exists()
    return package_path, session_id


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
