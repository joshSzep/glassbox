"""HTTP integration tests for workspace memory APIs."""

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import EventEnvelope
from glassbox.core import RuntimeNoteRecorded
from glassbox.core import SessionStarted
from glassbox.core import WorkspaceMemoryConfirmed
from glassbox.core import WorkspaceMemoryCreated
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import new_session_id
from glassbox.core import new_workspace_memory_id
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.web import create_app


def test_memory_routes_return_pages_and_detail(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            first_memory_id = new_workspace_memory_id()
            second_memory_id = new_workspace_memory_id()
            repo = SQLiteSessionRepository(connection)
            _seed_memory(
                repo,
                tmp_path,
                session_id,
                first_memory_id,
                summary="first memory",
            )
            _seed_memory(
                repo,
                tmp_path,
                session_id,
                second_memory_id,
                summary="second memory",
                start_session=False,
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                list_response = await client.get("/memory", params={"limit": 1})
                list_next = await client.get(
                    "/memory",
                    params={"cursor": 1, "limit": 1},
                )
                detail_response = await client.get(f"/memory/{first_memory_id}")
                filtered_response = await client.get(
                    "/memory",
                    params={"kind": "command", "state": "active"},
                )
                query_response = await client.get(
                    "/memory",
                    params={"query": "first"},
                )

            assert list_response.status_code == 200
            list_body = list_response.json()
            assert list_body["page"] == {
                "cursor": 0,
                "limit": 1,
                "next_cursor": 1,
                "has_more": True,
                "returned_count": 1,
            }
            assert list_body["items"][0]["summary"] == "second memory"

            assert list_next.status_code == 200
            assert list_next.json()["items"][0]["summary"] == "first memory"

            assert detail_response.status_code == 200
            detail_body = detail_response.json()
            assert detail_body["entry"]["memory_id"] == str(first_memory_id)
            assert detail_body["entry"]["confirmed_by"] == "operator"
            assert detail_body["entry"]["provenance"]["source_sequence"] == 1

            assert filtered_response.status_code == 200
            assert len(filtered_response.json()["items"]) == 2

            assert query_response.status_code == 200
            assert query_response.json()["items"][0]["summary"] == "first memory"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_memory_routes_handle_empty_unknown_and_invalid_pages(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            unknown_memory_id = new_workspace_memory_id()

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                empty_list = await client.get("/memory")
                unknown_detail = await client.get(f"/memory/{unknown_memory_id}")
                invalid_limit = await client.get("/memory", params={"limit": 0})
                invalid_state = await client.get(
                    "/memory",
                    params={"state": "forgotten"},
                )

            assert empty_list.status_code == 200
            assert empty_list.json()["items"] == []
            assert unknown_detail.status_code == 404
            assert invalid_limit.status_code == 422
            assert invalid_state.status_code == 422
        finally:
            connection.close()

    asyncio.run(scenario())


def test_memory_routes_add_confirm_and_reject_candidates(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            repo = SQLiteSessionRepository(connection)
            repo.append_events(
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
                        payload=RuntimeNoteRecorded(
                            category="operator",
                            message="Prefer concise web evidence secret=abc123",
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=RuntimeNoteRecorded(
                            category="runtime",
                            message="Warm repository index before release.",
                        ),
                    ),
                ]
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                add_response = await client.post(
                    "/memory",
                    json={
                        "session_id": str(session_id),
                        "kind": "convention",
                        "content": "Use password=hunter2 only in fixtures",
                    },
                )
                candidates_response = await client.get(
                    "/memory/candidates",
                    params={"session_id": str(session_id)},
                )
                candidates = candidates_response.json()["items"]
                confirm_response = await client.post(
                    f"/memory/candidates/{candidates[0]['candidate_id']}/confirm",
                    json={"session_id": str(session_id), "actor": "operator"},
                )
                reject_response = await client.post(
                    f"/memory/candidates/{candidates[1]['candidate_id']}/reject",
                    json={
                        "session_id": str(session_id),
                        "actor": "operator",
                        "reason": "too transient",
                    },
                )
                empty_candidates_response = await client.get(
                    "/memory/candidates",
                    params={"session_id": str(session_id)},
                )

            assert add_response.status_code == 200
            assert add_response.json()["entry"]["redacted"] is True
            assert "<redacted>" in add_response.json()["entry"]["content"]
            assert candidates_response.status_code == 200
            assert candidates[0]["redacted"] is True
            assert confirm_response.status_code == 200
            assert confirm_response.json()["entry"]["confirmed_by"] == "operator"
            assert reject_response.status_code == 200
            assert reject_response.json()["reason"] == "too transient"
            assert empty_candidates_response.status_code == 200
            assert empty_candidates_response.json()["items"] == []
        finally:
            connection.close()

    asyncio.run(scenario())


def test_memory_routes_confirm_invalidate_and_prune_entries(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            memory_id = new_workspace_memory_id()
            repo = SQLiteSessionRepository(connection)
            _seed_memory(
                repo, tmp_path, session_id, memory_id, summary="operator memory"
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                confirm_response = await client.post(
                    f"/memory/{memory_id}/confirm",
                    json={"actor": "qa", "reason": "still accurate"},
                )
                invalidate_response = await client.post(
                    f"/memory/{memory_id}/invalidate",
                    json={"actor": "qa", "reason": "path changed"},
                )
                missing_reason = await client.post(
                    f"/memory/{memory_id}/prune",
                    json={"actor": "qa"},
                )
                preview_response = await client.post(
                    f"/memory/{memory_id}/prune-preview",
                    json={"actor": "qa", "reason": "cleanup"},
                )
                prune_response = await client.post(
                    f"/memory/{memory_id}/prune",
                    json={"actor": "qa", "reason": "cleanup"},
                )
                pruned_list = await client.get(
                    "/memory",
                    params={"include_pruned": True, "state": "pruned"},
                )

            assert confirm_response.status_code == 200
            assert confirm_response.json()["entry"]["confirmed_by"] == "qa"
            assert invalidate_response.status_code == 200
            assert invalidate_response.json()["entry"]["state"] == "invalidated"
            assert missing_reason.status_code == 400
            assert preview_response.status_code == 200
            assert preview_response.json()["would_prune"] is True
            assert prune_response.status_code == 200
            assert prune_response.json()["entry"]["state"] == "pruned"
            assert pruned_list.status_code == 200
            assert pruned_list.json()["items"][0]["memory_id"] == str(memory_id)
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


def _seed_memory(
    repository: SQLiteSessionRepository,
    tmp_path: Path,
    session_id,
    memory_id,
    *,
    summary: str,
    start_session: bool = True,
) -> None:
    events = []
    if start_session:
        events.append(
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
    events.extend(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=WorkspaceMemoryCreated(
                    memory_id=memory_id,
                    kind=WorkspaceMemoryKind.COMMAND,
                    content="Use uv run pytest for backend tests.",
                    summary=summary,
                    provenance=WorkspaceMemoryProvenance(
                        source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                        session_id=session_id,
                        source_sequence=1,
                    ),
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=WorkspaceMemoryConfirmed(memory_id=memory_id),
            ),
        ]
    )
    repository.append_events(events)
