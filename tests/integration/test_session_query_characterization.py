"""Characterization coverage for the shared session-query boundary."""

import asyncio
import sqlite3
from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import EventEnvelope
from glassbox.core import MessagePart
from glassbox.core import SessionConfig
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import RecoveryDecisionRecorded
from glassbox.core.events import SessionCompleted
from glassbox.core.events import ToolAttemptHeartbeat
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_recovery_decision_id
from glassbox.core.ids import new_tool_attempt_id
from glassbox.core.ids import new_turn_id
from glassbox.core.types import RecoveryDecision
from glassbox.core.types import ToolAttemptStatus
from glassbox.runtime.bus import EventBus
from glassbox.runtime.context_builder import TurnContextBuilder
from glassbox.runtime.context_formatting import format_repository_context_for_prompt
from glassbox.runtime.context_formatting import format_runtime_notes_for_prompt
from glassbox.runtime.runtime_context_derivation import derive_runtime_context_snapshot
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import WorkspaceRuntimeSummaryView
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


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
            payload=TurnCompleted(turn_id=turn_id, outcome="completed"),
        )
    )
    return turn_id


def test_session_query_service_preserves_snapshot_shape_for_cli_and_web(
    tmp_path: Path,
) -> None:
    """Refactor-sensitive snapshot fields stay shaped at the shared query seam."""

    async def scenario() -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "docs").mkdir()
        (tmp_path / "README.md").write_text("# Glassbox\n", encoding="utf-8")

        connection = _open_initialized_db(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifacts = FilesystemArtifactRepository(connection, tmp_path)
            query_service = SessionQueryService(repository, artifacts)
            bus: EventBus[EventEnvelope] = EventBus()
            supervisor = SessionSupervisor(repository, bus)

            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.record_runtime_note(
                parent_state.session_id,
                category="repo",
                message="README is the operator entrypoint",
            )
            turn_id = _append_completed_turn(
                repository,
                parent_state.session_id,
                user_text="Inspect the repository",
                assistant_text="I received your request: Inspect the repository",
            )
            forked_session = await supervisor.fork_session(
                parent_state.session_id,
                branch_label="alt-path",
            )

            snapshot = query_service.get_session_snapshot(parent_state.session_id)
            status_view = query_service.get_session_status_view(parent_state.session_id)

            assert snapshot.session_id == parent_state.session_id
            assert snapshot.can_fork is True
            assert snapshot.branchable_turns[0].turn_id == turn_id
            assert snapshot.child_sessions[0].session_id == (
                forked_session.child_session_id
            )
            assert snapshot.runtime_context.repository_context.workspace_name == (
                tmp_path.name
            )
            assert "README.md" in (
                snapshot.runtime_context.repository_context.high_signal_paths
            )
            assert snapshot.runtime_context.runtime_notes[0].message == (
                "README is the operator entrypoint"
            )
            assert status_view.snapshot == snapshot
            assert status_view.latest_message_summary == (
                "assistant: I received your request: Inspect the repository"
            )
            assert status_view.effective_current_turn_id is None
        finally:
            connection.close()

    asyncio.run(scenario())


def test_session_query_surfaces_non_resumable_turn_recovery_posture(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifacts = FilesystemArtifactRepository(connection, tmp_path)
            query_service = SessionQueryService(repository, artifacts)
            supervisor = SessionSupervisor(repository, EventBus())

            session_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            turn_id = new_turn_id()
            repository.append_event(
                EventEnvelope(
                    session_id=session_state.session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=new_message_id(),
                    ),
                )
            )
            repository.append_event(
                EventEnvelope(
                    session_id=session_state.session_id,
                    sequence=0,
                    payload=RecoveryDecisionRecorded(
                        recovery_decision_id=new_recovery_decision_id(),
                        decision=RecoveryDecision.NON_RESUMABLE,
                        reason="provider stream was interrupted after restart",
                        safe_to_resume=False,
                        next_action="Retry with a new prompt or fork",
                        turn_id=turn_id,
                    ),
                )
            )

            summary = query_service.list_session_summaries()[0]
            snapshot = query_service.get_session_snapshot(session_state.session_id)
        finally:
            connection.close()

        assert summary.turn_recovery_posture is not None
        assert summary.turn_recovery_posture.state == "non_resumable"
        assert summary.next_action_summary == "Retry with a new prompt or fork"
        assert snapshot.turn_recovery_posture == summary.turn_recovery_posture

    asyncio.run(scenario())


def test_session_query_derives_long_run_status_from_durable_progress(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifacts = FilesystemArtifactRepository(connection, tmp_path)
            query_service = SessionQueryService(repository, artifacts)
            supervisor = SessionSupervisor(repository, EventBus())

            healthy = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            stale = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            stuck = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            paused = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            completed = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )

            _append_attempt(
                repository,
                healthy.session_id,
                status=ToolAttemptStatus.RUNNING,
                heartbeat_expires_at=datetime(2099, 1, 1, tzinfo=UTC),
                message="pytest still running",
            )
            _append_attempt(
                repository,
                stale.session_id,
                status=ToolAttemptStatus.RUNNING,
                heartbeat_expires_at=datetime(2000, 1, 1, tzinfo=UTC),
                message="pytest heartbeat",
            )
            _append_attempt(
                repository,
                stuck.session_id,
                status=ToolAttemptStatus.STALE,
                heartbeat_expires_at=datetime(2000, 1, 1, tzinfo=UTC),
                message="pytest stopped heartbeating",
            )
            _append_attempt(
                repository,
                paused.session_id,
                status=ToolAttemptStatus.WAITING,
                heartbeat_expires_at=datetime(2099, 1, 1, tzinfo=UTC),
                message="waiting for operator",
            )
            repository.append_event(
                EventEnvelope(
                    session_id=completed.session_id,
                    sequence=0,
                    payload=SessionCompleted(reason="finished"),
                )
            )

            summaries = {
                summary.session_id: summary
                for summary in query_service.list_session_summaries()
            }
            operator_rows = {
                row.session_id: row
                for row in query_service.get_session_aggregate(
                    runtime=WorkspaceRuntimeSummaryView(
                        workspace_root=str(tmp_path),
                        state="running",
                    )
                ).sessions
            }
            healthy_snapshot = query_service.get_session_snapshot(healthy.session_id)
        finally:
            connection.close()

        assert summaries[healthy.session_id].long_run_status.state == "healthy"
        assert summaries[healthy.session_id].long_run_status.current_attempt_tool_name
        assert operator_rows[healthy.session_id].has_active_turn is True
        assert healthy_snapshot.long_run_status == (
            summaries[healthy.session_id].long_run_status
        )
        assert summaries[stale.session_id].long_run_status.state == "stale"
        assert operator_rows[stale.session_id].action_needed is True
        assert summaries[stuck.session_id].long_run_status.state == "stuck"
        assert summaries[stuck.session_id].long_run_status.stuck_reason == (
            "tool attempt is stale"
        )
        assert summaries[paused.session_id].long_run_status.state == "paused"
        assert summaries[completed.session_id].long_run_status.state == "completed"

    asyncio.run(scenario())


def _append_attempt(
    repo: SQLiteSessionRepository,
    session_id,
    *,
    status: ToolAttemptStatus,
    heartbeat_expires_at: datetime,
    message: str,
) -> None:
    turn_id = new_turn_id()
    repo.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=TurnStarted(
                turn_id=turn_id,
                trigger_message_id=new_message_id(),
            ),
        )
    )
    repo.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=ToolAttemptHeartbeat(
                tool_attempt_id=new_tool_attempt_id(),
                status=status,
                turn_id=turn_id,
                tool_name="pytest",
                message=message,
                heartbeat_expires_at=heartbeat_expires_at,
            ),
        )
    )


