"""Integration tests for changeset derivation service creation paths."""

import sqlite3
import subprocess
from pathlib import Path

from glassbox.core import BranchCandidateForked
from glassbox.core import BranchCandidatePlanned
from glassbox.core import BranchCandidateSelected
from glassbox.core import BranchCandidateVerificationStatus
from glassbox.core import BranchCandidateVerified
from glassbox.core import BranchSearchStarted
from glassbox.core import ChangesetCandidateAdopted
from glassbox.core import ChangesetSourceKind
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import TaskCreated
from glassbox.core import TaskPlanStatus
from glassbox.core import TaskStatusChanged
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _start_session(connection: sqlite3.Connection):
    session_id = new_session_id()
    append_events(
        connection,
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd="/tmp/glassbox",
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            )
        ],
    )
    return session_id


def test_changeset_derivation_creates_from_session_task_and_candidate(
    tmp_path: Path,
) -> None:
    connection = _open_initialized_database(tmp_path)
    try:
        session_id = _start_session(connection)
        task_id = new_task_id()
        search_id = new_branch_search_id()
        candidate_id = new_branch_candidate_id()
        candidate_session_id = new_session_id()
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskCreated(
                        task_id=task_id,
                        title="Add changeset service",
                        goal="Derive changesets from local evidence",
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
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchSearchStarted(
                        search_id=search_id,
                        parent_session_id=session_id,
                        objective="try derivation strategies",
                        task_id=task_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchCandidatePlanned(
                        search_id=search_id,
                        candidate_id=candidate_id,
                        strategy_label="smallest diff",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchCandidateForked(
                        search_id=search_id,
                        candidate_id=candidate_id,
                        candidate_session_id=candidate_session_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchCandidateVerified(
                        search_id=search_id,
                        candidate_id=candidate_id,
                        verification_status=BranchCandidateVerificationStatus.PASSED,
                        summary="focused tests passed",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchCandidateSelected(
                        search_id=search_id,
                        candidate_id=candidate_id,
                        reason="best evidence",
                    ),
                ),
            ],
        )
        repository = SQLiteSessionRepository(connection)
        service = ChangesetDerivationService(repository)

        session_result = service.create_from_session(session_id)
        task_result = service.create_from_task(task_id)
        candidate_result = service.create_from_branch_candidate(
            search_id,
            candidate_id,
        )

        session_sources = repository.list_changeset_sources(
            session_id,
            session_result.changeset_id,
        )
        task_sources = repository.list_changeset_sources(
            session_id,
            task_result.changeset_id,
        )
        candidate_sources = repository.list_changeset_sources(
            session_id,
            candidate_result.changeset_id,
        )
    finally:
        connection.close()

    assert session_sources[0].source_kind == ChangesetSourceKind.SESSION
    assert task_sources[0].source_kind == ChangesetSourceKind.TASK
    assert task_sources[0].task_id == task_id
    assert (
        candidate_sources[0].source_kind == ChangesetSourceKind.BRANCH_SEARCH_CANDIDATE
    )
    assert candidate_sources[0].branch_candidate_id == candidate_id
    adoption_payload = candidate_result.stored_events[1].payload
    assert isinstance(adoption_payload, ChangesetCandidateAdopted)
    assert adoption_payload.workspace_mutation_performed is False


def test_changeset_derivation_creates_from_workspace_diff_without_staging(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
    (workspace / "changed.txt").write_text("local change\n", encoding="utf-8")
    connection = _open_initialized_database(tmp_path)
    try:
        session_id = _start_session(connection)
        repository = SQLiteSessionRepository(connection)

        result = ChangesetDerivationService(repository).create_from_workspace_diff(
            session_id,
            workspace,
        )
        sources = repository.list_changeset_sources(session_id, result.changeset_id)
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        connection.close()

    assert sources[0].source_kind == ChangesetSourceKind.WORKSPACE_DIFF
    assert "1 changed path" in sources[0].reason
    assert staged.stdout == ""
