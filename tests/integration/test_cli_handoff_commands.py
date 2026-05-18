"""CLI integration tests for handoff custody decisions."""

import json
from pathlib import Path

import pytest

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffIntent
from glassbox.core import HandoffPackageCreated
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffSourceKind
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_cli_handoff_accept_reject_and_archive(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "glassbox.sqlite3"
    session_id, package_id = _seed_handoff(tmp_path, db_path)

    list_exit = main(
        [
            "handoff",
            "list",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    list_payload = json.loads(capsys.readouterr().out)

    accept_exit = main(
        [
            "handoff",
            "accept",
            str(session_id),
            package_id,
            "--accepted-by",
            "recipient",
            "--follow-up-intent",
            "verification-needed",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    accept_payload = json.loads(capsys.readouterr().out)

    reject_exit = main(
        [
            "handoff",
            "reject",
            str(session_id),
            package_id,
            "--reason",
            "missing local-only evidence",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    reject_payload = json.loads(capsys.readouterr().out)

    archive_exit = main(
        [
            "handoff",
            "archive",
            str(session_id),
            package_id,
            "--reason",
            "historical record retained",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    archive_payload = json.loads(capsys.readouterr().out)

    default_list_exit = main(
        [
            "handoff",
            "list",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    default_list = json.loads(capsys.readouterr().out)

    archived_list_exit = main(
        [
            "handoff",
            "list",
            "--include-archived",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    archived_list = json.loads(capsys.readouterr().out)

    assert list_exit == 0
    assert list_payload[0]["action_state"] == "awaiting-recipient"
    assert accept_exit == 0
    assert accept_payload["event_type"] == "HandoffCustodyAccepted"
    assert accept_payload["record"]["custody_state"] == "accepted"
    assert accept_payload["record"]["follow_up_intent"] == "verification-needed"
    assert reject_exit == 0
    assert reject_payload["record"]["custody_state"] == "rejected"
    assert reject_payload["record"]["decision_reason"] == "missing local-only evidence"
    assert archive_exit == 0
    assert archive_payload["record"]["archived"] is True
    assert archive_payload["record"]["action_state"] == "archived-historical"
    assert default_list_exit == 0
    assert default_list == []
    assert archived_list_exit == 0
    assert archived_list[0]["package_id"] == package_id


def _seed_handoff(tmp_path: Path, db_path: Path):
    connection = open_database(db_path)
    initialize_database(connection)
    session_id = new_session_id()
    package_id = "pkg-review"
    try:
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
                    payload=HandoffPackageCreated(
                        package_id=package_id,
                        source_kind=HandoffSourceKind.SESSION,
                        source_id=str(session_id),
                        package_kind=HandoffPackageKind.SESSION,
                        intent=HandoffIntent.REVIEW_ONLY,
                        package_digest="digest",
                        compatibility_state=HandoffCompatibilityState.SUPPORTED,
                        redaction_posture=HandoffRedactionPosture.REDACTED,
                    ),
                ),
            ]
        )
    finally:
        connection.close()
    return session_id, package_id
