"""Integration tests for SQLite projection handlers and rebuilds."""

from pathlib import Path

from glassbox.core import AutonomyBudget
from glassbox.core import AutonomyBudgetRemaining
from glassbox.core import AutonomyBudgetUsage
from glassbox.core import AutonomyMode
from glassbox.core import BudgetDecisionRecorded
from glassbox.core import EventEnvelope
from glassbox.core import RuntimeNoteRecorded
from glassbox.core import SessionStarted
from glassbox.core import TaskBlockedReason
from glassbox.core import TaskCreated
from glassbox.core import TaskPaused
from glassbox.core import TaskPlanProposed
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepCompleted
from glassbox.core import TaskStepProposal
from glassbox.core import TaskStepStarted
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationStarted
from glassbox.core import TaskVerificationStatus
from glassbox.core import WorkspaceMemoryConfirmed
from glassbox.core import WorkspaceMemoryCreated
from glassbox.core import WorkspaceMemoryImported
from glassbox.core import WorkspaceMemoryInvalidated
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import WorkspaceMemoryUsedInContext
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_turn_id
from glassbox.core import new_workspace_memory_id
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import get_budget_posture
from glassbox.store.sqlite import list_runtime_notes
from glassbox.store.sqlite import list_workspace_memory
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


def test_task_projection_rebuilds_task_steps_and_verifications(tmp_path: Path) -> None:
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    verification_id = new_task_verification_id()
    connection = open_initialized_database(tmp_path)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd=str(tmp_path),
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskCreated(
                        task_id=task_id,
                        title="Add projections",
                        goal="Make task plans queryable",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskPlanProposed(
                        task_id=task_id,
                        plan=TaskPlanSnapshot(
                            task_id=task_id,
                            title="Add projections",
                            goal="Make task plans queryable",
                            steps=[
                                TaskStepProposal(
                                    step_id=step_id,
                                    title="Create task tables",
                                    order=0,
                                )
                            ],
                        ),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskStepStarted(task_id=task_id, step_id=step_id),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskStepCompleted(
                        task_id=task_id,
                        step_id=step_id,
                        summary="tables created",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationStarted(
                        task_id=task_id,
                        verification_id=verification_id,
                        step_id=step_id,
                        check_name="pytest",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationCompleted(
                        task_id=task_id,
                        verification_id=verification_id,
                        status=TaskVerificationStatus.PASSED,
                        summary="projection tests passed",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskPaused(
                        task_id=task_id,
                        reason=TaskBlockedReason.MANUAL_PAUSE,
                        detail="waiting for review",
                    ),
                ),
            ],
        )

        task_before = list(connection.execute("select * from tasks"))
        steps_before = list(connection.execute("select * from task_steps"))
        verifications_before = list(
            connection.execute("select * from task_verifications")
        )

        connection.execute("delete from task_verifications")
        connection.execute("delete from task_steps")
        connection.execute("delete from tasks")
        rebuild_session_projections(connection, session_id)

        task = connection.execute(
            """
            select status, blocked_reason, blocked_detail
            from tasks
            where task_id = ?
            """,
            (str(task_id),),
        ).fetchone()
        step = connection.execute(
            "select status, summary from task_steps where step_id = ?",
            (str(step_id),),
        ).fetchone()
        verification = connection.execute(
            "select status, summary from task_verifications where verification_id = ?",
            (str(verification_id),),
        ).fetchone()
    finally:
        connection.close()

    assert task_before
    assert steps_before
    assert verifications_before
    assert tuple(task) == ("paused", "manual_pause", "waiting for review")
    assert tuple(step) == ("completed", "tables created")
    assert tuple(verification) == ("passed", "projection tests passed")


def test_workspace_memory_projection_rebuilds_lifecycle(tmp_path: Path) -> None:
    session_id = new_session_id()
    memory_id = new_workspace_memory_id()
    imported_memory_id = new_workspace_memory_id()
    turn_id = new_turn_id()
    connection = open_initialized_database(tmp_path)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd=str(tmp_path),
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryCreated(
                        memory_id=memory_id,
                        kind=WorkspaceMemoryKind.COMMAND,
                        content="Use uv run pytest for backend tests.",
                        summary="backend pytest command",
                        provenance=WorkspaceMemoryProvenance(
                            source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                            session_id=session_id,
                            source_sequence=1,
                        ),
                        tags=["testing"],
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryConfirmed(memory_id=memory_id),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryUsedInContext(
                        memory_id=memory_id,
                        turn_id=turn_id,
                        prompt_section="workspace_memory",
                        reason="backend validation request",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryInvalidated(
                        memory_id=memory_id,
                        reason="superseded by focused command",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=WorkspaceMemoryImported(
                        memory_id=imported_memory_id,
                        kind=WorkspaceMemoryKind.FACT,
                        content="Imported memory is redacted unless reviewed.",
                        provenance=WorkspaceMemoryProvenance(
                            source_type=WorkspaceMemorySourceType.IMPORT,
                            source_label="session export",
                        ),
                        import_source="session-export.json",
                    ),
                ),
            ],
        )

        before_rebuild = list_workspace_memory(connection)
        connection.execute("delete from workspace_memory")
        rebuild_session_projections(connection, session_id)
        after_rebuild = list_workspace_memory(connection)
    finally:
        connection.close()

    assert len(before_rebuild) == 2
    assert after_rebuild == before_rebuild
    memory = next(entry for entry in after_rebuild if entry.memory_id == memory_id)
    imported_memory = next(
        entry for entry in after_rebuild if entry.memory_id == imported_memory_id
    )
    assert memory.memory_id == memory_id
    assert memory.session_id == session_id
    assert memory.state == "invalidated"
    assert memory.confirmed_by == "operator"
    assert memory.use_count == 1
    assert memory.invalidation_reason == "superseded by focused command"
    assert imported_memory.state == "imported"
    assert imported_memory.redacted is True
    assert imported_memory.import_source == "session-export.json"


def test_budget_projection_records_latest_session_posture(tmp_path: Path) -> None:
    session_id = new_session_id()
    budget = AutonomyBudget(
        max_steps=3,
        max_tool_calls=4,
        max_write_operations=0,
        max_command_operations=0,
        max_wall_clock_seconds=60,
        max_verification_attempts=2,
        max_branch_attempts=1,
        max_artifact_bytes=1024,
        allowed_risk_buckets=["read_only"],
    )
    usage = AutonomyBudgetUsage(steps=2, tool_calls=1)
    remaining = AutonomyBudgetRemaining(
        steps=1,
        tool_calls=3,
        write_operations=budget.max_write_operations,
        command_operations=budget.max_command_operations,
        wall_clock_seconds=budget.max_wall_clock_seconds,
        verification_attempts=budget.max_verification_attempts,
        branch_attempts=budget.max_branch_attempts,
        artifact_bytes=budget.max_artifact_bytes,
    )
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
                    payload=BudgetDecisionRecorded(
                        scope="session",
                        mode=AutonomyMode.GUIDED,
                        budget=budget,
                        usage=usage,
                        remaining=remaining,
                        decision="allowed",
                    ),
                ),
            ],
        )

        posture = get_budget_posture(connection, session_id)
    finally:
        connection.close()

    assert posture is not None
    assert posture.mode == AutonomyMode.GUIDED
    assert posture.last_decision == "allowed"
    assert posture.usage.steps == 2
    assert posture.remaining is not None
    assert posture.remaining.tool_calls == 3
