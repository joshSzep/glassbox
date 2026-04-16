"""Integration tests for the session supervisor lifecycle service."""

import asyncio
import sqlite3
from pathlib import Path

import pytest

from glassbox.core import (
    EventEnvelope,
    SessionConfig,
    SessionResumed,
    SessionStarted,
    SessionStatus,
    UserMessageReceived,
)
from glassbox.runtime import EventBus, SessionSupervisor
from glassbox.store import SQLiteSessionRepository, initialize_database, open_database


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def test_session_supervisor_starts_and_resumes_session(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = EventBus()
            supervisor = SessionSupervisor(repository, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            async with bus.subscribe() as subscription:
                started_state = await supervisor.start_session(config)
                started_event = await subscription.get()
                resumed_state = await supervisor.resume_session(
                    started_state.session_id,
                )
                resumed_event = await subscription.get()
        finally:
            connection.close()

        assert isinstance(started_event.payload, SessionStarted)
        assert started_state.status == SessionStatus.RUNNING
        assert started_state.last_sequence == 1
        assert isinstance(resumed_event.payload, SessionResumed)
        assert resumed_event.payload.from_sequence == 1
        assert resumed_state.status == SessionStatus.RUNNING
        assert resumed_state.last_sequence == 2

    asyncio.run(scenario())


def test_session_supervisor_submits_user_message_and_stops_session(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            bus: EventBus[EventEnvelope] = EventBus()
            supervisor = SessionSupervisor(repository, bus)
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            started_state = await supervisor.start_session(config)
            await supervisor.submit_user_message(
                started_state.session_id,
                "Inspect the repo",
            )
            stopped_state = await supervisor.stop_session(started_state.session_id)
            persisted_events = repository.read_session_events(started_state.session_id)
        finally:
            connection.close()

        assert [event.event_type for event in persisted_events] == [
            "SessionStarted",
            "UserMessageReceived",
            "SessionCompleted",
        ]
        assert isinstance(persisted_events[1].payload, UserMessageReceived)
        assert persisted_events[1].payload.text == "Inspect the repo"
        assert stopped_state.status == SessionStatus.COMPLETED
        assert stopped_state.last_sequence == 3

    asyncio.run(scenario())


def test_session_supervisor_rejects_input_into_completed_session(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            supervisor = SessionSupervisor(repository, EventBus())
            config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            started_state = await supervisor.start_session(config)
            await supervisor.stop_session(started_state.session_id)
            with pytest.raises(ValueError):
                await supervisor.submit_user_message(
                    started_state.session_id,
                    "Too late",
                )
        finally:
            connection.close()

    asyncio.run(scenario())
