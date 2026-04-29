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
