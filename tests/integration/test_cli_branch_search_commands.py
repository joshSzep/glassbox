"""CLI coverage for branch-search inspection commands."""

import json
from pathlib import Path

from glassbox.cli import main
from glassbox.core import BranchCandidatePlanned
from glassbox.core import BranchCandidateVerified
from glassbox.core import BranchSearchStarted
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.core import new_session_id
from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_branch_search_list_and_show_commands(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    search_id = new_branch_search_id()
    candidate_id = new_branch_candidate_id()
    _seed_branch_search(db_path, tmp_path, session_id, search_id, candidate_id)

    list_exit = main(
        [
            "branch-search",
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
            "branch-search",
            "show",
            str(search_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert list_exit == 0
    assert "Branch searches: 1" in list_output
    assert "Compare repair options" in list_output
    assert show_exit == 0
    assert payload["search"]["search_id"] == str(search_id)
    assert payload["candidates"][0]["candidate_id"] == str(candidate_id)
    assert payload["candidates"][0]["verification_status"] == "passed"
    assert payload["decision_support"]["automatic_merge"] is False
    assert (
        payload["decision_support"]["candidates"][0]["recommended_follow_up_action"]
        == "Candidate is eligible for operator review and explicit selection."
    )
    assert (
        payload["decision_support"]["candidates"][0]["verification_recommendations"][0][
            "source"
        ]
        == "existing-evidence"
    )


def test_branch_search_start_records_bounded_plan(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    _seed_session(db_path, tmp_path, session_id)

    exit_code = main(
        [
            "branch-search",
            "start",
            str(session_id),
            "--objective",
            "Try two repairs",
            "--strategy",
            "minimal",
            "--strategy",
            "broader",
            "--max-candidates",
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
    assert payload["parent_session_id"] == str(session_id)
    assert len(payload["candidate_ids"]) == 1


def test_branch_search_select_reject_and_needs_review_are_projected(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    search_id = new_branch_search_id()
    selected_id = new_branch_candidate_id()
    rejected_id = new_branch_candidate_id()
    review_id = new_branch_candidate_id()
    _seed_branch_search(db_path, tmp_path, session_id, search_id, selected_id)
    _append_candidate(db_path, session_id, search_id, rejected_id, "Reject me")
    _append_candidate(db_path, session_id, search_id, review_id, "Review me")

    for command, candidate_id, expected_output in (
        ("select", selected_id, "as selected"),
        ("reject", rejected_id, "as rejected"),
        ("needs-review", review_id, "as needs review"),
    ):
        exit_code = main(
            [
                "branch-search",
                command,
                str(search_id),
                str(candidate_id),
                "--reason",
                f"{command} reason",
                "--cwd",
                str(tmp_path),
                "--db-path",
                str(db_path),
            ]
        )
        assert exit_code == 0
        assert expected_output in capsys.readouterr().out

    show_exit = main(
        [
            "branch-search",
            "show",
            str(search_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    states = {
        candidate["candidate_id"]: candidate["selection_state"]
        for candidate in payload["candidates"]
    }

    assert show_exit == 0
    assert payload["search"]["selected_candidate_id"] == str(selected_id)
    assert states[str(selected_id)] == "selected"
    assert states[str(rejected_id)] == "rejected"
    assert states[str(review_id)] == "needs_review"
    support_by_id = {
        candidate["candidate_id"]: candidate
        for candidate in payload["decision_support"]["candidates"]
    }
    assert support_by_id[str(selected_id)]["risk_posture"] == "strong"
    assert support_by_id[str(rejected_id)]["risk_posture"] == "blocked"
    assert support_by_id[str(review_id)]["risk_posture"] == "review"
    assert (
        support_by_id[str(review_id)]["verification_recommendations"][0]["source"]
        == "missing-changed-files"
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


def _append_candidate(
    db_path: Path,
    session_id,
    search_id,
    candidate_id,
    label: str,
) -> None:
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BranchCandidatePlanned(
                    search_id=search_id,
                    candidate_id=candidate_id,
                    strategy_label=label,
                ),
            )
        )
    finally:
        connection.close()


def _seed_branch_search(
    db_path: Path,
    tmp_path: Path,
    session_id,
    search_id,
    candidate_id,
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
                    payload=BranchSearchStarted(
                        search_id=search_id,
                        parent_session_id=session_id,
                        objective="Compare repair options",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchCandidatePlanned(
                        search_id=search_id,
                        candidate_id=candidate_id,
                        strategy_label="Try minimal fix",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchCandidateVerified(
                        search_id=search_id,
                        candidate_id=candidate_id,
                        verification_status=BranchCandidateVerificationStatus.PASSED,
                        summary="Targeted tests passed.",
                    ),
                ),
            ]
        )
    finally:
        connection.close()
