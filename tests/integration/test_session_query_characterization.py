"""Characterization coverage for the shared session-query boundary."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from glassbox.core import EventEnvelope, MessagePart, SessionConfig
from glassbox.core.events import (
    AssistantMessageCompleted,
    TurnCompleted,
    TurnStarted,
    UserMessageReceived,
)
from glassbox.core.ids import new_message_id, new_turn_id
from glassbox.runtime.bus import EventBus
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.supervisor import SessionSupervisor
from glassbox.store.repositories import (
    FilesystemArtifactRepository,
    SQLiteSessionRepository,
)
from glassbox.store.sqlite import initialize_database, open_database


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
