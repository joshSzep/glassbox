"""HTTP integration tests for the session snapshot API (GBX-081)."""

import asyncio
import json
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import AutonomyBudgetRemaining
from glassbox.core import AutonomyBudgetUsage
from glassbox.core import BudgetDecisionRecorded
from glassbox.core import ContextCompactionCreated
from glassbox.core import ContextCompactionFreshness
from glassbox.core import ContextCompactionScope
from glassbox.core import EventEnvelope
from glassbox.core import MessagePart
from glassbox.core import RuntimeNoteRecorded
from glassbox.core import SessionConfig
from glassbox.core import WorkspaceMemoryConfirmed
from glassbox.core import WorkspaceMemoryCreated
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import new_workspace_memory_id
from glassbox.core.events import ApprovalRequested
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import ModelCallCompleted
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import SessionFailed
from glassbox.core.events import TaskCheckpointCreated
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.events import UserQuestionAsked
from glassbox.core.ids import new_approval_id
from glassbox.core.ids import new_artifact_id
from glassbox.core.ids import new_context_compaction_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_question_id
from glassbox.core.ids import new_task_checkpoint_id
from glassbox.core.ids import new_tool_attempt_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import AutonomyMode
from glassbox.core.types import LongRunPhase
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.autonomy import default_budget_for_autonomy_mode
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context_builder import PYTEST_FAILURE_DIGEST_ARTIFACT_KIND
from glassbox.runtime.context_builder import PytestFailureDigestArtifact
from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP
from glassbox.runtime.repository_index import build_and_write_repository_index
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


