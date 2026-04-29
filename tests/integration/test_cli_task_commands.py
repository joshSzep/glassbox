"""CLI coverage for read-only task-plan inspection commands."""

import json
from pathlib import Path

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import TaskCreated
from glassbox.core import TaskPlanProposed
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepProposal
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core.types import BackgroundJobKind
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_task_list_show_and_events_commands(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    _seed_task(db_path, tmp_path, session_id, task_id, step_id)

    list_exit = main(
        [
            "task",
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
            "task",
            "show",
            str(task_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    show_output = capsys.readouterr().out
    show_payload = json.loads(show_output)

    events_exit = main(
        [
            "task",
            "events",
            str(task_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    events_output = capsys.readouterr().out
    events_payload = json.loads(events_output)

    assert list_exit == 0
    assert "Tasks: 1" in list_output
    assert "Add task CLI" in list_output
    assert show_exit == 0
    assert show_payload["task"]["task_id"] == str(task_id)
    assert show_payload["steps"][0]["step_id"] == str(step_id)
    assert events_exit == 0
    assert [event["event_type"] for event in events_payload] == [
        "TaskCreated",
        "TaskPlanProposed",
    ]


def test_task_show_reports_unknown_task(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    task_id = new_task_id()

    exit_code = main(
        [
            "task",
            "show",
            str(task_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert f"unknown task_id: {task_id}" in captured.err


def test_task_continue_queues_background_job_json(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    _seed_task(db_path, tmp_path, session_id, task_id, step_id)

    exit_code = main(
        [
            "task",
            "continue",
            str(task_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["kind"] == BackgroundJobKind.MUTATING_CONTINUATION.value
    assert payload["job_type"] == "task-continuation-step"
    assert payload["task_id"] == str(task_id)
    assert payload["payload"]["verify_repair"] is False


def _seed_task(
    db_path: Path,
    tmp_path: Path,
    session_id,
    task_id,
    step_id,
) -> None:
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
                        title="Add task CLI",
                        goal="Expose task-plan inspection commands",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskPlanProposed(
                        task_id=task_id,
                        plan=TaskPlanSnapshot(
                            task_id=task_id,
                            title="Add task CLI",
                            goal="Expose task-plan inspection commands",
                            steps=[
                                TaskStepProposal(
                                    step_id=step_id,
                                    title="Implement task command",
                                    order=0,
                                )
                            ],
                        ),
                    ),
                ),
            ]
        )
    finally:
        connection.close()
