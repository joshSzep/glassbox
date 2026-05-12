"""HTTP integration tests for the operator-console aggregate API (GBX-321)."""

import asyncio
import sqlite3
from datetime import UTC
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from glassbox.core import EventEnvelope
from glassbox.core import SessionConfig
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import SessionFailed
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.bus import EventBus
from glassbox.runtime.daemon import RuntimeOwnerRecord
from glassbox.runtime.daemon import RuntimeOwnerStatus
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


def _append_in_progress_turn(
    repo: SQLiteSessionRepository,
    session_id,
    *,
    user_text: str,
) -> None:
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


def _append_pending_question(
    repo: SQLiteSessionRepository,
    session_id,
    *,
    question: str,
) -> str:
    user_message_id = new_message_id()
    turn_id = new_turn_id()
    question_id = new_question_id()
    repo.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=UserMessageReceived(
                message_id=user_message_id,
                text="Need operator input",
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
            payload=UserQuestionAsked(
                question_id=question_id,
                turn_id=turn_id,
                tool_call_id=new_tool_call_id(),
                provider_tool_call_id="provider-tool-call-1",
                question=question,
            ),
        )
    )
    return str(question_id)


def _append_pending_approval(
    repo: SQLiteSessionRepository,
    session_id,
    *,
    subject: str,
    reason: str,
) -> str:
    approval_id = new_approval_id()
    repo.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=ApprovalRequested(
                approval_id=approval_id,
                turn_id=new_turn_id(),
                subject=subject,
                reason=reason,
            ),
        )
    )
    return str(approval_id)


def _append_failure(
    repo: SQLiteSessionRepository,
    session_id,
    *,
    message: str,
) -> None:
    repo.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=SessionFailed(
                error_message=message,
                retryable=False,
            ),
        )
    )


def _wipe_session_state_projection(
    connection: sqlite3.Connection,
    session_id,
) -> None:
    with connection:
        connection.execute(
            "delete from session_state where session_id = ?",
            (str(session_id),),
        )


def _running_owner_status(tmp_path: Path) -> RuntimeOwnerStatus:
    return RuntimeOwnerStatus(
        state="running",
        health="ok",
        record=RuntimeOwnerRecord(
            pid=4321,
            workspace_root=tmp_path,
            database_path=tmp_path / ".glassbox" / "glassbox.sqlite3",
            host="127.0.0.1",
            port=8765,
            dashboard_url="http://127.0.0.1:8765/",
            started_at=datetime(2026, 4, 24, tzinfo=UTC),
        ),
    )


