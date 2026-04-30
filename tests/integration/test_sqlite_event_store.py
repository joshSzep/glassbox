"""Integration tests for the canonical SQLite event store."""

import sqlite3
from pathlib import Path

import pytest

from glassbox.core import EventEnvelope
from glassbox.core import LongRunPhase
from glassbox.core import LongRunPhaseChanged
from glassbox.core import LongRunPhaseState
from glassbox.core import SessionStarted
from glassbox.core import TaskCheckpointCreated
from glassbox.core import ToolAttemptHeartbeat
from glassbox.core import ToolAttemptStatus
from glassbox.core import ToolExecutionCompleted
from glassbox.core import TurnStarted
from glassbox.core import TurnStatus
from glassbox.core import TurnStatusChanged
from glassbox.core import UserMessageReceived
from glassbox.core import new_event_id
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_tool_attempt_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.store.sqlite import append_event
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.store.sqlite import read_events_by_correlation_id
from glassbox.store.sqlite import read_session_events
from glassbox.store.sqlite import read_session_events_after
from glassbox.store.sqlite import rebuild_session_projections


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def test_append_events_assigns_monotonic_sequences_and_replays_in_order(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    message_id = new_message_id()
    turn_id = new_turn_id()
    connection = _open_initialized_database(tmp_path)
    try:
        stored_events = append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=UserMessageReceived(
                        message_id=message_id,
                        text="inspect the repository",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=message_id,
                    ),
                ),
            ],
        )
        replayed_events = read_session_events(connection, session_id)
        last_sequence = connection.execute(
            "select last_sequence from sessions where session_id = ?",
            (str(session_id),),
        ).fetchone()[0]
    finally:
        connection.close()

    assert [event.sequence for event in stored_events] == [1, 2, 3]
    assert [event.sequence for event in replayed_events] == [1, 2, 3]
    assert replayed_events[1].message_id == message_id
    assert last_sequence == 3


def test_append_event_rejects_duplicate_event_id(tmp_path: Path) -> None:
    session_id = new_session_id()
    duplicate_event_id = new_event_id()
    connection = _open_initialized_database(tmp_path)
    try:
        append_event(
            connection,
            EventEnvelope(
                event_id=duplicate_event_id,
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd="/tmp/glassbox",
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            ),
        )

        with pytest.raises(sqlite3.IntegrityError):
            append_event(
                connection,
                EventEnvelope(
                    event_id=duplicate_event_id,
                    session_id=session_id,
                    sequence=0,
                    payload=UserMessageReceived(
                        message_id=new_message_id(),
                        text="duplicate id",
                    ),
                ),
            )
    finally:
        connection.close()


def test_read_session_events_after_returns_only_newer_events(tmp_path: Path) -> None:
    session_id = new_session_id()
    message_id = new_message_id()
    turn_id = new_turn_id()
    connection = _open_initialized_database(tmp_path)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=UserMessageReceived(
                        message_id=message_id,
                        text="inspect the repository",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=message_id,
                    ),
                ),
            ],
        )
        tail_events = read_session_events_after(
            connection,
            session_id,
            after_sequence=1,
        )
    finally:
        connection.close()

    assert [event.sequence for event in tail_events] == [2, 3]
    assert [event.event_type for event in tail_events] == [
        "UserMessageReceived",
        "TurnStarted",
    ]


def test_read_events_by_correlation_id_returns_matching_events(tmp_path: Path) -> None:
    session_id = new_session_id()
    message_id = new_message_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    connection = _open_initialized_database(tmp_path)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=UserMessageReceived(
                        message_id=message_id,
                        text="inspect the repository",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=message_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStatusChanged(
                        turn_id=turn_id,
                        status=TurnStatus.EXECUTING_TOOL,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionCompleted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        success=True,
                        summary="completed",
                    ),
                ),
            ],
        )
        turn_events = read_events_by_correlation_id(
            connection,
            session_id,
            turn_id=turn_id,
        )
    finally:
        connection.close()

    assert [event.event_type for event in turn_events] == [
        "TurnStarted",
        "TurnStatusChanged",
        "ToolExecutionCompleted",
    ]


def test_long_run_events_persist_correlations_and_rebuild_projection(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    message_id = new_message_id()
    turn_id = new_turn_id()
    task_id = new_task_id()
    checkpoint_id = new_task_checkpoint_id()
    tool_attempt_id = new_tool_attempt_id()
    tool_call_id = new_tool_call_id()
    connection = _open_initialized_database(tmp_path)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=message_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=LongRunPhaseChanged(
                        phase=LongRunPhase.TOOL_EXECUTION,
                        state=LongRunPhaseState.ENTERED,
                        task_id=task_id,
                        turn_id=turn_id,
                        tool_attempt_id=tool_attempt_id,
                        reason="running focused tests",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskCheckpointCreated(
                        checkpoint_id=checkpoint_id,
                        task_id=task_id,
                        turn_id=turn_id,
                        tool_attempt_id=tool_attempt_id,
                        objective="complete GBX-1010",
                        completed_step="added event models",
                        next_action="verify SQLite projection",
                        recovery_guidance="resume with the focused event-store test",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolAttemptHeartbeat(
                        tool_attempt_id=tool_attempt_id,
                        status=ToolAttemptStatus.RUNNING,
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        task_id=task_id,
                        tool_name="pytest",
                        message="tests still running",
                    ),
                ),
            ],
        )
        task_events = read_events_by_correlation_id(
            connection,
            session_id,
            task_id=task_id,
        )
        checkpoint_events = read_events_by_correlation_id(
            connection,
            session_id,
            checkpoint_id=checkpoint_id,
        )
        projected_before = connection.execute(
            """
            select event_type, task_id, turn_id, tool_attempt_id, checkpoint_id,
                   phase, status, summary
            from long_run_events
            where session_id = ?
            order by sequence
            """,
            (str(session_id),),
        ).fetchall()
        connection.execute(
            "delete from long_run_events where session_id = ?",
            (str(session_id),),
        )
        rebuild_session_projections(connection, session_id)
        projected_after = connection.execute(
            """
            select event_type, task_id, turn_id, tool_attempt_id, checkpoint_id,
                   phase, status, summary
            from long_run_events
            where session_id = ?
            order by sequence
            """,
            (str(session_id),),
        ).fetchall()
    finally:
        connection.close()

    assert [event.event_type for event in task_events] == [
        "LongRunPhaseChanged",
        "TaskCheckpointCreated",
        "ToolAttemptHeartbeat",
    ]
    assert [event.event_type for event in checkpoint_events] == [
        "TaskCheckpointCreated"
    ]
    assert [tuple(row) for row in projected_after] == [
        tuple(row) for row in projected_before
    ]
    assert projected_after[0]["phase"] == "tool_execution"
    assert projected_after[0]["status"] == "entered"
    assert projected_after[1]["checkpoint_id"] == str(checkpoint_id)
    assert projected_after[2]["summary"] == "tests still running"


def test_read_events_by_correlation_id_requires_exactly_one_filter(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    connection = _open_initialized_database(tmp_path)
    try:
        with pytest.raises(ValueError):
            read_events_by_correlation_id(connection, session_id)
    finally:
        connection.close()
