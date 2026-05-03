"""Integration tests for SQLite projection handlers and rebuilds."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import AutonomyBudget
from glassbox.core import AutonomyBudgetRemaining
from glassbox.core import AutonomyBudgetUsage
from glassbox.core import AutonomyMode
from glassbox.core import BudgetDecisionRecorded
from glassbox.core import CommandEnvironmentSummary
from glassbox.core import CommandPurpose
from glassbox.core import CommandReviewRelevance
from glassbox.core import CommandToolchainVersion
from glassbox.core import ContextCompactionCreated
from glassbox.core import ContextCompactionFreshness
from glassbox.core import ContextCompactionFreshnessChanged
from glassbox.core import ContextCompactionScope
from glassbox.core import EventEnvelope
from glassbox.core import LongRunPhase
from glassbox.core import ProviderRecoveryAction
from glassbox.core import ProviderRecoveryKind
from glassbox.core import ProviderRecoveryRecorded
from glassbox.core import RuntimeNoteRecorded
from glassbox.core import SessionStarted
from glassbox.core import TaskBlockedReason
from glassbox.core import TaskCheckpointCreated
from glassbox.core import TaskCreated
from glassbox.core import TaskPaused
from glassbox.core import TaskPlanProposed
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepCompleted
from glassbox.core import TaskStepProposal
from glassbox.core import TaskStepStarted
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationFailed
from glassbox.core import TaskVerificationPlanned
from glassbox.core import TaskVerificationResidualRiskAccepted
from glassbox.core import TaskVerificationStarted
from glassbox.core import TaskVerificationStatus
from glassbox.core import ToolAttemptHeartbeat
from glassbox.core import ToolAttemptRetryClassification
from glassbox.core import ToolAttemptStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationFailureCategory
from glassbox.core import VerificationFailureDigest
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import WorkspaceMemoryConfirmed
from glassbox.core import WorkspaceMemoryCreated
from glassbox.core import WorkspaceMemoryImported
from glassbox.core import WorkspaceMemoryInvalidated
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import WorkspaceMemoryUsedInContext
from glassbox.core import new_artifact_id
from glassbox.core import new_context_compaction_id
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_tool_attempt_id
from glassbox.core import new_turn_id
from glassbox.core import new_workspace_memory_id
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import get_budget_posture
from glassbox.store.sqlite import get_context_compaction
from glassbox.store.sqlite import get_latest_provider_recovery
from glassbox.store.sqlite import get_latest_task_checkpoint
from glassbox.store.sqlite import get_tool_attempt
from glassbox.store.sqlite import list_context_compactions
from glassbox.store.sqlite import list_provider_recovery
from glassbox.store.sqlite import list_runtime_notes
from glassbox.store.sqlite import list_task_checkpoints
from glassbox.store.sqlite import list_tool_attempts
from glassbox.store.sqlite import list_workspace_memory
from glassbox.store.sqlite import rebuild_session_projections
from glassbox.store.sqlite_query_verification_ledger import (
    get_task_verification_ledger_summary,
)
from glassbox.store.sqlite_query_verification_ledger import (
    list_task_verification_ledger,
)
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


def test_task_checkpoint_projection_keeps_latest_history_and_rebuilds(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    task_id = new_task_id()
    first_checkpoint_id = new_task_checkpoint_id()
    latest_checkpoint_id = new_task_checkpoint_id()
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
                    payload=TaskCheckpointCreated(
                        checkpoint_id=first_checkpoint_id,
                        task_id=task_id,
                        objective="Finish GBX-1020",
                        current_phase=LongRunPhase.CHECKPOINTING,
                        completed_step="Added checkpoint projection schema",
                        next_action="Add checkpoint query helpers",
                        recovery_guidance="Resume from the projection test",
                        touched_files=["src/glassbox/store/sqlite_schema.py"],
                        verification_status="pending",
                        budget_status="within budget",
                        source_start_sequence=1,
                        source_end_sequence=2,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskCheckpointCreated(
                        checkpoint_id=latest_checkpoint_id,
                        task_id=task_id,
                        objective="Finish GBX-1020",
                        current_phase=LongRunPhase.VERIFYING,
                        completed_step="Added checkpoint query helpers",
                        next_action="Run focused projection tests",
                        recovery_guidance="Rerun pytest for checkpoint projections",
                        blockers=["waiting for test result"],
                        touched_files=[
                            "src/glassbox/store/sqlite_query_checkpoints.py",
                            "tests/integration/test_sqlite_projections.py",
                        ],
                        verification_status="running",
                        budget_status="within budget",
                        source_start_sequence=1,
                        source_end_sequence=3,
                    ),
                ),
            ],
        )

        latest_before = get_latest_task_checkpoint(
            connection,
            session_id,
            task_id=task_id,
        )
        history_before = list_task_checkpoints(connection, session_id, task_id=task_id)
        connection.execute(
            "delete from task_checkpoints where session_id = ?",
            (str(session_id),),
        )
        rebuild_session_projections(connection, session_id)
        latest_after = get_latest_task_checkpoint(
            connection,
            session_id,
            task_id=task_id,
        )
        history_after = list_task_checkpoints(connection, session_id, task_id=task_id)
    finally:
        connection.close()

    assert latest_before == latest_after
    assert history_before == history_after
    assert latest_after is not None
    assert latest_after.checkpoint_id == latest_checkpoint_id
    assert latest_after.current_phase == LongRunPhase.VERIFYING
    assert latest_after.blockers == ["waiting for test result"]
    assert latest_after.touched_files == [
        "src/glassbox/store/sqlite_query_checkpoints.py",
        "tests/integration/test_sqlite_projections.py",
    ]
    assert latest_after.source_start_sequence == 1
    assert latest_after.source_end_sequence == 3
    assert [record.checkpoint_id for record in history_after] == [
        latest_checkpoint_id,
        first_checkpoint_id,
    ]


def test_context_compaction_projection_keeps_history_and_rebuilds(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    task_id = new_task_id()
    compaction_id = new_context_compaction_id()
    source_artifact_id = new_artifact_id()
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
                    payload=ContextCompactionCreated(
                        compaction_id=compaction_id,
                        scope=ContextCompactionScope.TRANSCRIPT,
                        source_start_sequence=1,
                        source_end_sequence=8,
                        summary="Condensed decisions and blockers for handoff",
                        artifact_id=new_artifact_id(),
                        freshness=ContextCompactionFreshness.FRESH,
                        task_id=task_id,
                        source_artifact_ids=[source_artifact_id],
                        decision_count=2,
                        unresolved_question_count=1,
                        accepted_risk_count=1,
                        limitations=["omits raw command output"],
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ContextCompactionFreshnessChanged(
                        compaction_id=compaction_id,
                        freshness=ContextCompactionFreshness.STALE,
                        reason="A newer checkpoint superseded this compaction.",
                        superseded_by_compaction_id=new_context_compaction_id(),
                    ),
                ),
            ],
        )

        before = get_context_compaction(connection, session_id, compaction_id)
        history_before = list_context_compactions(connection, session_id)
        connection.execute(
            "delete from context_compactions where session_id = ?",
            (str(session_id),),
        )
        rebuild_session_projections(connection, session_id)
        after = get_context_compaction(connection, session_id, compaction_id)
        history_after = list_context_compactions(connection, session_id)
    finally:
        connection.close()

    assert before == after
    assert history_before == history_after
    assert after is not None
    assert after.scope == ContextCompactionScope.TRANSCRIPT
    assert after.freshness == ContextCompactionFreshness.STALE
    assert after.freshness_reason == "A newer checkpoint superseded this compaction."
    assert after.superseded_by_compaction_id is not None
    assert after.source_artifact_ids == [source_artifact_id]
    assert after.decision_count == 2
    assert after.unresolved_question_count == 1
    assert after.accepted_risk_count == 1
    assert after.limitations == ["omits raw command output"]


def test_provider_recovery_projection_keeps_latest_history_and_rebuilds(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    next_retry_at = datetime(2026, 4, 30, 12, 5, tzinfo=UTC)
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
                    payload=ProviderRecoveryRecorded(
                        provider="openai",
                        model_name="gpt-5.4",
                        failure_kind=ProviderRecoveryKind.RATE_LIMIT,
                        action=ProviderRecoveryAction.RETRY_SCHEDULED,
                        reason="rate limit exceeded",
                        retryable=True,
                        safe_to_continue=True,
                        operator_next_action="wait for bounded retry",
                        turn_id=turn_id,
                        attempt=1,
                        max_attempts=3,
                        backoff_seconds=4,
                        next_retry_at=next_retry_at,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ProviderRecoveryRecorded(
                        provider="openai",
                        model_name="gpt-5.4",
                        failure_kind=ProviderRecoveryKind.LOST_STREAM,
                        action=ProviderRecoveryAction.RETRY_EXHAUSTED,
                        reason="stream interrupted after retry budget",
                        retryable=True,
                        safe_to_continue=False,
                        operator_next_action="inspect checkpoint before retrying",
                        turn_id=turn_id,
                        attempt=3,
                        max_attempts=3,
                    ),
                ),
            ],
        )

        latest_before = get_latest_provider_recovery(connection, session_id)
        history_before = list_provider_recovery(connection, session_id)
        connection.execute(
            "delete from provider_recovery where session_id = ?",
            (str(session_id),),
        )
        rebuild_session_projections(connection, session_id)
        latest_after = get_latest_provider_recovery(connection, session_id)
        history_after = list_provider_recovery(connection, session_id)
    finally:
        connection.close()

    assert latest_before == latest_after
    assert history_before == history_after
    assert latest_after is not None
    assert latest_after.failure_kind.value == "lost_stream"
    assert latest_after.action.value == "retry_exhausted"
    assert latest_after.safe_to_continue is False
    assert history_after[1].next_retry_at == next_retry_at


def test_tool_attempt_projection_rebuilds_from_heartbeats(tmp_path: Path) -> None:
    session_id = new_session_id()
    turn_id = new_turn_id()
    tool_attempt_id = new_tool_attempt_id()
    heartbeat_expires_at = datetime(2026, 4, 30, 12, 5, tzinfo=UTC)
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
                    payload=ToolAttemptHeartbeat(
                        tool_attempt_id=tool_attempt_id,
                        status=ToolAttemptStatus.STARTED,
                        turn_id=turn_id,
                        tool_name="run_command",
                        message="started",
                        heartbeat_expires_at=heartbeat_expires_at,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolAttemptHeartbeat(
                        tool_attempt_id=tool_attempt_id,
                        status=ToolAttemptStatus.SUCCEEDED,
                        turn_id=turn_id,
                        tool_name="run_command",
                        message="pytest passed",
                        completed_units=1,
                        total_units=1,
                        safe_to_retry=False,
                        retry_classification=(
                            ToolAttemptRetryClassification.UNSAFE_TO_RETRY
                        ),
                        retry_requires_approval=False,
                        retry_reason=(
                            "attempt already succeeded; retrying could duplicate "
                            "completed work"
                        ),
                        command_purpose=CommandPurpose.TEST,
                        command_review_relevance=CommandReviewRelevance.VERIFICATION,
                        command_supports_verification=True,
                        command_purpose_reason=(
                            "test command can support verification evidence"
                        ),
                        command_environment=CommandEnvironmentSummary(
                            capture_scope="verification_or_local_artifact",
                            command_purpose=CommandPurpose.TEST,
                            platform="Darwin",
                            python_version="3.13.0",
                            toolchains=[
                                CommandToolchainVersion(
                                    name="python",
                                    version="3.13.0",
                                    available=True,
                                    source="fixture",
                                    redacted_executable="<redacted-path>/python",
                                )
                            ],
                            environment={"CI": "true"},
                            redaction_notes=["raw environment is not stored"],
                        ),
                    ),
                ),
            ],
        )

        before = get_tool_attempt(connection, session_id, tool_attempt_id)
        history_before = list_tool_attempts(connection, session_id)
        connection.execute(
            "delete from tool_attempts where session_id = ?",
            (str(session_id),),
        )
        rebuild_session_projections(connection, session_id)
        after = get_tool_attempt(connection, session_id, tool_attempt_id)
        history_after = list_tool_attempts(connection, session_id)
    finally:
        connection.close()

    assert before == after
    assert history_before == history_after
    assert after is not None
    assert after.status == ToolAttemptStatus.SUCCEEDED
    assert after.message == "pytest passed"
    assert after.completed_units == 1
    assert after.total_units == 1
    assert after.safe_to_retry is False
    assert after.retry_classification == "unsafe_to_retry"
    assert after.retry_requires_approval is False
    assert after.retry_reason == (
        "attempt already succeeded; retrying could duplicate completed work"
    )
    assert after.command_purpose == CommandPurpose.TEST
    assert after.command_review_relevance == CommandReviewRelevance.VERIFICATION
    assert after.command_supports_verification is True
    assert after.command_purpose_reason == (
        "test command can support verification evidence"
    )
    assert after.command_environment is not None
    assert after.command_environment.environment == {"CI": "true"}
    assert after.command_environment.toolchains[0].redacted_executable == (
        "<redacted-path>/python"
    )
    assert after.completed_at is not None
    assert after.heartbeat_expires_at == heartbeat_expires_at


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


def test_verification_ledger_rebuilds_multi_step_history(tmp_path: Path) -> None:
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    passed_id = new_task_verification_id()
    failed_id = new_task_verification_id()
    artifact_id = new_artifact_id()
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
                        title="Track verification",
                        goal="Retain incremental proof",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        step_id=step_id,
                        verification=VerificationPlanEntry(
                            verification_id=passed_id,
                            check_name="pytest unit",
                            kind=VerificationCheckKind.TEST,
                            command=["uv", "run", "pytest", "tests/unit"],
                            source=VerificationPlanSource.OPERATOR,
                            rationale="focused unit coverage",
                            changed_paths=[Path("src/glassbox/runtime/example.py")],
                        ),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationStarted(
                        task_id=task_id,
                        verification_id=passed_id,
                        step_id=step_id,
                        check_name="pytest unit",
                        attempt=1,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationCompleted(
                        task_id=task_id,
                        verification_id=passed_id,
                        status=TaskVerificationStatus.PASSED,
                        summary="unit tests passed",
                        artifact_id=artifact_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=VerificationPlanEntry(
                            verification_id=failed_id,
                            check_name="eval recommend",
                            kind=VerificationCheckKind.EVAL,
                            command=[
                                "uv",
                                "run",
                                "glassbox",
                                "eval",
                                "recommend",
                                "src/glassbox/runtime/example.py",
                            ],
                            source=VerificationPlanSource.EVAL_RECOMMENDATION,
                            rationale="long-run surface changed",
                            eval_profile_id="commit-smoke",
                        ),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationFailed(
                        task_id=task_id,
                        verification_id=failed_id,
                        failure=VerificationFailureDigest(
                            category=VerificationFailureCategory.ASSERTION,
                            summary="recommended eval failed",
                            exit_code=1,
                            artifact_id=artifact_id,
                        ),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationResidualRiskAccepted(
                        task_id=task_id,
                        verification_id=failed_id,
                        reason="known fixture drift accepted for local run",
                        residual_risks=["fixture drift remains"],
                    ),
                ),
            ],
        )
        before = list_task_verification_ledger(connection, session_id, task_id)
        connection.execute("delete from task_verification_ledger")
        rebuild_session_projections(connection, session_id)
        after = list_task_verification_ledger(connection, session_id, task_id)
        summary = get_task_verification_ledger_summary(
            connection,
            session_id,
            task_id,
        )
    finally:
        connection.close()

    assert before == after
    assert [entry.check_name for entry in after] == ["pytest unit", "eval recommend"]
    assert after[0].status == TaskVerificationStatus.PASSED
    assert after[0].command == ["uv", "run", "pytest", "tests/unit"]
    assert after[0].changed_paths == [Path("src/glassbox/runtime/example.py")]
    assert after[0].last_success_sequence is not None
    assert after[1].status == TaskVerificationStatus.ACCEPTED_WITH_RISK
    assert after[1].latest_failed_summary == "recommended eval failed"
    assert after[1].latest_failed_category == VerificationFailureCategory.ASSERTION
    assert after[1].accepted_risk_count == 1
    assert after[1].accepted_risks == ["fixture drift remains"]
    assert summary.current_posture == "accepted_with_risk"
    assert summary.latest_success_check_name == "pytest unit"
    assert summary.latest_failed_check_name == "eval recommend"


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
        max_unattended_seconds=45,
        checkpoint_interval_seconds=30,
        quiet_window_policy="checkpoint_before_quiet_window",
        max_retry_delay_seconds=10,
        checkpoint_approval_required=True,
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
        unattended_seconds=35,
        seconds_since_checkpoint=20,
        retry_delay_seconds=5,
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
    assert posture.unattended_remaining_seconds == 35
    assert posture.next_checkpoint_due_in_seconds == 20
    assert posture.retry_delay_remaining_seconds == 5
    assert posture.quiet_window_policy == "checkpoint_before_quiet_window"
    assert posture.checkpoint_approval_required is True
