"""HTTP integration tests for the session snapshot API (GBX-081)."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import EventEnvelope, MessagePart, SessionConfig
from glassbox.core.events import (
    ApprovalRequested,
    AssistantMessageCompleted,
    ModelCallCompleted,
    SessionFailed,
    TurnCompleted,
    TurnStarted,
    UserMessageReceived,
    UserQuestionAsked,
)
from glassbox.core.ids import (
    new_approval_id,
    new_message_id,
    new_question_id,
    new_tool_call_id,
    new_turn_id,
)
from glassbox.runtime import EventBus, SessionSupervisor
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import (
    SQLiteSessionRepository,
    initialize_database,
    open_database,
)
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


def test_get_session_returns_404_for_unknown_session(tmp_path: Path) -> None:
    """GET /sessions/{id} returns 404 for a session that does not exist."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, _ = _make_app(tmp_path, connection)
            unknown_id = "00000000-0000-0000-0000-000000000099"

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{unknown_id}")

            assert response.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_returns_snapshot_after_session_started(tmp_path: Path) -> None:
    """GET /sessions/{id} returns the session metadata after the session is started."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["session_id"] == str(state.session_id)
            assert body["model_name"] == "openai:gpt-5.4"
            assert body["approval_mode"] == "confirm"
            assert body["status"] == "running"
            assert body["current_turn_id"] is None
            assert body["dashboard_url"] is None
            assert body["pending_approval_id"] is None
            assert body["pending_question_id"] is None
            assert body["pending_question_text"] is None
            assert body["session_failure_message"] is None
            assert body["session_failure_retryable"] is None
            assert body["transcript"] == []
            assert body["active_tool_calls"] == []
            assert body["pending_approvals"] == []
            assert (
                body["runtime_context"]["repository_context"]["workspace_name"]
                == tmp_path.name
            )
            assert body["runtime_context"]["runtime_notes"] == []
            assert body["runtime_context"]["additional_runtime_note_count"] == 0
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_includes_dashboard_url_when_live_dashboard_is_configured(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
                dashboard_url="http://127.0.0.1:8765/",
            )
            state = await supervisor.start_session(config)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["dashboard_url"] == "http://127.0.0.1:8765/"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_includes_transcript_messages(tmp_path: Path) -> None:
    """Snapshot transcript reflects persisted messages."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            (tmp_path / "src").mkdir(exist_ok=True)
            (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
            app, runtime_context = _make_app(tmp_path, connection)
            repo = runtime_context.repositories.sessions
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)
            # UserMessageReceived drives a transcript projection
            await supervisor.submit_user_message(state.session_id, "Hello!")

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            transcript = body["transcript"]
            # At least the user message must appear
            user_messages = [m for m in transcript if m["role"] == "user"]
            assert len(user_messages) >= 1
            assert any(
                any(part["text"] == "Hello!" for part in m["parts"])
                for m in user_messages
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_includes_pending_approvals(tmp_path: Path) -> None:
    """Pending approvals are listed in the snapshot."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)

            # Seed a pending approval directly
            approval_id = new_approval_id()
            repo.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=ApprovalRequested(
                        approval_id=approval_id,
                        turn_id=new_turn_id(),
                        reason="needs operator sign-off",
                        subject="apply_patch",
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "awaiting_approval"
            pending = body["pending_approvals"]
            assert len(pending) == 1
            assert body["pending_approval_id"] == str(approval_id)
            assert pending[0]["approval_id"] == str(approval_id)
            assert pending[0]["subject"] == "apply_patch"
            assert pending[0]["reason"] == "needs operator sign-off"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_includes_runtime_context_runtime_notes(tmp_path: Path) -> None:
    """Snapshot exposes bounded runtime context for operator inspection."""

    async def scenario() -> None:
        (tmp_path / "src").mkdir(exist_ok=True)
        (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = runtime_context.repositories.sessions
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)
            await supervisor.record_runtime_note(
                state.session_id,
                category="repo",
                message="README.md is the primary operator entrypoint",
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            runtime_context_body = body["runtime_context"]
            assert (
                runtime_context_body["repository_context"]["workspace_name"]
                == tmp_path.name
            )
            assert set(
                runtime_context_body["repository_context"]["high_signal_paths"]
            ) == {"README.md", "src/"}
            assert runtime_context_body["runtime_notes"] == [
                {
                    "category": "repo",
                    "message": "README.md is the primary operator entrypoint",
                    "inherited": False,
                    "source_session_id": str(state.session_id),
                }
            ]
            assert runtime_context_body["additional_runtime_note_count"] == 0
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_includes_pending_user_question_context(tmp_path: Path) -> None:
    """Snapshot exposes awaiting-user-input status and the current turn id."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)
            turn_id = new_turn_id()
            question_id = new_question_id()
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
                    payload=UserQuestionAsked(
                        question_id=question_id,
                        turn_id=turn_id,
                        tool_call_id=new_tool_call_id(),
                        provider_tool_call_id="provider-tool-call-1",
                        question="Proceed?",
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "awaiting_user_input"
            assert body["current_turn_id"] == str(turn_id)
            assert body["pending_question_id"] == str(question_id)
            assert body["pending_question_text"] == "Proceed?"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_includes_latest_session_failure_details(tmp_path: Path) -> None:
    """Snapshot exposes the latest SessionFailed payload for operator debugging."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = runtime_context.repositories.sessions
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)
            repo.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=SessionFailed(
                        error_message="dashboard wiring failed",
                        retryable=True,
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "failed"
            assert body["session_failure_message"] == "dashboard wiring failed"
            assert body["session_failure_retryable"] is True
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_snapshot_response_schema(tmp_path: Path) -> None:
    """Response JSON contains all expected top-level keys."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            body = response.json()
            expected_keys = {
                "session_id",
                "status",
                "current_turn_id",
                "model_name",
                "cwd",
                "approval_mode",
                "parent_session_id",
                "forked_from_turn_id",
                "forked_from_sequence",
                "branch_label",
                "child_sessions",
                "branchable_turns",
                "can_fork",
                "latest_fork_point_turn_id",
                "latest_fork_point_sequence",
                "fork_blocked_reason",
                "dashboard_url",
                "created_at",
                "updated_at",
                "last_sequence",
                "pending_approval_id",
                "pending_question_id",
                "pending_question_text",
                "session_failure_message",
                "session_failure_retryable",
                "transcript",
                "active_tool_calls",
                "pending_approvals",
                "turn_metrics",
            }
            assert expected_keys <= body.keys()
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_includes_lineage_and_child_session_summaries(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = runtime_context.repositories.sessions
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "parent",
                    approval_mode="confirm",
                )
            )
            turn_id = _append_completed_turn(
                repo,
                parent_state.session_id,
                user_text="Inspect the repository",
                assistant_text="I received your request: Inspect the repository",
            )
            forked_session = await supervisor.fork_session(
                parent_state.session_id,
                branch_label="alt-path",
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                parent_response = await client.get(
                    f"/sessions/{parent_state.session_id}"
                )
                child_response = await client.get(
                    f"/sessions/{forked_session.child_session_id}"
                )

            assert parent_response.status_code == 200
            assert child_response.status_code == 200

            parent_body = parent_response.json()
            child_body = child_response.json()

            assert parent_body["parent_session_id"] is None
            assert parent_body["can_fork"] is True
            assert parent_body["latest_fork_point_turn_id"] is not None
            assert parent_body["fork_blocked_reason"] is None
            assert len(parent_body["child_sessions"]) == 1
            assert len(parent_body["branchable_turns"]) == 1
            assert parent_body["branchable_turns"][0]["turn_id"] == str(turn_id)
            assert (
                parent_body["branchable_turns"][0]["label"] == "Inspect the repository"
            )
            assert parent_body["child_sessions"][0]["session_id"] == str(
                forked_session.child_session_id
            )
            assert parent_body["child_sessions"][0]["branch_label"] == "alt-path"

            assert child_body["parent_session_id"] == str(parent_state.session_id)
            assert child_body["forked_from_turn_id"] == str(
                forked_session.forked_from_turn_id
            )
            assert (
                child_body["forked_from_sequence"]
                == forked_session.forked_from_sequence
            )
            assert child_body["branch_label"] == "alt-path"
            assert child_body["child_sessions"] == []
            assert child_body["branchable_turns"] == []
            assert child_body["can_fork"] is False
            assert child_body["latest_fork_point_turn_id"] is None
            assert child_body["latest_fork_point_sequence"] is None
            assert child_body["fork_blocked_reason"] == (
                f"session {forked_session.child_session_id} has no completed fork point"
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_includes_turn_metrics(tmp_path: Path) -> None:
    """Snapshot exposes aggregated per-turn runtime metrics."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = runtime_context.repositories.sessions
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)
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
                    payload=ModelCallCompleted(
                        turn_id=turn_id,
                        input_tokens=42,
                        output_tokens=13,
                        duration_ms=600,
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            assert len(body["turn_metrics"]) == 1
            assert body["turn_metrics"][0]["turn_id"] == str(turn_id)
            assert body["turn_metrics"][0]["model_call_count"] == 1
            assert body["turn_metrics"][0]["model_duration_ms_total"] == 600
            assert body["turn_metrics"][0]["model_input_tokens_total"] == 42
            assert body["turn_metrics"][0]["model_output_tokens_total"] == 13
        finally:
            connection.close()

    asyncio.run(scenario())
