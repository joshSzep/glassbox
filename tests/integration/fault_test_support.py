"""Shared fixtures for integration tests around recovery boundaries."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from glassbox.core import ApprovalDecision
from glassbox.core import ApprovalId
from glassbox.core import ApprovalRequested
from glassbox.core import ApprovalResolved
from glassbox.core import AssistantMessageCompleted
from glassbox.core import AssistantMessageDelta
from glassbox.core import AssistantMessageStarted
from glassbox.core import EventEnvelope
from glassbox.core import MessageId
from glassbox.core import MessagePart
from glassbox.core import ModelToolCallRequested
from glassbox.core import SessionId
from glassbox.core import SessionStarted
from glassbox.core import ToolCallId
from glassbox.core import ToolExecutionCompleted
from glassbox.core import ToolExecutionStarted
from glassbox.core import TurnCompleted
from glassbox.core import TurnId
from glassbox.core import TurnStarted
from glassbox.core import UserMessageReceived
from glassbox.core import new_approval_id
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database


@dataclass(frozen=True)
class RepresentativeSessionIds:
    session_id: SessionId
    user_message_id: MessageId
    assistant_message_id: MessageId
    turn_id: TurnId
    tool_call_id: ToolCallId
    approval_id: ApprovalId


def open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def append_representative_completed_session(
    connection: sqlite3.Connection,
    workspace_root: Path,
) -> RepresentativeSessionIds:
    ids = RepresentativeSessionIds(
        session_id=new_session_id(),
        user_message_id=new_message_id(),
        assistant_message_id=new_message_id(),
        turn_id=new_turn_id(),
        tool_call_id=new_tool_call_id(),
        approval_id=new_approval_id(),
    )
    append_events(
        connection,
        [
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(workspace_root),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=UserMessageReceived(
                    message_id=ids.user_message_id,
                    text="inspect the repository",
                ),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=TurnStarted(
                    turn_id=ids.turn_id,
                    trigger_message_id=ids.user_message_id,
                ),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=AssistantMessageStarted(message_id=ids.assistant_message_id),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=AssistantMessageDelta(
                    message_id=ids.assistant_message_id,
                    delta="Inspecting",
                ),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=ModelToolCallRequested(
                    turn_id=ids.turn_id,
                    tool_call_id=ids.tool_call_id,
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
                session_id=ids.session_id,
                sequence=0,
                payload=ToolExecutionStarted(
                    turn_id=ids.turn_id,
                    tool_call_id=ids.tool_call_id,
                    tool_name="read_file",
                    policy_outcome="allow",
                    policy_risk_level="read_only",
                    policy_source_kind="default",
                    policy_source_label="read_only",
                    policy_reason="allowed: read-only tool within workspace scope",
                ),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=ApprovalRequested(
                    approval_id=ids.approval_id,
                    turn_id=ids.turn_id,
                    reason="Need permission",
                    subject="read_file",
                    policy_outcome="approve",
                    policy_risk_level="workspace_write",
                    policy_source_kind="default",
                    policy_source_label="workspace_write",
                ),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=ApprovalResolved(
                    approval_id=ids.approval_id,
                    decision=ApprovalDecision.APPROVED,
                    decided_by="user",
                ),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=ToolExecutionCompleted(
                    turn_id=ids.turn_id,
                    tool_call_id=ids.tool_call_id,
                    success=True,
                    exit_code=0,
                    summary="read complete",
                ),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=AssistantMessageCompleted(
                    message_id=ids.assistant_message_id,
                    parts=[MessagePart(kind="text", text="Inspecting complete")],
                ),
            ),
            EventEnvelope(
                session_id=ids.session_id,
                sequence=0,
                payload=TurnCompleted(
                    turn_id=ids.turn_id,
                    outcome="completed",
                ),
            ),
        ],
    )
    return ids


def projection_snapshot(
    connection: sqlite3.Connection,
    session_id: SessionId,
) -> dict[str, list[tuple]]:
    session_id_value = str(session_id)
    return {
        "session_state": [
            tuple(row)
            for row in connection.execute(
                """
                select status, current_turn_id, pending_approval_id, last_sequence
                from session_state
                where session_id = ?
                """,
                (session_id_value,),
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
                (session_id_value,),
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
                (session_id_value,),
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
                (session_id_value,),
            ).fetchall()
        ],
    }
