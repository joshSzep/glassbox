"""Tests for checkpoint-absence reason derivation."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import AutonomyBudgetPostureRecord
from glassbox.core import AutonomyBudgetUsage
from glassbox.core import CheckpointAbsenceReason
from glassbox.core import EventEnvelope
from glassbox.core import MessagePart
from glassbox.core import ProjectionHealth
from glassbox.core import SessionRecord
from glassbox.core import SessionStarted
from glassbox.core import SessionStatus
from glassbox.core import TranscriptMessageImported
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.core.types import AutonomyMode
from glassbox.runtime.autonomy import default_budget_for_autonomy_mode
from glassbox.runtime.budgeting import evaluate_budget
from glassbox.runtime.session_query_helpers import checkpoint_absence_from_evidence


def test_checkpoint_absence_identifies_imported_inspection_sessions() -> None:
    session = _session_record(status=SessionStatus.COMPLETED)
    absence = checkpoint_absence_from_evidence(
        status="completed",
        events=[
            _session_started(session),
            EventEnvelope(
                session_id=session.session_id,
                sequence=2,
                payload=TranscriptMessageImported(
                    message_id=new_message_id(),
                    source_session_id=new_session_id(),
                    source_message_id=new_message_id(),
                    source_turn_id=None,
                    role="user",
                    parts=[MessagePart(kind="text", text="imported prompt")],
                    source_created_at=_timestamp(),
                ),
            ),
        ],
        projection_health=_projection_health(),
        budget_posture=None,
        latest_checkpoint=None,
    )

    assert absence is not None
    assert absence.reason == CheckpointAbsenceReason.IMPORTED_INSPECTION_ONLY
    assert absence.severity == "info"
    assert "imported for inspection" in absence.message


def test_checkpoint_absence_identifies_historical_pre_checkpoint_sessions() -> None:
    session = _session_record(status=SessionStatus.COMPLETED)
    absence = checkpoint_absence_from_evidence(
        status="completed",
        events=[_session_started(session)],
        projection_health=_projection_health(),
        budget_posture=None,
        latest_checkpoint=None,
    )

    assert absence is not None
    assert absence.reason == CheckpointAbsenceReason.HISTORICAL_PRE_CHECKPOINT
    assert absence.next_action == (
        "No checkpoint action is required for historical inspection."
    )


def test_checkpoint_absence_identifies_active_expected_checkpoint_gap() -> None:
    session = _session_record(status=SessionStatus.RUNNING)
    absence = checkpoint_absence_from_evidence(
        status="running",
        events=[_session_started(session)],
        projection_health=_projection_health(),
        budget_posture=_checkpoint_due_posture(session),
        latest_checkpoint=None,
    )

    assert absence is not None
    assert absence.reason == CheckpointAbsenceReason.ACTIVE_CHECKPOINT_EXPECTED
    assert absence.severity == "warning"
    assert "reached its checkpoint interval" in absence.message


def test_checkpoint_absence_identifies_projection_degradation() -> None:
    session = _session_record(status=SessionStatus.RUNNING)
    absence = checkpoint_absence_from_evidence(
        status="running",
        events=[_session_started(session)],
        projection_health=ProjectionHealth(
            state="unavailable",
            canonical_last_sequence=3,
            projected_last_sequence=None,
            lag=3,
            estimated_rebuild_event_count=3,
            degraded=True,
            detail="projection read failed",
        ),
        budget_posture=None,
        latest_checkpoint=None,
    )

    assert absence is not None
    assert absence.reason == CheckpointAbsenceReason.PROJECTION_DEGRADED
    assert absence.severity == "blocked"
    assert "Rebuild derived projections" in absence.next_action


def test_checkpoint_absence_identifies_not_expected_yet_live_sessions() -> None:
    session = _session_record(status=SessionStatus.RUNNING)
    absence = checkpoint_absence_from_evidence(
        status="running",
        events=[_session_started(session)],
        projection_health=_projection_health(),
        budget_posture=None,
        latest_checkpoint=None,
    )

    assert absence is not None
    assert absence.reason == CheckpointAbsenceReason.NOT_EXPECTED_YET
    assert absence.next_action == "No checkpoint action is required yet."


def _session_record(*, status: SessionStatus) -> SessionRecord:
    return SessionRecord(
        session_id=new_session_id(),
        status=status,
        created_at=_timestamp(),
        updated_at=_timestamp(),
        cwd=Path("."),
        model_name="openai:gpt-5.4",
        approval_mode="confirm",
        last_sequence=1,
    )


def _session_started(session: SessionRecord) -> EventEnvelope:
    return EventEnvelope(
        session_id=session.session_id,
        sequence=1,
        created_at=_timestamp(),
        payload=SessionStarted(
            cwd=str(session.cwd),
            model_name=session.model_name,
            approval_mode=session.approval_mode,
        ),
    )


def _checkpoint_due_posture(session: SessionRecord) -> AutonomyBudgetPostureRecord:
    budget = default_budget_for_autonomy_mode(AutonomyMode.TEST_DRIVEN)
    usage = AutonomyBudgetUsage(
        seconds_since_checkpoint=budget.checkpoint_interval_seconds or 0,
    )
    remaining = evaluate_budget(budget, usage).remaining
    return AutonomyBudgetPostureRecord(
        session_id=session.session_id,
        mode=AutonomyMode.TEST_DRIVEN,
        budget=budget,
        usage=usage,
        remaining=remaining,
        last_decision="allow",
        next_checkpoint_due_in_seconds=0,
        checkpoint_approval_required=budget.checkpoint_approval_required,
        last_sequence=session.last_sequence,
        updated_at=_timestamp(),
    )


def _projection_health() -> ProjectionHealth:
    return ProjectionHealth(
        state="ok",
        canonical_last_sequence=1,
        projected_last_sequence=1,
        projected_progress_ratio=1.0,
    )


def _timestamp() -> datetime:
    return datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
