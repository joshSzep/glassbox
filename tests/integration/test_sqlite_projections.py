"""Integration tests for SQLite projection handlers and rebuilds."""

from pathlib import Path

from glassbox.core import EventEnvelope
from glassbox.core import RuntimeNoteRecorded
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import list_runtime_notes
from glassbox.store.sqlite import rebuild_session_projections
from tests.integration.fault_test_support import append_representative_completed_session
from tests.integration.fault_test_support import open_initialized_database
from tests.integration.fault_test_support import projection_snapshot


def test_append_events_updates_projection_tables(tmp_path: Path) -> None:
    connection = open_initialized_database(tmp_path)
    try:
        ids = append_representative_completed_session(connection, tmp_path)

        session_state_row = connection.execute(
            """
            select status, current_turn_id, pending_approval_id, last_sequence
            from session_state
            where session_id = ?
            """,
            (str(ids.session_id),),
        ).fetchone()
        transcript_rows = connection.execute(
            """
            select role, status, content_text
            from transcript_messages
            where session_id = ?
            order by created_at asc
            """,
            (str(ids.session_id),),
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
            (str(ids.tool_call_id),),
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
            (str(ids.approval_id),),
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
    connection = open_initialized_database(tmp_path)
    try:
        ids = append_representative_completed_session(connection, tmp_path)
        before_rebuild = projection_snapshot(connection, ids.session_id)
        connection.execute(
            "delete from session_state where session_id = ?",
            (str(ids.session_id),),
        )
        connection.execute(
            "delete from transcript_messages where session_id = ?",
            (str(ids.session_id),),
        )
        connection.execute(
            "delete from tool_calls where session_id = ?",
            (str(ids.session_id),),
        )
        connection.execute(
            "delete from approvals where session_id = ?",
            (str(ids.session_id),),
        )

        rebuild_session_projections(connection, ids.session_id)
        after_rebuild = projection_snapshot(connection, ids.session_id)
    finally:
        connection.close()

    assert after_rebuild == before_rebuild


def test_runtime_note_projection_keeps_history_and_bounded_active_set(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    connection = open_initialized_database(tmp_path)
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