def test_get_sessions_aggregate_returns_priority_counts_and_runtime_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)

            approval_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "approval",
                    approval_mode="confirm",
                )
            )
            approval_id = _append_pending_approval(
                repo,
                approval_state.session_id,
                subject="apply_patch",
                reason="needs operator sign-off",
            )

            question_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "question",
                    approval_mode="confirm",
                )
            )
            question_id = _append_pending_question(
                repo,
                question_state.session_id,
                question="Proceed with deployment?",
            )

            failed_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "failed",
                    approval_mode="confirm",
                )
            )
            _append_failure(
                repo,
                failed_state.session_id,
                message="provider bootstrap failed",
            )

            degraded_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "degraded",
                    approval_mode="confirm",
                )
            )
            _wipe_session_state_projection(connection, degraded_state.session_id)

            active_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "active",
                    approval_mode="confirm",
                )
            )
            _append_in_progress_turn(
                repo,
                active_state.session_id,
                user_text="Inspect the repository",
            )

            idle_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "idle",
                    approval_mode="confirm",
                )
            )

            monkeypatch.setattr(
                "glassbox.web.routes.sessions.inspect_runtime_owner",
                lambda _workspace_root: _running_owner_status(tmp_path),
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/sessions/aggregate")

            assert response.status_code == 200
            body = response.json()
            assert body["queue_counts"] == {
                "total": 6,
                "approvals": 1,
                "questions": 1,
                "failures": 1,
                "degraded": 1,
                "active": 5,
                "action_needed": 4,
                "historical": 1,
            }
            assert body["operator_queue_schema_version"] == "operator-queue.v1"
            assert body["operator_queue_counts"] == {
                "total": 10,
                "work_blocking": 3,
                "review_blocking": 0,
                "verification_blocking": 0,
                "maintenance": 6,
                "advisory": 0,
                "informational": 1,
            }
            assert [item["family"] for item in body["operator_queue"][:3]] == [
                "work_blocking",
                "work_blocking",
                "work_blocking",
            ]
            assert (
                sum(
                    1
                    for item in body["operator_queue"]
                    if item["family"] == "maintenance"
                )
                == 6
            )
            assert {
                item["dedupe_key"]["key"]
                for item in body["operator_queue"]
                if item["family"] == "maintenance"
            } >= {
                "maintenance:projection_drift",
                "maintenance:backup_posture",
                "maintenance:stale_repository_intelligence",
                "maintenance:provider_config_issues",
                "maintenance:eval_baseline_drift",
            }
            queue_item = next(
                item
                for item in body["operator_queue"]
                if item["dedupe_key"]["key"]
                == f"work:session:{approval_state.session_id}:approval:{approval_id}"
            )
            assert queue_item["target"]["target_id"] == str(approval_state.session_id)
            assert queue_item["safe_next_action"]["kind"] == "approve"
            assert (
                queue_item["evidence_summary"]["supporting_evidence"][0]["ref_id"]
                == approval_id
            )
            assert body["projection_health_counts"] == {
                "ok": 5,
                "stale": 1,
                "unavailable": 0,
                "degraded": 1,
            }
            assert body["runtime"] == {
                "workspace_root": str(tmp_path),
                "state": "running",
                "health": "ok",
                "pid": 4321,
                "dashboard_url": "http://127.0.0.1:8765/",
                "health_url": "http://127.0.0.1:8765/healthz",
                "session_index_url": "http://127.0.0.1:8765/",
                "started_at": "2026-04-24T00:00:00Z",
                "background_job_failed_count": 0,
                "background_job_retryable_count": 0,
                "background_job_abandoned_count": 0,
            }
            assert body["provider_evidence"]["advisory"] is True
            assert body["provider_evidence"]["latest_status"] == "missing"
            assert body["provider_evidence"]["freshness_status"] == "missing"
            assert body["provider_evidence"]["provider"] is None
            assert body["provider_evidence"]["model_name"] is None
            assert body["provider_evidence"]["next_actions"] == [
                f"glassbox provider canary run --cwd {tmp_path}"
            ]
            assert body["repository_intelligence"]["index_status"] == "missing"
            assert body["repository_intelligence"]["topology_status"] == "missing"
            assert body["repository_intelligence"]["command_recipe_status"] == "missing"
            assert body["repository_intelligence"]["freshness_cues"]
            assert body["knowledge_posture"]["overall_status"] in {
                "degraded",
                "missing",
                "stale",
            }
            assert {cue["key"] for cue in body["knowledge_posture"]["cues"]} >= {
                "workspace-memory",
                "repository-index",
                "checkpoints",
                "compactions",
                "verification",
                "provider-evidence",
            }
            assert (
                "glassbox repo index status --cwd ."
                in body["knowledge_posture"]["next_actions"]
            )
            repository_cue = next(
                cue
                for cue in body["knowledge_posture"]["cues"]
                if cue["key"] == "repository-index"
            )
            assert repository_cue["provenance"][0]["source_kind"] == "repository-index"
            assert repository_cue["provenance"][0]["path"].endswith(
                "repository-index.json"
            )
            assert [item["session_id"] for item in body["sessions"]] == [
                str(approval_state.session_id),
                str(question_state.session_id),
                str(failed_state.session_id),
                str(degraded_state.session_id),
                str(active_state.session_id),
                str(idle_state.session_id),
            ]
            assert [item["priority_bucket"] for item in body["sessions"]] == [
                "approvals",
                "questions",
                "failures",
                "degraded",
                "running",
                "idle_running",
            ]
            assert body["sessions"][0]["pending_approval_id"] == approval_id
            assert body["sessions"][1]["pending_question_id"] == question_id
            assert body["sessions"][2]["session_failure_message"] == (
                "provider bootstrap failed"
            )
            assert body["sessions"][3]["projection_health"]["state"] == "stale"
            assert body["sessions"][3]["action_needed"] is True
            assert body["sessions"][4]["has_active_turn"] is True
            assert body["sessions"][4]["next_action_summary"] == (
                "Wait for the current turn to finish"
            )
            assert body["sessions"][5]["has_active_turn"] is False
            assert body["sessions"][5]["next_action_summary"] == "Send the next prompt"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_sessions_aggregate_supports_queue_status_and_sort_filters(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)

            question_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "question",
                    approval_mode="confirm",
                )
            )
            _append_pending_question(
                repo,
                question_state.session_id,
                question="Proceed?",
            )

            active_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "active",
                    approval_mode="confirm",
                )
            )
            _append_in_progress_turn(
                repo,
                active_state.session_id,
                user_text="Inspect the repository",
            )

            idle_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path / "idle",
                    approval_mode="confirm",
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                question_response = await client.get(
                    "/sessions/aggregate",
                    params={
                        "queue": "questions",
                        "status": "awaiting_user_input",
                    },
                )
                running_response = await client.get(
                    "/sessions/aggregate",
                    params={
                        "status": "running",
                        "sort": "updated_at",
                        "limit": 1,
                    },
                )

            assert question_response.status_code == 200
            question_body = question_response.json()
            assert [item["session_id"] for item in question_body["sessions"]] == [
                str(question_state.session_id)
            ]
            assert question_body["sessions"][0]["queue_memberships"] == [
                "questions",
                "active",
                "action-needed",
            ]

            assert running_response.status_code == 200
            running_body = running_response.json()
            assert running_body["limit"] == 1
            assert [item["session_id"] for item in running_body["sessions"]] == [
                str(idle_state.session_id)
            ]
            assert running_body["sessions"][0]["priority_bucket"] == "idle_running"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_sessions_aggregate_matches_snapshot_summary_fields(tmp_path: Path) -> None:
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
                    cwd=tmp_path / "question",
                    approval_mode="confirm",
                )
            )
            question_id = _append_pending_question(
                repo,
                state.session_id,
                question="Need more context?",
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                aggregate_response = await client.get(
                    "/sessions/aggregate",
                    params={"queue": "questions"},
                )
                snapshot_response = await client.get(f"/sessions/{state.session_id}")

            assert aggregate_response.status_code == 200
            assert snapshot_response.status_code == 200

            summary = aggregate_response.json()["sessions"][0]
            snapshot = snapshot_response.json()
            assert summary["session_id"] == snapshot["session_id"]
            assert summary["status"] == snapshot["status"]
            assert summary["pending_question_id"] == question_id
            assert summary["pending_question_id"] == snapshot["pending_question_id"]
            assert summary["pending_question_text"] == snapshot["pending_question_text"]
            assert summary["projection_health"] == snapshot["projection_health"]
            assert (
                summary["next_action_summary"]
                == "Answer pending question: Need more context?"
            )
            assert summary["live_actionable"] is True
            assert summary["historical_only"] is False
        finally:
            connection.close()

    asyncio.run(scenario())
