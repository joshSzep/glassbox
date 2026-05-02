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
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationPlanned
from glassbox.core import TaskVerificationStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import new_artifact_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
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
    plan_exit = main(
        [
            "changeset",
            "verification-plan",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    plan = json.loads(capsys.readouterr().out)
    verification_command = plan["recommended_commands"][0]
    verification_id = new_task_verification_id()
    artifact_id = new_artifact_id()
    _seed_verification(
        db_path,
        session_id,
        task_id,
        verification_id,
        command=verification_command.split(),
        artifact_id=artifact_id,
    )
    record_exit = main(
        [
            "changeset",
            "record-verification",
            changeset_id,
            "--verification",
            str(verification_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    recorded = json.loads(capsys.readouterr().out)
    brief_exit = main(
        [
            "changeset",
            "brief",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    brief = json.loads(capsys.readouterr().out)
    brief_show_exit = main(
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
    brief_detail = json.loads(capsys.readouterr().out)
    export_path = tmp_path / "changeset-export.json"
    export_exit = main(
        [
            "changeset",
            "export",
            changeset_id,
            str(export_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    exported = json.loads(capsys.readouterr().out)
    export_payload = json.loads(export_path.read_text(encoding="utf-8"))
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
    assert plan_exit == 0
    assert plan["expected_scope"] == ["app.py"]
    assert plan["readiness"]["state"] == "missing"
    assert record_exit == 0
    assert recorded["readiness"]["state"] == "passed"
    assert recorded["retained_artifact_ids"] == [str(artifact_id)]
    assert brief_exit == 0
    assert brief["brief"]["artifact_kind"] == "changeset_review_brief"
    assert brief["brief"]["verification"]["body"].startswith("Readiness is passed")
    assert brief["event"]["payload"]["event_type"] == "ChangesetReviewBriefCreated"
    assert brief["readiness_event"]["payload"]["state"] == "ready"
    assert Path(tmp_path / brief["artifact_path"]).exists()
    assert brief_show_exit == 0
    assert (
        brief_detail["changeset"]["latest_review_brief_artifact_id"]
        == (brief["artifact_id"])
    )
    assert brief_detail["review_briefs"][0]["artifact_id"] == brief["artifact_id"]
    assert brief_detail["readiness"][0]["readiness_kind"] == "review"
    assert export_exit == 0
    assert exported["status"] == "exported"
    assert export_payload["export_kind"] == "changeset_review_export"
    assert export_payload["changeset"]["changeset_id"] == changeset_id
    assert export_payload["review_brief"]["artifact_id"] == brief["artifact_id"]
    assert (
        "raw .glassbox database state is not included"
        in (export_payload["redaction_report"])
    )
    assert export_payload["artifact_references"][0]["local_only"] is True
    assert stale_show_exit == 0
    assert stale_detail["inventory"]["freshness"] == "stale"
    assert stale_detail["verification_posture"]["state"] == "passed"
    assert stale_detail["verification_plan"]["readiness"]["state"] == "stale"
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


def _seed_verification(
    db_path: Path,
    session_id,
    task_id,
    verification_id,
    *,
    command: list[str],
    artifact_id,
) -> None:
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=VerificationPlanEntry(
                            verification_id=verification_id,
                            check_name="changeset verification",
                            kind=VerificationCheckKind.COMMAND,
                            command=command,
                            source=VerificationPlanSource.EVAL_RECOMMENDATION,
                            rationale="operator selected changeset plan command",
                            changed_paths=[Path("app.py")],
                        ),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationCompleted(
                        task_id=task_id,
                        verification_id=verification_id,
                        status=TaskVerificationStatus.PASSED,
                        summary="selected verification passed",
                        artifact_id=artifact_id,
                    ),
                ),
            ]
        )
    finally:
        connection.close()