def _append_runtime_notes(
    repo: SQLiteSessionRepository,
    session_id,
    *,
    count: int,
) -> None:
    for index in range(count):
        repo.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=RuntimeNoteRecorded(
                    category="test",
                    message=f"large compaction source event {index}",
                ),
            )
        )


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
            assert body["checkpoint_absence"]["reason"] == "not_expected_yet"
            assert body["dashboard_url"] is None
            assert body["pending_approval_id"] is None
            assert body["pending_question_id"] is None
            assert body["pending_question_text"] is None
            assert body["session_failure_message"] is None
            assert body["session_failure_retryable"] is None
            assert body["long_run_status"]["state"] == "healthy"
            assert body["long_run_status"]["last_event_type"] == "SessionStarted"
            assert body["long_run_status"]["progress_summary"]
            assert body["transcript"] == []
            assert body["active_tool_calls"] == []
            assert body["pending_approvals"] == []
            assert (
                body["runtime_context"]["repository_context"]["workspace_name"]
                == tmp_path.name
            )
            assert body["runtime_context"]["runtime_notes"] == []
            assert body["runtime_context"]["additional_runtime_note_count"] == 0
            assert body["runtime_context"]["working_set"] == {
                "items": [],
                "additional_item_count": 0,
            }
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_exposes_latest_checkpoint_and_checkpoint_page(
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
            checkpoint_id = new_task_checkpoint_id()
            runtime_context.repositories.sessions.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=TaskCheckpointCreated(
                        checkpoint_id=checkpoint_id,
                        objective="Expose checkpoint over API",
                        current_phase=LongRunPhase.CHECKPOINTING,
                        completed_step="Projected checkpoint row",
                        next_action="Fetch checkpoint page",
                        recovery_guidance="Resume from the API checkpoint",
                        touched_files=["src/glassbox/web/session_api.py"],
                        verification_status="pending",
                        budget_status="within budget",
                        source_start_sequence=1,
                        source_end_sequence=2,
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                snapshot_response = await client.get(f"/sessions/{state.session_id}")
                page_response = await client.get(
                    f"/sessions/{state.session_id}/checkpoints"
                )

            assert snapshot_response.status_code == 200
            assert page_response.status_code == 200
            snapshot_body = snapshot_response.json()
            page_body = page_response.json()
            assert snapshot_body["latest_checkpoint"]["checkpoint_id"] == str(
                checkpoint_id
            )
            assert snapshot_body["checkpoint_absence"] is None
            assert snapshot_body["latest_checkpoint"]["current_phase"] == (
                "checkpointing"
            )
            assert snapshot_body["checkpoint_history"][0]["next_action"] == (
                "Fetch checkpoint page"
            )
            assert page_body["page"]["returned_count"] == 1
            assert page_body["items"][0]["source_start_sequence"] == 1
            assert page_body["items"][0]["source_end_sequence"] == 2
        finally:
            connection.close()

    asyncio.run(scenario())


def test_session_compaction_api_lists_and_invalidates_with_confirmation(
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
            compaction_id = new_context_compaction_id()
            runtime_context.repositories.sessions.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=ContextCompactionCreated(
                        compaction_id=compaction_id,
                        scope=ContextCompactionScope.TRANSCRIPT,
                        source_start_sequence=1,
                        source_end_sequence=1,
                        summary="Compacted early transcript context.",
                        artifact_id=new_artifact_id(),
                        freshness=ContextCompactionFreshness.FRESH,
                    ),
                )
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                page_response = await client.get(
                    f"/sessions/{state.session_id}/compactions"
                )
                rejected_response = await client.post(
                    f"/sessions/{state.session_id}/compactions/"
                    f"{compaction_id}/invalidate",
                    json={
                        "reason": "operator rejected the summary",
                        "confirmed": False,
                    },
                )
                invalidate_response = await client.post(
                    f"/sessions/{state.session_id}/compactions/"
                    f"{compaction_id}/invalidate",
                    json={
                        "reason": "operator rejected the summary",
                        "confirmed": True,
                    },
                )
                page_after_response = await client.get(
                    f"/sessions/{state.session_id}/compactions"
                )

            assert page_response.status_code == 200
            assert page_response.json()["items"][0]["freshness"] == "fresh"
            assert rejected_response.status_code == 409
            assert invalidate_response.status_code == 200
            assert invalidate_response.json()["freshness"] == "invalidated"
            page_after_body = page_after_response.json()
            assert page_after_body["items"][0]["freshness"] == "invalidated"
            assert page_after_body["items"][0]["freshness_reason"] == (
                "operator rejected the summary"
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_session_compaction_refresh_rejects_over_cap_range_with_json_guidance(
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
            compaction_id = new_context_compaction_id()
            runtime_context.repositories.sessions.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=ContextCompactionCreated(
                        compaction_id=compaction_id,
                        scope=ContextCompactionScope.TRANSCRIPT,
                        source_start_sequence=1,
                        source_end_sequence=1,
                        summary="Compacted early transcript context.",
                        artifact_id=new_artifact_id(),
                        freshness=ContextCompactionFreshness.FRESH,
                    ),
                )
            )
            _append_runtime_notes(
                runtime_context.repositories.sessions,
                state.session_id,
                count=CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP + 5,
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                refresh_response = await client.post(
                    f"/sessions/{state.session_id}/compactions/{compaction_id}/refresh",
                    json={
                        "reason": "refresh with newer transcript context",
                        "confirmed": True,
                    },
                )

            assert refresh_response.status_code == 409
            detail = refresh_response.json()["detail"]
            assert detail["error"] == "source_range_exceeds_cap"
            assert (
                detail["source_reference_cap"]
                == CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP
            )
            assert detail["selected_event_count"] > (
                CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP
            )
            assert "Retry with a bounded range" in detail["message"]
            assert detail["suggested_ranges"][0]["label"] == "first"
            assert (
                detail["suggested_ranges"][0]["selected_event_count"]
                == CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP
            )
            assert detail["suggested_ranges"][1]["label"] == "latest"
            assert (
                detail["suggested_ranges"][1]["selected_event_count"]
                == CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_snapshot_exposes_autonomy_budget_posture(
    tmp_path: Path,
) -> None:
    """Snapshot exposes projected autonomy budget posture for operators."""

    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(runtime_context.repositories.sessions, bus)
            budget = default_budget_for_autonomy_mode(AutonomyMode.TEST_DRIVEN)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="on-request",
                autonomy_mode=AutonomyMode.TEST_DRIVEN,
                autonomy_budget=budget,
                autonomy_budget_preset="test-driven",
            )
            state = await supervisor.start_session(config)
            runtime_context.repositories.sessions.append_event(
                EventEnvelope(
                    session_id=state.session_id,
                    sequence=0,
                    payload=BudgetDecisionRecorded(
                        scope="session",
                        mode=AutonomyMode.TEST_DRIVEN,
                        budget=budget,
                        usage=AutonomyBudgetUsage(
                            steps=4,
                            tool_calls=6,
                            write_operations=2,
                            command_operations=1,
                            wall_clock_seconds=15,
                            unattended_seconds=120,
                            seconds_since_checkpoint=90,
                            retry_delay_seconds=20,
                            verification_attempts=1,
                            branch_attempts=0,
                            artifact_bytes=128,
                        ),
                        remaining=AutonomyBudgetRemaining(
                            steps=0,
                            tool_calls=2,
                            write_operations=1,
                            command_operations=0,
                            wall_clock_seconds=45,
                            unattended_seconds=780,
                            seconds_since_checkpoint=210,
                            retry_delay_seconds=100,
                            verification_attempts=1,
                            branch_attempts=0,
                            artifact_bytes=1024,
                        ),
                        decision="exhausted",
                        reason=AutonomyEscalationReason.BUDGET_EXHAUSTED,
                        limit_name="steps",
                        detail="step budget exhausted",
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
            assert body["budget_posture"]["mode"] == "test-driven"
            assert body["budget_posture"]["last_decision"] == "exhausted"
            assert body["budget_posture"]["last_reason"] == "budget_exhausted"
            assert body["budget_posture"]["last_limit_name"] == "steps"
            assert body["budget_posture"]["remaining"]["steps"] == 0
            assert body["budget_posture"]["unattended_remaining_seconds"] == 780
            assert body["budget_posture"]["next_checkpoint_due_in_seconds"] == 210
            assert body["budget_posture"]["retry_delay_remaining_seconds"] == 100
            assert body["budget_posture"]["quiet_window_policy"] == "allow"
            assert body["budget_posture"]["checkpoint_approval_required"] is False
            assert "on-request" in body["approval_behavior"]
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


def test_get_session_includes_artifact_backed_context(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app, runtime_context = _make_app(tmp_path, connection)
            repo = runtime_context.repositories.sessions
            artifact_repo = runtime_context.repositories.artifacts
            bus: EventBus[EventEnvelope] = runtime_context.infrastructure.event_bus
            supervisor = SessionSupervisor(repo, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )
            state = await supervisor.start_session(config)
            tool_call_id = new_tool_call_id()
            turn_id = new_turn_id()
            artifact_repo.record_text_artifact(
                state.session_id,
                turn_id,
                tool_call_id,
                PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
                json.dumps(
                    PytestFailureDigestArtifact(
                        target_paths=["tests/unit/test_context_builder.py"],
                        failure_count=1,
                        failing_tests=[
                            "tests/unit/test_context_builder.py::test_failure"
                        ],
                    ).model_dump(mode="json")
                ),
                suffix="json",
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["runtime_context"]["artifact_context"]["summaries"] == [
                {
                    "summary_kind": "pytest_failure_digest",
                    "provenance_class": "artifact_backed_summary",
                    "source_tool_name": "run_tests",
                    "artifact_kind": "context_pytest_failure_digest",
                    "artifact_path": body["runtime_context"]["artifact_context"][
                        "summaries"
                    ][0]["artifact_path"],
                    "summary": (
                        "1 failing test(s) for tests/unit/test_context_builder.py"
                    ),
                    "freshness": "fresh",
                    "target_paths": ["tests/unit/test_context_builder.py"],
                    "keyword_filter": None,
                    "failing_tests": [
                        "tests/unit/test_context_builder.py::test_failure"
                    ],
                    "failure_count": 1,
                    "error_count": 0,
                    "timed_out": False,
                    "inherited": False,
                    "source_tool_call_id": str(tool_call_id),
                }
            ]
            assert (
                body["runtime_context"]["artifact_context"]["additional_summary_count"]
                == 0
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
                        policy_outcome="approve",
                        policy_risk_level="workspace_write",
                        policy_source_kind="default",
                        policy_source_label="workspace_write",
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
            assert pending[0]["policy_outcome"] == "approve"
            assert pending[0]["policy_risk_level"] == "workspace_write"
            assert pending[0]["policy_source_kind"] == "default"
            assert pending[0]["policy_source_label"] == "workspace_write"
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
            assert runtime_context_body["working_set"] == {
                "items": [
                    {
                        "subject_kind": "note",
                        "subject": (
                            "[repo] README.md is the primary operator entrypoint"
                        ),
                        "summary": "runtime note",
                        "reasons": [
                            (
                                "runtime note [repo] README.md is the primary "
                                "operator entrypoint"
                            )
                        ],
                        "signal_types": ["runtime_note"],
                        "inherited": False,
                    }
                ],
                "additional_item_count": 0,
            }
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_includes_memory_and_repository_index_context(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        (tmp_path / "src").mkdir(exist_ok=True)
        (tmp_path / "src" / "sample.py").write_text(
            "class UsefulThing:\n    pass\n",
            encoding="utf-8",
        )
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "fixture"\n',
            encoding="utf-8",
        )
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
            memory_id = new_workspace_memory_id()
            repo.append_events(
                [
                    EventEnvelope(
                        session_id=state.session_id,
                        sequence=0,
                        payload=WorkspaceMemoryCreated(
                            memory_id=memory_id,
                            kind=WorkspaceMemoryKind.COMMAND,
                            content="Use uv run pytest for backend tests.",
                            summary="Backend tests use uv",
                            provenance=WorkspaceMemoryProvenance(
                                source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                                session_id=state.session_id,
                                source_sequence=1,
                            ),
                        ),
                    ),
                    EventEnvelope(
                        session_id=state.session_id,
                        sequence=0,
                        payload=WorkspaceMemoryConfirmed(memory_id=memory_id),
                    ),
                ]
            )
            build_and_write_repository_index(tmp_path)

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            runtime_context_body = response.json()["runtime_context"]
            assert runtime_context_body["workspace_memory"][0]["memory_id"] == str(
                memory_id
            )
            assert runtime_context_body["workspace_memory"][0]["provenance"] == {
                "source_type": "session_event",
                "source_label": None,
                "session_id": str(state.session_id),
                "source_sequence": 1,
                "task_id": None,
                "artifact_id": None,
                "tool_call_id": None,
            }
            assert runtime_context_body["additional_workspace_memory_count"] == 0
            assert runtime_context_body["repository_index"]["status"] == "fresh"
            assert runtime_context_body["repository_index"]["entry_count"] >= 2
            assert runtime_context_body["repository_index"]["items"]
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
                "runtime_context",
                "projection_health",
            }
            assert expected_keys <= body.keys()
            assert body["projection_health"]["state"] == "ok"
        finally:
            connection.close()

    asyncio.run(scenario())


def test_get_session_snapshot_reports_unavailable_projection_state(
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
            with connection:
                connection.execute("drop table session_state")

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/sessions/{state.session_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["projection_health"]["state"] == "unavailable"
            assert body["projection_health"]["degraded"] is True
            assert "projection read failed" in body["projection_health"]["detail"]
            assert body["transcript"] == []
            assert body["pending_approvals"] == []
            assert body["can_fork"] is False
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


def test_tool_attempt_retry_and_abandon_routes_require_confirmation_and_record_evidence(
    tmp_path: Path,
) -> None:
    """Tool-attempt recovery routes mutate only after explicit confirmation."""

    async def scenario() -> None:
        (tmp_path / "note.txt").write_text("hello\n", encoding="utf-8")
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
            retry_tool_call_id = new_tool_call_id()
            retry_attempt_id = new_tool_attempt_id()
            abandon_attempt_id = new_tool_attempt_id()
            repo.append_events(
                [
                    EventEnvelope(
                        session_id=state.session_id,
                        sequence=0,
                        payload=TurnStarted(
                            turn_id=turn_id,
                            trigger_message_id=new_message_id(),
                        ),
                    ),
                    EventEnvelope(
                        session_id=state.session_id,
                        sequence=0,
                        payload=ModelToolCallRequested(
                            turn_id=turn_id,
                            tool_call_id=retry_tool_call_id,
                            tool_name="read_file",
                            arguments_json=json.dumps({"path": "note.txt"}),
                            policy_outcome="allow",
                            policy_risk_level="read_only",
                            policy_source_kind="default",
                            policy_source_label="read_only",
                            policy_reason=(
                                "allowed: read-only tool within workspace scope"
                            ),
                        ),
                    ),
                    EventEnvelope(
                        session_id=state.session_id,
                        sequence=0,
                        payload=ToolAttemptHeartbeat(
                            tool_attempt_id=retry_attempt_id,
                            status=ToolAttemptStatus.FAILED,
                            turn_id=turn_id,
                            tool_call_id=retry_tool_call_id,
                            tool_name="read_file",
                            message="transient read failure",
                            safe_to_retry=True,
                            retry_classification=(
                                ToolAttemptRetryClassification.RETRYABLE
                            ),
                            retry_requires_approval=False,
                            retry_reason=(
                                "read-only tools do not mutate workspace state"
                            ),
                        ),
                    ),
                    EventEnvelope(
                        session_id=state.session_id,
                        sequence=0,
                        payload=ToolAttemptHeartbeat(
                            tool_attempt_id=abandon_attempt_id,
                            status=ToolAttemptStatus.STALE,
                            turn_id=turn_id,
                            tool_name="run_command",
                            message="heartbeat expired",
                            safe_to_retry=None,
                            retry_classification=ToolAttemptRetryClassification.UNKNOWN,
                            retry_requires_approval=True,
                            retry_reason="retry side effects are unknown",
                        ),
                    ),
                ]
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                unconfirmed = await client.post(
                    f"/sessions/{state.session_id}/tool-attempts/"
                    f"{retry_attempt_id}/retry",
                    json={"confirmed": False},
                )
                retry_response = await client.post(
                    f"/sessions/{state.session_id}/tool-attempts/"
                    f"{retry_attempt_id}/retry",
                    json={"confirmed": True, "reason": "route smoke"},
                )
                abandon_response = await client.post(
                    f"/sessions/{state.session_id}/tool-attempts/"
                    f"{abandon_attempt_id}/abandon",
                    json={
                        "confirmed": True,
                        "reason": "operator moved on",
                    },
                )

            assert unconfirmed.status_code == 409
            assert retry_response.status_code == 200
            retry_body = retry_response.json()
            assert retry_body["original_attempt"]["status"] == "retried"
            assert retry_body["retry_attempt"]["status"] == "succeeded"

            assert abandon_response.status_code == 200
            abandon_body = abandon_response.json()
            assert abandon_body["original_attempt"]["status"] == "abandoned"
            assert "operator moved on" in abandon_body["message"]
        finally:
            connection.close()

    asyncio.run(scenario())
