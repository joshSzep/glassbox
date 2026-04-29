"""HTTP integration tests for branch-search dashboard APIs."""

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import BranchCandidatePlanned
from glassbox.core import BranchCandidateVerified
from glassbox.core import BranchSearchStarted
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.core import new_session_id
from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.web import create_app


def test_branch_search_routes_show_and_mark_candidates(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            search_id = new_branch_search_id()
            selected_id = new_branch_candidate_id()
            rejected_id = new_branch_candidate_id()
            review_id = new_branch_candidate_id()
            repository = SQLiteSessionRepository(connection)
            _seed_branch_search(
                repository,
                tmp_path,
                session_id,
                search_id,
                selected_id,
            )
            _append_candidate(repository, session_id, search_id, rejected_id, "Reject")
            _append_candidate(repository, session_id, search_id, review_id, "Review")

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                list_response = await client.get("/branch-searches")
                detail_response = await client.get(f"/branch-searches/{search_id}")
                select_response = await client.post(
                    f"/branch-searches/{search_id}/candidates/{selected_id}/select",
                    json={"actor": "qa", "reason": "best verification"},
                )
                reject_response = await client.post(
                    f"/branch-searches/{search_id}/candidates/{rejected_id}/reject",
                    json={"actor": "qa", "reason": "too broad"},
                )
                review_response = await client.post(
                    f"/branch-searches/{search_id}/candidates/{review_id}/needs-review",
                    json={"actor": "qa", "reason": "needs artifact review"},
                )
                updated_detail = await client.get(f"/branch-searches/{search_id}")

            assert list_response.status_code == 200
            assert list_response.json()["items"][0]["search_id"] == str(search_id)
            assert detail_response.status_code == 200
            assert (
                detail_response.json()["candidates"][0]["verification_status"]
                == "passed"
            )
            assert select_response.status_code == 200
            assert select_response.json()["candidate"]["selection_state"] == "selected"
            assert reject_response.status_code == 200
            assert reject_response.json()["candidate"]["selection_state"] == "rejected"
            assert review_response.status_code == 200
            assert (
                review_response.json()["candidate"]["selection_state"] == "needs_review"
            )
            states = {
                candidate["candidate_id"]: candidate["selection_state"]
                for candidate in updated_detail.json()["candidates"]
            }
            assert states[str(selected_id)] == "selected"
            assert states[str(rejected_id)] == "rejected"
            assert states[str(review_id)] == "needs_review"
        finally:
            connection.close()

    asyncio.run(scenario())


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context)


def _seed_branch_search(
    repository: SQLiteSessionRepository,
    tmp_path: Path,
    session_id,
    search_id,
    candidate_id,
) -> None:
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


def _append_candidate(
    repository: SQLiteSessionRepository,
    session_id,
    search_id,
    candidate_id,
    label: str,
) -> None:
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
