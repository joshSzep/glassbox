"""HTTP integration tests for session fork creation and lineage contracts."""

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import EventEnvelope
from glassbox.core import MessagePart
from glassbox.core import SessionConfig
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_turn_id
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.bus import EventBus
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.web import create_app


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_database(db_path)
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context), runtime_context


def _append_completed_turn(
    repo: SQLiteSessionRepository,
    session_id,
    *,
    user_text: str,
    assistant_text: str,
):
    user_message_id = new_message_id()
    turn_id = new_turn_id()

    repo.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=UserMessageReceived(
                message_id=user_message_id,
                text=user_text,
            ),
        )
    )
    repo.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=TurnStarted(
                turn_id=turn_id,
                trigger_message_id=user_message_id,
            ),
        )
    )
    repo.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=AssistantMessageCompleted(
                message_id=new_message_id(),
                parts=[MessagePart(kind="text", text=assistant_text)],
            ),
        )
    )
    repo.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=TurnCompleted(
                turn_id=turn_id,
                outcome="completed",
            ),
        )
    )
    return turn_id


def test_post_session_fork_creates_child_from_latest_completed_turn(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            _append_completed_turn(
                repo,
                parent_state.session_id,
                user_text="Inspect the repository",
                assistant_text="I received your request: Inspect the repository",
            )
            parent_events_before = repo.read_session_events(parent_state.session_id)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{parent_state.session_id}/fork",
                    json={"branch_label": "alt-path"},
                )

            parent_events_after = repo.read_session_events(parent_state.session_id)
            sessions = repo.list_sessions()
            child_session = next(
                session
                for session in sessions
                if session.session_id != parent_state.session_id
            )
            child_transcript = repo.list_transcript_messages(child_session.session_id)

            assert response.status_code == 201
            body = response.json()
            assert body["child_session_id"] == str(child_session.session_id)
            assert body["parent_session_id"] == str(parent_state.session_id)
            assert body["branch_label"] == "alt-path"
            assert body["inherited_message_count"] == 2
            assert body["last_sequence"] == 3
            assert child_session.parent_session_id == parent_state.session_id
            assert child_session.branch_label == "alt-path"
            assert [message.parts[0].text for message in child_transcript] == [
                "Inspect the repository",
                "I received your request: Inspect the repository",
            ]
            assert len(parent_events_before) == len(parent_events_after)
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_fork_supports_explicit_turn_selection(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            first_completed_turn_id = _append_completed_turn(
                repo,
                parent_state.session_id,
                user_text="First prompt",
                assistant_text="I received your request: First prompt",
            )
            _append_completed_turn(
                repo,
                parent_state.session_id,
                user_text="Second prompt",
                assistant_text="I received your request: Second prompt",
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{parent_state.session_id}/fork",
                    json={"turn_id": str(first_completed_turn_id)},
                )

            child_session_id = response.json()["child_session_id"]
            child_transcript = repo.list_transcript_messages(child_session_id)

            assert response.status_code == 201
            assert response.json()["forked_from_turn_id"] == str(
                first_completed_turn_id
            )
            assert [message.parts[0].text for message in child_transcript] == [
                "First prompt",
                "I received your request: First prompt",
            ]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_fork_returns_404_for_unknown_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, _ = _make_app(tmp_path, connection)
            unknown_session_id = "00000000-0000-0000-0000-000000000099"

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{unknown_session_id}/fork",
                    json={},
                )

            assert response.status_code == 404
            assert response.json()["detail"] == (
                f"session {unknown_session_id} not found"
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_fork_returns_409_for_invalid_turn_selection(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            _append_completed_turn(
                repo,
                parent_state.session_id,
                user_text="Inspect the repository",
                assistant_text="I received your request: Inspect the repository",
            )
            unknown_turn_id = "00000000-0000-0000-0000-000000000088"

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{parent_state.session_id}/fork",
                    json={"turn_id": unknown_turn_id},
                )

            assert response.status_code == 409
            assert response.json()["detail"] == f"unknown turn_id: {unknown_turn_id}"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_post_session_fork_returns_409_for_non_branchable_session_state(
    tmp_path: Path,
) -> None:
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
            turn_id = new_turn_id()
            repo.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=new_message_id(),
                    ),
                )
            )
            repo.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=ApprovalRequested(
                        approval_id=new_approval_id(),
                        turn_id=turn_id,
                        reason="needs confirmation",
                        subject="apply_patch",
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    f"/sessions/{state.session_id}/fork",
                    json={},
                )

            assert response.status_code == 409
            assert response.json()["detail"] == (
                f"session {state.session_id} is awaiting approval"
            )
        finally:
            connection.close()

    asyncio.run(scenario())
