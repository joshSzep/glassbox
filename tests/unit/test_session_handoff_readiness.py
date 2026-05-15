"""Unit tests for session-level handoff readiness derivation."""

from datetime import UTC
from datetime import datetime

from glassbox.core import CheckpointAbsenceReason
from glassbox.core import CheckpointAbsenceRecord
from glassbox.core import HandoffIntent
from glassbox.core import HandoffReadinessState
from glassbox.core import ProjectionHealth
from glassbox.core import TaskCheckpointRecord
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.runtime.session_handoff_readiness import derive_session_handoff_readiness
from glassbox.runtime.session_queries import SessionSnapshotView


def test_session_handoff_readiness_ready_for_review_with_checkpoint() -> None:
    snapshot = _snapshot(latest_checkpoint=_checkpoint())

    readiness = derive_session_handoff_readiness(
        snapshot,
        intent=HandoffIntent.REVIEW_ONLY,
    )

    assert readiness.state == HandoffReadinessState.READY
    assert readiness.confidence == "high"
    assert readiness.supporting_evidence
    assert all(command.read_only for command in readiness.safe_first_commands)
    assert "does not resume" in readiness.non_claims[1]


def test_session_handoff_readiness_blocks_pending_approval() -> None:
    snapshot = _snapshot(
        latest_checkpoint=_checkpoint(),
        pending_approval_id="approval-123",
    )

    readiness = derive_session_handoff_readiness(
        snapshot,
        intent=HandoffIntent.CONTINUE_WORK,
    )

    assert readiness.state == HandoffReadinessState.AWAITING_APPROVAL
    assert any("Pending approval" in reason.summary for reason in readiness.reasons)


def test_session_handoff_readiness_marks_imported_session_historical_only() -> None:
    snapshot = _snapshot(
        status="completed",
        checkpoint_absence=CheckpointAbsenceRecord(
            reason=CheckpointAbsenceReason.IMPORTED_INSPECTION_ONLY,
            severity="info",
            message="Imported for inspection.",
            next_action="Inspect transcript.",
        ),
    )

    readiness = derive_session_handoff_readiness(
        snapshot,
        intent=HandoffIntent.CONTINUE_WORK,
    )

    assert readiness.state == HandoffReadinessState.HISTORICAL_ONLY
    assert any("inspection state" in item for item in readiness.limitations)


def test_session_handoff_readiness_needs_context_without_checkpoint() -> None:
    snapshot = _snapshot()

    readiness = derive_session_handoff_readiness(
        snapshot,
        intent=HandoffIntent.CONTINUE_WORK,
    )

    assert readiness.state == HandoffReadinessState.NEEDS_CONTEXT
    assert readiness.freshness == "missing"


def test_session_handoff_readiness_surfaces_local_only_tool_attempts() -> None:
    snapshot = _snapshot(
        latest_checkpoint=_checkpoint(),
        recent_tool_attempts=[object()],
    )

    readiness = derive_session_handoff_readiness(
        snapshot,
        intent=HandoffIntent.REVIEW_ONLY,
    )

    assert readiness.state == HandoffReadinessState.LOCAL_ONLY_EVIDENCE
    assert readiness.local_only_evidence[0].portable is False


def _snapshot(
    *,
    status: str = "running",
    latest_checkpoint: TaskCheckpointRecord | None = None,
    checkpoint_absence: CheckpointAbsenceRecord | None = None,
    pending_approval_id: str | None = None,
    pending_question_id: str | None = None,
    session_failure_message: str | None = None,
    recent_tool_attempts: list[object] | None = None,
) -> SessionSnapshotView:
    return SessionSnapshotView.model_construct(
        session_id=new_session_id(),
        status=status,
        transcript=[object()],
        latest_checkpoint=latest_checkpoint,
        checkpoint_absence=checkpoint_absence,
        pending_approval_id=pending_approval_id,
        pending_question_id=pending_question_id,
        session_failure_message=session_failure_message,
        session_failure_retryable=None,
        recent_tool_attempts=recent_tool_attempts or [],
        latest_provider_recovery=None,
        projection_health=ProjectionHealth(
            state="ok",
            canonical_last_sequence=1,
            projected_last_sequence=1,
        ),
    )


def _checkpoint() -> TaskCheckpointRecord:
    session_id = new_session_id()
    return TaskCheckpointRecord(
        checkpoint_id=new_task_checkpoint_id(),
        session_id=session_id,
        objective="Finish the handoff.",
        next_action="Inspect handoff readiness.",
        recovery_guidance="Continue from the readiness summary.",
        source_start_sequence=1,
        source_end_sequence=2,
        created_at=datetime(2026, 5, 14, tzinfo=UTC),
        last_sequence=2,
    )
