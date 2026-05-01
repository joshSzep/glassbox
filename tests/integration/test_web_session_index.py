"""HTTP integration tests for the session index API (GBX-181)."""

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import EventEnvelope
from glassbox.core import MessagePart
from glassbox.core import SessionConfig
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import SessionFailed
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_tool_call_id
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


def test_get_sessions_returns_empty_list_when_no_sessions_exist(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, _ = _make_app(tmp_path, connection)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/sessions")

            assert response.status_code == 200
            assert response.json() == []
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_sessions_returns_recent_summaries_in_updated_order(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)

            running_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "running",
                    approval_mode="confirm",
                )
            )
            await supervisor.submit_user_message(
                running_state.session_id,
                "Inspect the repository",
            )

            waiting_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "waiting",
                    approval_mode="confirm",
                )
            )
            turn_id = new_turn_id()
            question_id = new_question_id()
            repo.append_event(
                EventEnvelope(
                    session_id=waiting_state.session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=new_message_id(),
                    ),
                )
            )
            repo.append_event(
                EventEnvelope(
                    session_id=waiting_state.session_id,
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

            failed_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "failed",
                    approval_mode="confirm",
                )
            )
            repo.append_event(
                EventEnvelope(
                    session_id=failed_state.session_id,
                    sequence=0,
                    payload=SessionFailed(
                        error_message="provider bootstrap failed",
                        retryable=False,
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/sessions")

            assert response.status_code == 200
            body = response.json()
            assert [item["session_id"] for item in body] == [
                str(failed_state.session_id),
                str(waiting_state.session_id),
                str(running_state.session_id),
            ]
            assert body[0]["status"] == "failed"
            assert body[0]["next_action_summary"] == (
                "Review failure: provider bootstrap failed"
            )
            assert body[1]["status"] == "awaiting_user_input"
            assert body[1]["pending_question_id"] == str(question_id)
            assert body[1]["pending_question_text"] == "Proceed?"
            assert body[1]["next_action_summary"] == (
                "Answer pending question: Proceed?"
            )
            assert body[2]["status"] == "running"
            assert body[2]["latest_message_summary"] == "user: Inspect the repository"
            assert body[2]["next_action_summary"] == "Send the next prompt"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_sessions_summary_response_includes_expected_top_level_keys(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/sessions")

            assert response.status_code == 200
            body = response.json()
            assert len(body) == 1
            assert body[0]["session_id"] == str(state.session_id)
            assert set(body[0]) == {
                "session_id",
                "status",
                "model_name",
                "cwd",
                "approval_mode",
                "approval_behavior",
                "budget_posture",
                "parent_session_id",
                "forked_from_turn_id",
                "forked_from_sequence",
                "branch_label",
                "child_session_count",
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
                "turn_recovery_posture",
                "latest_checkpoint",
                "checkpoint_absence",
                "latest_provider_recovery",
                "long_run_status",
                "latest_message_summary",
                "projection_health",
                "next_action_summary",
            }
            assert body[0]["turn_recovery_posture"] is None
            assert body[0]["latest_checkpoint"] is None
            assert body[0]["checkpoint_absence"]["reason"] == "not_expected_yet"
            assert body[0]["latest_provider_recovery"] is None
            assert body[0]["long_run_status"]["state"] == "healthy"
            assert body[0]["projection_health"]["state"] == "ok"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_sessions_includes_lineage_and_branchability_fields(tmp_path: Path) -> None:
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
                    cwd=tmp_path / "parent",
                    approval_mode="confirm",
                )
            )
            _append_completed_turn(
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
                response = await client.get("/sessions")

            assert response.status_code == 200
            body = response.json()
            parent_summary = next(
                item
                for item in body
                if item["session_id"] == str(parent_state.session_id)
            )
            child_summary = next(
                item
                for item in body
                if item["session_id"] == str(forked_session.child_session_id)
            )

            assert parent_summary["parent_session_id"] is None
            assert parent_summary["child_session_count"] == 1
            assert parent_summary["can_fork"] is True
            assert parent_summary["latest_fork_point_turn_id"] is not None
            assert parent_summary["latest_fork_point_sequence"] is not None
            assert parent_summary["fork_blocked_reason"] is None

            assert child_summary["parent_session_id"] == str(parent_state.session_id)
            assert child_summary["forked_from_turn_id"] == str(
                forked_session.forked_from_turn_id
            )
            assert (
                child_summary["forked_from_sequence"]
                == forked_session.forked_from_sequence
            )
            assert child_summary["branch_label"] == "alt-path"
            assert child_summary["child_session_count"] == 0
            assert child_summary["can_fork"] is False
            assert child_summary["latest_fork_point_turn_id"] is None
            assert child_summary["latest_fork_point_sequence"] is None
            assert child_summary["fork_blocked_reason"] == (
                f"session {forked_session.child_session_id} has no completed fork point"
            )
        finally:
            connection.close()

    asyncio.run(scenario())
