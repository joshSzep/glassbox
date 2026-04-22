"""Integration tests for the turn metrics projection (GBX-110)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from glassbox.core import EventEnvelope, SessionStarted
from glassbox.core.events import (
    ModelCallCompleted,
    ModelCallStarted,
    ToolExecutionCompleted,
    ToolExecutionStarted,
    TurnCompleted,
    TurnStarted,
)
from glassbox.core.ids import new_session_id, new_tool_call_id, new_turn_id
from glassbox.store import SQLiteSessionRepository, initialize_database, open_database


def test_turn_metrics_projection_aggregates_model_tokens_and_durations(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)

    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    created_at=datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC),
                    payload=SessionStarted(
                        cwd=str(tmp_path),
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    created_at=datetime(2026, 4, 21, 12, 0, 1, tzinfo=UTC),
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=new_turn_id(),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    created_at=datetime(2026, 4, 21, 12, 0, 2, tzinfo=UTC),
                    payload=ModelCallStarted(
                        turn_id=turn_id,
                        provider="openai",
                        model_name="gpt-5.4",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    created_at=datetime(2026, 4, 21, 12, 0, 3, tzinfo=UTC),
                    payload=ModelCallCompleted(
                        turn_id=turn_id,
                        input_tokens=120,
                        output_tokens=45,
                        duration_ms=850,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    created_at=datetime(2026, 4, 21, 12, 0, 4, tzinfo=UTC),
                    payload=ModelCallCompleted(
                        turn_id=turn_id,
                        input_tokens=30,
                        output_tokens=15,
                        duration_ms=150,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    created_at=datetime(2026, 4, 21, 12, 0, 5, tzinfo=UTC),
                    payload=ToolExecutionStarted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="read_file",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    created_at=datetime(2026, 4, 21, 12, 0, 7, tzinfo=UTC),
                    payload=ToolExecutionCompleted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        success=True,
                        summary="done",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    created_at=datetime(2026, 4, 21, 12, 0, 9, tzinfo=UTC),
                    payload=TurnCompleted(
                        turn_id=turn_id,
                        outcome="completed",
                    ),
                ),
            ]
        )

        metrics = repository.list_turn_metrics(session_id)
    finally:
        connection.close()

    assert len(metrics) == 1
    assert metrics[0].turn_id == turn_id
    assert metrics[0].model_call_count == 2
    assert metrics[0].model_duration_ms_total == 1000
    assert metrics[0].model_input_tokens_total == 150
    assert metrics[0].model_output_tokens_total == 60
    assert metrics[0].tool_call_count == 1
    assert metrics[0].tool_duration_ms_total == 2000
    assert metrics[0].succeeded_tool_call_count == 1
    assert metrics[0].failed_tool_call_count == 0
    assert metrics[0].turn_duration_ms == 8000
