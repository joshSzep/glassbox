"""Integration tests for SQLite projection handlers and rebuilds."""

import sqlite3
from pathlib import Path

from glassbox.core import ApprovalDecision
from glassbox.core import ApprovalRequested
from glassbox.core import ApprovalResolved
from glassbox.core import AssistantMessageCompleted
from glassbox.core import AssistantMessageDelta
from glassbox.core import AssistantMessageStarted
from glassbox.core import EventEnvelope
from glassbox.core import MessagePart
from glassbox.core import ModelToolCallRequested
from glassbox.core import RuntimeNoteRecorded
from glassbox.core import SessionStarted
from glassbox.core import ToolExecutionCompleted
from glassbox.core import ToolExecutionStarted
from glassbox.core import TurnCompleted
from glassbox.core import TurnStarted
from glassbox.core import UserMessageReceived
from glassbox.core import new_approval_id
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import list_runtime_notes
from glassbox.store.sqlite import open_database
from glassbox.store.sqlite import rebuild_session_projections


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _projection_snapshot(
    connection: sqlite3.Connection,
    session_id: str,
) -> dict[str, list[tuple]]:
    return {
        "session_state": [
            tuple(row)
            for row in connection.execute(
                """
                select status, current_turn_id, pending_approval_id, last_sequence
                from session_state
                where session_id = ?
                """,
                (session_id,),
            ).fetchall()
        ],
        "transcript_messages": [
            tuple(row)
            for row in connection.execute(
                """
                select message_id, role, status, content_text
                from transcript_messages
                where session_id = ?
                order by created_at asc
                """,
                (session_id,),
            ).fetchall()
        ],
        "tool_calls": [
            tuple(row)
            for row in connection.execute(
                """
                select
                    tool_call_id,
                    tool_name,
                    status,
                    summary,
                    exit_code,
                    policy_outcome,
                    policy_risk_level,
                    policy_source_kind,
                    policy_source_label,
                    policy_reason
                from tool_calls
                where session_id = ?
                """,
                (session_id,),
            ).fetchall()
        ],
        "approvals": [
            tuple(row)
            for row in connection.execute(
                """
                select
                    approval_id,
                    status,
                    decided_by,
                    policy_outcome,
                    policy_risk_level,
                    policy_source_kind,
                    policy_source_label
                from approvals
                where session_id = ?
                """,
                (session_id,),
            ).fetchall()
        ],
    }


