"""Focused coverage for task query verification and repair derivation."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import EventEnvelope
from glassbox.core import TaskVerificationRetried
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import TaskVerificationLedgerRecord
from glassbox.core.models import TaskVerificationLedgerSummary
from glassbox.core.types import LongRunPhase
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import VerificationFailureCategory
from glassbox.runtime.task_query_repair import repair_history_view
from glassbox.runtime.task_query_verification import last_known_good_view
from glassbox.runtime.verification_drift import VerificationDriftAssessment


def test_last_known_good_includes_checkpoint_and_stale_drift_evidence() -> None:
    session_id = new_session_id()
    task_id = new_task_id()
    verification_id = new_task_verification_id()
    checkpoint_id = new_task_checkpoint_id()
    ledger = [
        _ledger(
            session_id=session_id,
            task_id=task_id,
            verification_id=verification_id,
            status=TaskVerificationStatus.PASSED,
            last_success_sequence=42,
            changed_paths=[Path("src/glassbox/runtime/task_queries.py")],
            summary="tests passed",
        )
    ]
    checkpoints = [
        TaskCheckpointRecord(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            task_id=task_id,
            objective="Keep task query behavior stable",
            current_phase=LongRunPhase.VERIFYING,
            next_action="rerun task route tests",
            recovery_guidance="resume from verification evidence",
            source_start_sequence=40,
            source_end_sequence=45,
            created_at=datetime.now(UTC),
            last_sequence=46,
        )
    ]
    drift = VerificationDriftAssessment(
        task_id=task_id,
        posture="stale",
        workspace_clean=False,
        changed_paths=["src/glassbox/runtime/task_queries.py"],
        material_changed_paths=["src/glassbox/runtime/task_queries.py"],
        stale_verification_ids=[verification_id],
        stale_changed_paths=["src/glassbox/runtime/task_queries.py"],
        changed_path_digest="digest",
        reason="tracked files changed after verification",
    )

    view = last_known_good_view(
        task_id=task_id,
        ledger=ledger,
        checkpoints=checkpoints,
        drift=drift,
    )

    assert view is not None
    assert view.verification_id == verification_id
    assert view.checkpoint_id == checkpoint_id
    assert view.checkpoint_sequence == 46
    assert view.evidence_status == "stale"
    assert view.stale_paths == ["src/glassbox/runtime/task_queries.py"]


def test_repair_history_reports_repaired_retry_edges() -> None:
    session_id = new_session_id()
    task_id = new_task_id()
    failed_id = new_task_verification_id()
    repair_id = new_task_verification_id()
    ledger = [
        _ledger(
            session_id=session_id,
            task_id=task_id,
            verification_id=failed_id,
            status=TaskVerificationStatus.FAILED,
            latest_failed_sequence=10,
            latest_failed_summary="ty found a type mismatch",
            latest_failed_category=VerificationFailureCategory.TYPECHECK,
        ),
        _ledger(
            session_id=session_id,
            task_id=task_id,
            verification_id=repair_id,
            status=TaskVerificationStatus.PASSED,
            last_success_sequence=15,
            accepted_risk_count=1,
        ),
    ]
    summary = TaskVerificationLedgerSummary(
        task_id=task_id,
        total_count=2,
        passed_count=1,
        failed_count=1,
        latest_success_verification_id=repair_id,
        latest_success_check_name="ty check",
        latest_success_sequence=15,
        latest_failed_verification_id=failed_id,
        latest_failed_check_name="ty check",
        latest_failed_sequence=10,
        latest_failed_summary="ty found a type mismatch",
        current_posture="verified",
    )
    event = EventEnvelope(
        session_id=session_id,
        sequence=12,
        payload=TaskVerificationRetried(
            task_id=task_id,
            verification_id=failed_id,
            next_verification_id=repair_id,
            attempt=2,
            reason="fixed the type mismatch",
        ),
    )

    view = repair_history_view(
        task_id=task_id,
        ledger=ledger,
        events=[event],
        summary=summary,
    )

    assert view.status == "repaired"
    assert view.failure_count == 1
    assert view.retry_count == 1
    assert view.repaired_count == 1
    assert view.attempts[0].failed_summary == "ty found a type mismatch"
    assert view.attempts[0].accepted_risk_count == 1


def test_repair_history_counts_repeated_failure_signatures() -> None:
    session_id = new_session_id()
    task_id = new_task_id()
    first_failed_id = new_task_verification_id()
    second_failed_id = new_task_verification_id()
    ledger = [
        _ledger(
            session_id=session_id,
            task_id=task_id,
            verification_id=first_failed_id,
            status=TaskVerificationStatus.FAILED,
            latest_failed_sequence=8,
            latest_failed_summary="pytest failed",
            latest_failed_category=VerificationFailureCategory.LINT,
        ),
        _ledger(
            session_id=session_id,
            task_id=task_id,
            verification_id=second_failed_id,
            status=TaskVerificationStatus.FAILED,
            latest_failed_sequence=11,
            latest_failed_summary="pytest failed",
            latest_failed_category=VerificationFailureCategory.LINT,
        ),
    ]
    summary = TaskVerificationLedgerSummary(
        task_id=task_id,
        total_count=2,
        failed_count=2,
        latest_failed_verification_id=second_failed_id,
        latest_failed_check_name="pytest",
        latest_failed_sequence=11,
        latest_failed_summary="pytest failed",
        current_posture="failed",
    )

    view = repair_history_view(
        task_id=task_id,
        ledger=ledger,
        events=[],
        summary=summary,
    )

    assert view.status == "failed"
    assert view.repeated_failure_count == 1
    assert view.latest_failure_sequence == 11


def _ledger(
    *,
    session_id,
    task_id,
    verification_id,
    status: TaskVerificationStatus,
    last_success_sequence: int | None = None,
    latest_failed_sequence: int | None = None,
    latest_failed_summary: str | None = None,
    latest_failed_category: VerificationFailureCategory | None = None,
    changed_paths: list[Path] | None = None,
    accepted_risk_count: int = 0,
    summary: str | None = None,
) -> TaskVerificationLedgerRecord:
    return TaskVerificationLedgerRecord(
        session_id=session_id,
        task_id=task_id,
        verification_id=verification_id,
        status=status,
        check_name="ty check",
        changed_paths=changed_paths or [],
        attempt_count=1,
        latest_attempt=1,
        last_success_sequence=last_success_sequence,
        latest_failed_sequence=latest_failed_sequence,
        latest_failed_summary=latest_failed_summary,
        latest_failed_category=latest_failed_category,
        accepted_risk_count=accepted_risk_count,
        summary=summary,
        updated_at=datetime.now(UTC),
        last_sequence=last_success_sequence or latest_failed_sequence or 1,
    )
