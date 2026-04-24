"""Integration tests for the session supervisor lifecycle service."""

import asyncio
import logging
import sqlite3
from pathlib import Path

import pytest

from glassbox.core import (
    EventEnvelope,
    MessagePart,
    RuntimeNoteRecorded,
    SessionConfig,
    SessionResumed,
    SessionStarted,
    SessionStatus,
    TranscriptMessageImported,
    TurnCompleted,
    TurnStarted,
    UserMessageReceived,
)
from glassbox.core.events import (
    ApprovalRequested,
    AssistantMessageCompleted,
    SessionCompleted,
)
from glassbox.core.ids import new_approval_id, new_message_id, new_turn_id
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


def test_session_supervisor_records_runtime_note_and_keeps_it_across_resume(
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

            async with bus.subscribe() as subscription:
                started_state = await supervisor.start_session(config)
                await subscription.get()

                assert repository.list_runtime_notes(started_state.session_id) == []

                await supervisor.record_runtime_note(
                    started_state.session_id,
                    category=" Operator ",
                    message=" Prefer concise output ",
                )
                note_event = await subscription.get()

                resumed_state = await supervisor.resume_session(
                    started_state.session_id
                )
                await subscription.get()

                notes = repository.list_runtime_notes(started_state.session_id)
        finally:
            connection.close()

        assert isinstance(note_event.payload, RuntimeNoteRecorded)
        assert note_event.payload.category == "operator"
        assert note_event.payload.message == "Prefer concise output"
        assert resumed_state.last_sequence == 3
        assert [
            (
                note.source_session_id,
                note.category,
                note.message,
                note.inherited,
            )
            for note in notes
        ] == [
            (
                started_state.session_id,
                "operator",
                "Prefer concise output",
                False,
            )
        ]

    asyncio.run(scenario())


def test_session_supervisor_emits_structured_runtime_logs(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
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

            with caplog.at_level(logging.INFO, logger="glassbox.runtime"):
                started_state = await supervisor.start_session(config)
                await supervisor.submit_user_message(
                    started_state.session_id,
                    "Inspect the repo",
                )
                await supervisor.stop_session(started_state.session_id)
        finally:
            connection.close()

    asyncio.run(scenario())

    events = {
        str(record.__dict__["runtime_event"]): record for record in caplog.records
    }
    assert "session_started" in events
    assert events["session_started"].__dict__["session_id"]
    assert events["session_started"].__dict__["model_name"] == "openai:gpt-5.4"
    assert events["session_started"].__dict__["approval_mode"] == "confirm"
    assert "user_message_submitted" in events
    assert events["user_message_submitted"].__dict__["text_length"] == len(
        "Inspect the repo"
    )
    assert "session_stopped" in events
    assert events["session_stopped"].__dict__["reason"] == "stopped"


def test_session_supervisor_resumes_awaiting_approval_session(
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

            async with bus.subscribe() as subscription:
                started_state = await supervisor.start_session(config)
                await subscription.get()  # SessionStarted

                approval_id = new_approval_id()
                repository.append_event(
                    EventEnvelope(
                        session_id=started_state.session_id,
                        sequence=0,
                        payload=ApprovalRequested(
                            approval_id=approval_id,
                            turn_id=new_turn_id(),
                            reason="needs operator sign-off",
                            subject="apply_patch",
                        ),
                    )
                )

                resumed_state = await supervisor.resume_session(
                    started_state.session_id,
                )
                resumed_event = await subscription.get()
        finally:
            connection.close()

        assert isinstance(resumed_event.payload, SessionResumed)
        assert resumed_state.status == SessionStatus.AWAITING_APPROVAL
        assert resumed_state.pending_approval_id == approval_id

    asyncio.run(scenario())


def test_session_supervisor_rejects_resuming_completed_session(
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
            repository.append_event(
                EventEnvelope(
                    session_id=started_state.session_id,
                    sequence=0,
                    payload=SessionCompleted(reason="done"),
                )
            )

            with pytest.raises(ValueError, match="cannot resume session"):
                await supervisor.resume_session(started_state.session_id)
        finally:
            connection.close()

    asyncio.run(scenario())


def test_session_supervisor_forks_child_session_from_completed_turn(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            supervisor = SessionSupervisor(repository, EventBus())
            parent_config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            parent_state = await supervisor.start_session(parent_config)
            prompt_message_id = new_message_id()
            turn_id = new_turn_id()
            assistant_message_id = new_message_id()
            repository.append_events(
                [
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=UserMessageReceived(
                            message_id=prompt_message_id,
                            text="Inspect the repo",
                        ),
                    ),
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=TurnStarted(
                            turn_id=turn_id,
                            trigger_message_id=prompt_message_id,
                        ),
                    ),
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=AssistantMessageCompleted(
                            message_id=assistant_message_id,
                            parts=[
                                MessagePart(
                                    kind="text",
                                    text="I received your request: Inspect the repo",
                                )
                            ],
                        ),
                    ),
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=TurnCompleted(
                            turn_id=turn_id,
                            outcome="completed",
                        ),
                    ),
                ]
            )

            parent_events_before = repository.read_session_events(
                parent_state.session_id
            )
            forked_session = await supervisor.fork_session(
                parent_state.session_id,
                turn_id=turn_id,
                branch_label="investigate-alt-path",
            )
            child_session = repository.get_session(forked_session.child_session_id)
            child_events = repository.read_session_events(
                forked_session.child_session_id
            )
            child_transcript = repository.list_transcript_messages(
                forked_session.child_session_id
            )
            parent_events_after = repository.read_session_events(
                parent_state.session_id
            )
        finally:
            connection.close()

        assert child_session is not None
        assert child_session.parent_session_id == parent_state.session_id
        assert child_session.forked_from_turn_id == turn_id
        assert child_session.forked_from_sequence == 5
        assert child_session.branch_label == "investigate-alt-path"
        assert forked_session.parent_session_id == parent_state.session_id
        assert forked_session.forked_from_turn_id == turn_id
        assert forked_session.inherited_message_count == 2
        assert forked_session.last_sequence == 3
        assert [event.event_type for event in child_events] == [
            "SessionStarted",
            "TranscriptMessageImported",
            "TranscriptMessageImported",
        ]
        assert isinstance(child_events[0].payload, SessionStarted)
        assert child_events[0].payload.parent_session_id == parent_state.session_id
        assert isinstance(child_events[1].payload, TranscriptMessageImported)
        assert [message.parts[0].text for message in child_transcript] == [
            "Inspect the repo",
            "I received your request: Inspect the repo",
        ]
        assert len(parent_events_before) == len(parent_events_after)

    asyncio.run(scenario())


def test_session_supervisor_runtime_notes_are_inherited_by_child_queries(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            supervisor = SessionSupervisor(repository, EventBus())
            parent_config = SessionConfig(
                model_name="openai:gpt-5.4",
                cwd=tmp_path,
                approval_mode="confirm",
            )

            parent_state = await supervisor.start_session(parent_config)
            await supervisor.record_runtime_note(
                parent_state.session_id,
                category="operator",
                message="Stay inside src/glassbox",
            )

            prompt_message_id = new_message_id()
            turn_id = new_turn_id()
            repository.append_events(
                [
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=UserMessageReceived(
                            message_id=prompt_message_id,
                            text="Inspect the repo",
                        ),
                    ),
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=TurnStarted(
                            turn_id=turn_id,
                            trigger_message_id=prompt_message_id,
                        ),
                    ),
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=TurnCompleted(
                            turn_id=turn_id,
                            outcome="completed",
                        ),
                    ),
                ]
            )

            forked_session = await supervisor.fork_session(parent_state.session_id)
            await supervisor.record_runtime_note(
                forked_session.child_session_id,
                category="runtime",
                message="Child branch prefers narrow diffs",
            )

            inherited_notes = repository.list_runtime_notes(
                forked_session.child_session_id
            )
            local_notes = repository.list_runtime_notes(
                forked_session.child_session_id,
                include_inherited=False,
            )
        finally:
            connection.close()

        assert [
            (
                note.source_session_id,
                note.category,
                note.message,
                note.inherited,
            )
            for note in inherited_notes
        ] == [
            (
                parent_state.session_id,
                "operator",
                "Stay inside src/glassbox",
                True,
            ),
            (
                forked_session.child_session_id,
                "runtime",
                "Child branch prefers narrow diffs",
                False,
            ),
        ]
        assert [
            (
                note.source_session_id,
                note.category,
                note.message,
                note.inherited,
            )
            for note in local_notes
        ] == [
            (
                forked_session.child_session_id,
                "runtime",
                "Child branch prefers narrow diffs",
                False,
            )
        ]

    asyncio.run(scenario())


