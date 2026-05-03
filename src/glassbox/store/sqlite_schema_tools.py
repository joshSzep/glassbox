"""Tool-call, approval, and tool-attempt SQLite schema migrations."""

import sqlite3

from glassbox.store.sqlite_schema_helpers import column_names


def ensure_policy_metadata_projection_schema(
    connection: sqlite3.Connection,
) -> None:
    tool_call_columns = column_names(connection, "tool_calls")
    if "policy_outcome" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_outcome text")
    if "policy_risk_level" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_risk_level text")
    if "policy_source_kind" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_source_kind text")
    if "policy_source_label" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_source_label text")
    if "policy_reason" not in tool_call_columns:
        connection.execute("alter table tool_calls add column policy_reason text")

    approval_columns = column_names(connection, "approvals")
    if "policy_outcome" not in approval_columns:
        connection.execute("alter table approvals add column policy_outcome text")
    if "policy_risk_level" not in approval_columns:
        connection.execute("alter table approvals add column policy_risk_level text")
    if "policy_source_kind" not in approval_columns:
        connection.execute("alter table approvals add column policy_source_kind text")
    if "policy_source_label" not in approval_columns:
        connection.execute("alter table approvals add column policy_source_label text")


def ensure_tool_attempt_projection_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        create table if not exists tool_attempts (
            tool_attempt_id text not null,
            session_id text not null,
            turn_id text not null,
            tool_call_id text,
            task_id text,
            tool_name text not null,
            status text not null,
            message text,
            started_at text,
            last_heartbeat_at text,
            heartbeat_expires_at text,
            completed_at text,
            completed_units integer,
            total_units integer,
            output_artifact_id text,
            safe_to_retry integer,
            retry_classification text,
            retry_requires_approval integer,
            retry_reason text,
            retry_policy_reason text,
            command_purpose text,
            command_review_relevance text,
            command_supports_verification integer,
            command_purpose_reason text,
            command_environment_json text,
            last_sequence integer not null,
            primary key (session_id, tool_attempt_id),
            foreign key (session_id) references sessions(session_id)
        )
        """
    )
    connection.execute(
        """
        create index if not exists idx_tool_attempts_session_status
            on tool_attempts (session_id, status, last_sequence desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_tool_attempts_turn
            on tool_attempts (session_id, turn_id, last_sequence desc)
        """
    )
    connection.execute(
        """
        create index if not exists idx_tool_attempts_tool_call
            on tool_attempts (session_id, tool_call_id, last_sequence desc)
        """
    )
    existing_columns = column_names(connection, "tool_attempts")
    if "retry_classification" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column retry_classification text"
        )
    if "retry_requires_approval" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column retry_requires_approval integer"
        )
    if "retry_policy_reason" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column retry_policy_reason text"
        )
    if "command_purpose" not in existing_columns:
        connection.execute("alter table tool_attempts add column command_purpose text")
    if "command_review_relevance" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column command_review_relevance text"
        )
    if "command_supports_verification" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column command_supports_verification integer"
        )
    if "command_purpose_reason" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column command_purpose_reason text"
        )
    if "command_environment_json" not in existing_columns:
        connection.execute(
            "alter table tool_attempts add column command_environment_json text"
        )
