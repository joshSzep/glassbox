"""CLI coverage for changeset inspection commands."""

import json
import subprocess
from pathlib import Path

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import TaskCreated
from glassbox.core import TaskPlanStatus
from glassbox.core import TaskStatusChanged
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_changeset_create_list_show_refresh_and_archive(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    _init_git_repo(tmp_path)
    _seed_task(db_path, tmp_path, session_id, task_id)

    create_exit = main(
        [
            "changeset",
            "create",
            "--from",
            "task",
            "--task",
            str(task_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    created = json.loads(capsys.readouterr().out)
    changeset_id = created["changeset_id"]

    list_exit = main(
        [
            "changeset",
            "list",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    list_output = capsys.readouterr().out

    show_exit = main(
        [
            "changeset",
            "show",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    detail = json.loads(capsys.readouterr().out)

    (tmp_path / "app.py").write_text("print('changed')\n", encoding="utf-8")

    refresh_exit = main(
        [
            "changeset",
            "refresh",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    refresh_output = capsys.readouterr().out
    (tmp_path / "app.py").write_text("print('changed again')\n", encoding="utf-8")

    stale_show_exit = main(
        [
            "changeset",
            "show",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    stale_detail = json.loads(capsys.readouterr().out)

    archive_exit = main(
        [
            "changeset",
            "archive",
            changeset_id,
            "--reason",
            "superseded",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    archived = json.loads(capsys.readouterr().out)

    assert create_exit == 0
    assert created["session_id"] == str(session_id)
    assert list_exit == 0
    assert "Changesets: 1" in list_output
    assert show_exit == 0
    assert detail["changeset"]["task_id"] == str(task_id)
    assert detail["sources"][0]["source_kind"] == "task"
    assert "glassbox changeset refresh" in detail["safe_next_actions"][1]
    assert refresh_exit == 0
    assert "Refreshed change inventory" in refresh_output
    assert stale_show_exit == 0
    assert stale_detail["inventory"]["freshness"] == "stale"
    assert stale_detail["inventory_status"]["stale"] is True
    assert "source digest changed" in stale_detail["inventory_status"]["reason"]
    assert archive_exit == 0
    assert archived["payload"]["event_type"] == "ChangesetArchived"


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


def _seed_task(db_path: Path, tmp_path: Path, session_id, task_id) -> None:
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd=str(tmp_path),
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskCreated(
                        task_id=task_id,
                        title="Add changeset command",
                        goal="Expose changeset surfaces",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskStatusChanged(
                        task_id=task_id,
                        status=TaskPlanStatus.COMPLETED,
                    ),
                ),
            ]
        )
    finally:
        connection.close()
