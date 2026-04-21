"""HTTP integration tests for the approval resolution endpoint (GBX-083)."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import EventEnvelope, SessionConfig
from glassbox.core.events import ApprovalRequested
from glassbox.core.ids import new_approval_id, new_turn_id
from glassbox.core.types import ApprovalDecision
from glassbox.runtime import EventBus, SessionSupervisor
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import (
    SQLiteSessionRepository,
    initialize_database,
    open_database,
)
from glassbox.web import create_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context), runtime_context


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolve_approval_returns_404_for_unknown_session(tmp_path: Path) -> None:
    """POST to an unknown session returns 404."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, _ = _make_app(tmp_path, connection)
            unknown_id = "00000000-0000-0000-0000-000000000099"
            unknown_approval = "00000000-0000-0000-0000-000000000001"

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{unknown_id}/approvals/{unknown_approval}",
                    json={"decision": "approved"},
                )

            assert response.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())


def test_resolve_approval_approve_succeeds(tmp_path: Path) -> None:
    """POST approve on a pending approval returns 200 and resolves it."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)

            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            approval_id = new_approval_id()
            repo.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=ApprovalRequested(
                        approval_id=approval_id,
                        turn_id=new_turn_id(),
                        reason="needs sign-off",
                        subject="apply_patch",
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/approvals/{approval_id}",
                    json={"decision": ApprovalDecision.APPROVED},
                )

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        finally:
            connection.close()

    asyncio.run(scenario())


def test_resolve_approval_deny_succeeds(tmp_path: Path) -> None:
    """POST deny on a pending approval returns 200 and resolves it."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)

            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            approval_id = new_approval_id()
            repo.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=ApprovalRequested(
                        approval_id=approval_id,
                        turn_id=new_turn_id(),
                        reason="needs sign-off",
                        subject="apply_patch",
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/approvals/{approval_id}",
                    json={"decision": ApprovalDecision.DENIED},
                )

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        finally:
            connection.close()

    asyncio.run(scenario())


def test_resolve_approval_returns_409_when_session_not_awaiting(tmp_path: Path) -> None:
    """POST to a session that is not AWAITING_APPROVAL returns 409."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)

            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            # Session is RUNNING, not AWAITING_APPROVAL
            fake_approval_id = new_approval_id()

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/approvals/{fake_approval_id}",
                    json={"decision": ApprovalDecision.APPROVED},
                )

            assert response.status_code == 409
        finally:
            connection.close()

    asyncio.run(scenario())


def test_resolve_approval_returns_409_for_unknown_approval_id(tmp_path: Path) -> None:
    """POST with an unknown approval_id returns 409."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)

            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            # Seed real approval to put session in AWAITING_APPROVAL
            real_approval_id = new_approval_id()
            repo.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=ApprovalRequested(
                        approval_id=real_approval_id,
                        turn_id=new_turn_id(),
                        reason="needs sign-off",
                        subject="apply_patch",
                    ),
                )
            )

            wrong_approval_id = new_approval_id()
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/approvals/{wrong_approval_id}",
                    json={"decision": ApprovalDecision.APPROVED},
                )

            assert response.status_code == 409
        finally:
            connection.close()

    asyncio.run(scenario())


def test_resolve_approval_request_schema_reject_invalid_decision(
    tmp_path: Path,
) -> None:
    """POST with an invalid decision value returns 422 Unprocessable Entity."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)

            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            approval_id = new_approval_id()
            repo.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=ApprovalRequested(
                        approval_id=approval_id,
                        turn_id=new_turn_id(),
                        reason="needs sign-off",
                        subject="apply_patch",
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/approvals/{approval_id}",
                    json={"decision": "maybe"},
                )

            assert response.status_code == 422
        finally:
            connection.close()

    asyncio.run(scenario())
