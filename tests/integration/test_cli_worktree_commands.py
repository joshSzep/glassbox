"""CLI coverage for temporary local worktree isolation commands."""

import json
import subprocess
from pathlib import Path

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import WorktreeCleanupRecorded
from glassbox.core import WorktreeCreated
from glassbox.core import WorktreeStatusRecorded
from glassbox.core import new_session_id
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_worktree_create_status_cleanup_records_custody_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    _init_git_repo(tmp_path)
    _seed_session(db_path, tmp_path, session_id)

    create_exit = main(
        [
            "worktree",
            "create",
            "--session",
            str(session_id),
            "--source",
            "manual",
            "--source-id",
            "candidate-a",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    created_output = capsys.readouterr()
    assert create_exit == 0, created_output.err
    created = json.loads(created_output.out)
    worktree = created["worktree"]
    worktree_id = worktree["worktree_id"]
    worktree_path = Path(worktree["path"])
    created_path_exists = worktree_path.exists()

    list_exit = main(
        [
            "worktree",
            "list",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    listed = json.loads(capsys.readouterr().out)

    status_exit = main(
        [
            "worktree",
            "status",
            worktree_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    status = json.loads(capsys.readouterr().out)

    (worktree_path / "app.py").write_text("print('dirty worktree')\n", encoding="utf-8")
    blocked_cleanup_exit = main(
        [
            "worktree",
            "cleanup",
            worktree_id,
            "--confirm",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    blocked_cleanup = json.loads(capsys.readouterr().out)
    blocked_path_exists = worktree_path.exists()

    forced_cleanup_exit = main(
        [
            "worktree",
            "cleanup",
            worktree_id,
            "--confirm",
            "--discard-user-changes",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    forced_cleanup = json.loads(capsys.readouterr().out)
    events = _read_events(db_path, session_id)

    assert created["event"]["payload"]["event_type"] == "WorktreeCreated"
    assert created["safe_copy"].startswith("Glassbox created a local worktree only")
    assert worktree["session_id"] == str(session_id)
    assert worktree["source_kind"] == "manual"
    assert created_path_exists is True
    assert list_exit == 0
    assert listed[0]["worktree_id"] == worktree_id
    assert status_exit == 0
    assert status["event"]["payload"]["event_type"] == "WorktreeStatusRecorded"
    assert status["status"]["dirty"] is False
    assert blocked_cleanup_exit == 1
    assert blocked_cleanup["blocked"] is True
    assert blocked_cleanup["event"]["payload"]["state"] == "cleanup_blocked"
    assert blocked_path_exists is True
    assert forced_cleanup_exit == 0
    assert forced_cleanup["removed"] is True
    assert forced_cleanup["event"]["payload"]["state"] == "cleaned"
    assert not worktree_path.exists()
    assert any(isinstance(event.payload, WorktreeCreated) for event in events)
    assert any(isinstance(event.payload, WorktreeStatusRecorded) for event in events)
    assert any(isinstance(event.payload, WorktreeCleanupRecorded) for event in events)


def test_worktree_create_rejects_paths_outside_safe_root(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    _init_git_repo(tmp_path)
    _seed_session(db_path, tmp_path, session_id)

    exit_code = main(
        [
            "worktree",
            "create",
            "--session",
            str(session_id),
            "--path",
            str(tmp_path / "outside-worktrees"),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "safe local root" in captured.err


def _init_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "app.py").write_text("print('base')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


def _seed_session(db_path: Path, tmp_path: Path, session_id) -> None:
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            )
        )
    finally:
        connection.close()


def _read_events(db_path: Path, session_id) -> list[EventEnvelope]:
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        return repository.read_session_events(session_id)
    finally:
        connection.close()