def test_forked_child_runtime_notes_are_snapshotted_at_fork_time(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        try:
            repository = SQLiteSessionRepository(connection)
            supervisor = SessionSupervisor(repository, EventBus())
            parent_state = await supervisor.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await supervisor.record_runtime_note(
                parent_state.session_id,
                category="operator",
                message="Stay inside src/glassbox",
            )

            prompt_message_id = new_message_id()
            turn_id = new_turn_id()
            repository.append_events(
                [
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=UserMessageReceived(
                            message_id=prompt_message_id,
                            text="Inspect the repo",
                        ),
                    ),
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=TurnStarted(
                            turn_id=turn_id,
                            trigger_message_id=prompt_message_id,
                        ),
                    ),
                    EventEnvelope(
                        session_id=parent_state.session_id,
                        sequence=0,
                        payload=TurnCompleted(
                            turn_id=turn_id,
                            outcome="completed",
                        ),
                    ),
                ]
            )

            forked_session = await supervisor.fork_session(parent_state.session_id)
            await supervisor.record_runtime_note(
                parent_state.session_id,
                category="operator",
                message="Parent note added after fork",
            )

            child_notes = repository.list_runtime_notes(forked_session.child_session_id)
            child_local_notes = repository.list_runtime_notes(
                forked_session.child_session_id,
                include_inherited=False,
            )
        finally:
            connection.close()

        assert [
            (note.category, note.message, note.inherited) for note in child_notes
        ] == [("operator", "Stay inside src/glassbox", True)]
        assert child_local_notes == []

    asyncio.run(scenario())


def test_session_supervisor_rejects_resuming_in_flight_turn_after_restart(
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
            turn_id = new_turn_id()
            repository.append_event(
                EventEnvelope(
                    session_id=started_state.session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=new_turn_id(),
                    ),
                )
            )

            with pytest.raises(ValueError, match="in-flight turn"):
                await supervisor.resume_session(started_state.session_id)
        finally:
            connection.close()

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