def test_append_events_updates_projection_tables(tmp_path: Path) -> None:
    session_id = new_session_id()
    user_message_id = new_message_id()
    assistant_message_id = new_message_id()
    turn_id = new_turn_id()
    tool_call_id = new_tool_call_id()
    approval_id = new_approval_id()
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
                        message_id=user_message_id,
                        text="inspect the repository",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=user_message_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=AssistantMessageStarted(message_id=assistant_message_id),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=AssistantMessageDelta(
                        message_id=assistant_message_id,
                        delta="Inspecting",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ModelToolCallRequested(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="read_file",
                        arguments_json="{}",
                        policy_outcome="allow",
                        policy_risk_level="read_only",
                        policy_source_kind="default",
                        policy_source_label="read_only",
                        policy_reason="allowed: read-only tool within workspace scope",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionStarted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="read_file",
                        policy_outcome="allow",
                        policy_risk_level="read_only",
                        policy_source_kind="default",
                        policy_source_label="read_only",
                        policy_reason="allowed: read-only tool within workspace scope",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ApprovalRequested(
                        approval_id=approval_id,
                        turn_id=turn_id,
                        reason="Need permission",
                        subject="read_file",
                        policy_outcome="approve",
                        policy_risk_level="workspace_write",
                        policy_source_kind="default",
                        policy_source_label="workspace_write",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ApprovalResolved(
                        approval_id=approval_id,
                        decision=ApprovalDecision.APPROVED,
                        decided_by="user",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionCompleted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        success=True,
                        exit_code=0,
                        summary="read complete",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=AssistantMessageCompleted(
                        message_id=assistant_message_id,
                        parts=[MessagePart(kind="text", text="Inspecting complete")],
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnCompleted(
                        turn_id=turn_id,
                        outcome="completed",
                    ),
                ),
            ],
        )

        session_state_row = connection.execute(
            """
            select status, current_turn_id, pending_approval_id, last_sequence
            from session_state
            where session_id = ?
            """,
            (str(session_id),),
        ).fetchone()
        transcript_rows = connection.execute(
            """
            select role, status, content_text
            from transcript_messages
            where session_id = ?
            order by created_at asc
            """,
            (str(session_id),),
        ).fetchall()
        tool_call_row = connection.execute(
            """
            select
                tool_name,
                status,
                summary,
                exit_code,
                policy_outcome,
                policy_risk_level,
                policy_source_kind,
                policy_source_label,
                policy_reason
            from tool_calls
            where tool_call_id = ?
            """,
            (str(tool_call_id),),
        ).fetchone()
        approval_row = connection.execute(
            """
            select
                status,
                decided_by,
                policy_outcome,
                policy_risk_level,
                policy_source_kind,
                policy_source_label
            from approvals
            where approval_id = ?
            """,
            (str(approval_id),),
        ).fetchone()
    finally:
        connection.close()

    assert tuple(session_state_row) == ("running", None, None, 12)
    assert [tuple(row) for row in transcript_rows] == [
        ("user", "completed", "inspect the repository"),
        ("assistant", "completed", "Inspecting complete"),
    ]
    assert tuple(tool_call_row) == (
        "read_file",
        "succeeded",
        "read complete",
        0,
        "allow",
        "read_only",
        "default",
        "read_only",
        "allowed: read-only tool within workspace scope",
    )
    assert tuple(approval_row) == (
        "approved",
        "user",
        "approve",
        "workspace_write",
        "default",
        "workspace_write",
    )


def test_rebuild_session_projections_reproduces_projection_state(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    user_message_id = new_message_id()
    assistant_message_id = new_message_id()
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
                        message_id=user_message_id,
                        text="inspect the repository",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=user_message_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=AssistantMessageStarted(message_id=assistant_message_id),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=AssistantMessageDelta(
                        message_id=assistant_message_id,
                        delta="Inspecting",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ModelToolCallRequested(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="read_file",
                        arguments_json="{}",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionStarted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="read_file",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionCompleted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        success=True,
                        exit_code=0,
                        summary="read complete",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=AssistantMessageCompleted(
                        message_id=assistant_message_id,
                        parts=[MessagePart(kind="text", text="Inspecting complete")],
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnCompleted(
                        turn_id=turn_id,
                        outcome="completed",
                    ),
                ),
            ],
        )
        before_rebuild = _projection_snapshot(connection, str(session_id))
        connection.execute(
            "delete from session_state where session_id = ?",
            (str(session_id),),
        )
        connection.execute(
            "delete from transcript_messages where session_id = ?",
            (str(session_id),),
        )
        connection.execute(
            "delete from tool_calls where session_id = ?",
            (str(session_id),),
        )
        connection.execute(
            "delete from approvals where session_id = ?",
            (str(session_id),),
        )

        rebuild_session_projections(connection, session_id)
        after_rebuild = _projection_snapshot(connection, str(session_id))
    finally:
        connection.close()

    assert after_rebuild == before_rebuild


def test_runtime_note_projection_keeps_history_and_bounded_active_set(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
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
                    payload=RuntimeNoteRecorded(
                        category="operator",
                        message="Prefer concise output",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=RuntimeNoteRecorded(
                        category="operator",
                        message="Prefer concise output",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=RuntimeNoteRecorded(
                        category="runtime",
                        message="Repo indexing is warm",
                    ),
                ),
            ],
        )

        projected_rows = connection.execute(
            """
            select sequence, category, message
            from runtime_notes
            where session_id = ?
            order by sequence asc
            """,
            (str(session_id),),
        ).fetchall()
        active_notes_before = list_runtime_notes(connection, session_id)

        rebuild_session_projections(connection, session_id)

        active_notes_after = list_runtime_notes(connection, session_id)
    finally:
        connection.close()

    assert [tuple(row) for row in projected_rows] == [
        (2, "operator", "Prefer concise output"),
        (3, "operator", "Prefer concise output"),
        (4, "runtime", "Repo indexing is warm"),
    ]
    assert [
        (note.source_sequence, note.category, note.message, note.inherited)
        for note in active_notes_before
    ] == [
        (3, "operator", "Prefer concise output", False),
        (4, "runtime", "Repo indexing is warm", False),
    ]
    assert active_notes_after == active_notes_before
