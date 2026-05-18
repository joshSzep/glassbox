"""HTTP integration tests for handoff custody routes."""

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import EventEnvelope
from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffIntent
from glassbox.core import HandoffPackageCreated
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffSourceKind
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database
from glassbox.web import create_app


def test_handoff_routes_record_accept_reject_archive(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = create_app(_build_runtime_context(connection, tmp_path))
            session_id, package_id = _seed_handoff(tmp_path, connection)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                list_response = await client.get("/handoffs")
                accept_response = await client.post(
                    f"/handoffs/{session_id}/{package_id}/accept",
                    json={
                        "accepted_by": "recipient",
                        "follow_up_intent": "continue-work",
                    },
                )
                reject_response = await client.post(
                    f"/handoffs/{session_id}/{package_id}/reject",
                    json={"reason": "recipient cannot inspect local-only evidence"},
                )
                archive_response = await client.post(
                    f"/handoffs/{session_id}/{package_id}/archive",
                    json={"reason": "stored as historical context"},
                )
                visible_response = await client.get("/handoffs")
                archived_response = await client.get(
                    "/handoffs",
                    params={"include_archived": "true"},
                )

            assert list_response.status_code == 200
            assert list_response.json()["items"][0]["action_state"] == (
                "awaiting-recipient"
            )
            assert accept_response.status_code == 200
            assert accept_response.json()["event_type"] == "HandoffCustodyAccepted"
            assert (
                accept_response.json()["handoff"]["record"]["follow_up_intent"]
                == "continue-work"
            )
            assert reject_response.status_code == 200
            assert reject_response.json()["handoff"]["action_state"] == (
                "rejected-needs-sender-review"
            )
            assert archive_response.status_code == 200
            assert archive_response.json()["handoff"]["action_state"] == (
                "archived-historical"
            )
            assert visible_response.json()["items"] == []
            assert archived_response.json()["items"][0]["record"]["archived"] is True
        finally:
            connection.close()

    asyncio.run(scenario())


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


def _seed_handoff(tmp_path: Path, connection: sqlite3.Connection):
    session_id = new_session_id()
    package_id = "pkg-api-review"
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
    return session_id, package_id