def test_session_query_and_turn_context_share_runtime_context_derivation(
    tmp_path: Path,
) -> None:
    """Session snapshots and prompt-context assembly adapt the same structure."""

    async def scenario() -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "README.md").write_text("# Glassbox\n", encoding="utf-8")

        connection = _open_initialized_db(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            artifacts = FilesystemArtifactRepository(connection, tmp_path)
            query_service = SessionQueryService(repository, artifacts)
            bus: EventBus[EventEnvelope] = EventBus()
            supervisor = SessionSupervisor(repository, bus)

            session_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.record_runtime_note(
                session_state.session_id,
                category="repo",
                message="Keep session snapshots and prompt context aligned",
            )

            runtime_context = derive_runtime_context_snapshot(
                repository,
                session_state.session_id,
                tmp_path,
                artifact_repository=artifacts,
            )
            snapshot = query_service.get_session_snapshot(session_state.session_id)
            turn_context = TurnContextBuilder(repository).build_from_runtime_context(
                session_state.session_id,
                runtime_context,
            )

            assert snapshot.runtime_context == runtime_context
            assert turn_context.repo_context == format_repository_context_for_prompt(
                runtime_context.repository_context
            )
            assert turn_context.repository_index is None
            assert turn_context.memory_notes == format_runtime_notes_for_prompt(
                runtime_context.runtime_notes
            )
        finally:
            connection.close()

    asyncio.run(scenario())
