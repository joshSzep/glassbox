"""Unit tests for task-level handoff readiness derivation."""

from datetime import UTC
from datetime import datetime

from glassbox.core import HandoffIntent
from glassbox.core import HandoffReadinessState
from glassbox.core import TaskBlockedReason
from glassbox.core import TaskPlanStatus
from glassbox.core import TaskStepStatus
from glassbox.core import TaskVerificationStatus
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.task_handoff_readiness import derive_task_handoff_readiness
from glassbox.runtime.task_query_models import TaskDetailView
from glassbox.runtime.task_query_models import TaskRepairHistoryView
from glassbox.runtime.task_query_models import TaskStepView
from glassbox.runtime.task_query_models import TaskSummaryView
from glassbox.runtime.task_query_models import TaskVerificationLedgerSummaryView
from glassbox.runtime.task_query_models import TaskVerificationLedgerView
from glassbox.runtime.verification_drift import VerificationDriftAssessment


def test_task_handoff_readiness_needs_context_without_verification() -> None:
    detail = _detail()

    readiness = derive_task_handoff_readiness(
        detail,
        intent=HandoffIntent.CONTINUE_WORK,
    )

    assert readiness.state == HandoffReadinessState.NEEDS_CONTEXT
    assert readiness.freshness == "missing"
    assert readiness.source.kind == "task"
    assert readiness.missing_evidence[0].kind == "verification"
    assert readiness.safe_first_commands[0].display.startswith("glassbox task show")


def test_task_handoff_readiness_blocks_approval() -> None:
    detail = _detail(
        blocked_reason=TaskBlockedReason.AWAITING_APPROVAL,
        blocked_detail="approval required before shell command",
    )

    readiness = derive_task_handoff_readiness(detail)

    assert readiness.state == HandoffReadinessState.AWAITING_APPROVAL
    assert readiness.reasons[0].kind == "policy-blocker"
    assert "approval required" in readiness.reasons[0].summary


def test_task_handoff_readiness_needs_verification_after_failure() -> None:
    detail = _detail(
        verification_summary=TaskVerificationLedgerSummaryView(
            task_id=new_task_id(),
            total_count=1,
            passed_count=0,
            failed_count=1,
            running_count=0,
            skipped_count=0,
            accepted_risk_count=0,
            latest_failed_verification_id=new_task_verification_id(),
            latest_failed_check_name="pytest",
            latest_failed_sequence=10,
            latest_failed_summary="pytest failed",
            current_posture="failed",
        ),
        repair_history=TaskRepairHistoryView(
            task_id=new_task_id(),
            status="failed",
            failure_count=1,
            retry_count=0,
            repaired_count=0,
            repeated_failure_count=0,
            accepted_risk_count=0,
            latest_failure_sequence=10,
            latest_failure_summary="pytest failed",
        ),
    )

    readiness = derive_task_handoff_readiness(detail)

    assert readiness.state == HandoffReadinessState.NEEDS_VERIFICATION
    assert any("failed" in reason.summary for reason in readiness.reasons)
    assert any(
        "task events" in command.display for command in readiness.safe_first_commands
    )


def test_task_handoff_readiness_surfaces_accepted_risk() -> None:
    task_id = new_task_id()
    detail = _detail(
        task_id=task_id,
        verification_summary=TaskVerificationLedgerSummaryView(
            task_id=task_id,
            total_count=1,
            passed_count=1,
            failed_count=0,
            running_count=0,
            skipped_count=0,
            accepted_risk_count=1,
            latest_success_verification_id=new_task_verification_id(),
            latest_success_check_name="ty check",
            latest_success_sequence=12,
            current_posture="accepted_with_risk",
        ),
        verification_ledger=[
            TaskVerificationLedgerView(
                verification_id=new_task_verification_id(),
                check_name="ty check",
                status=TaskVerificationStatus.PASSED,
                accepted_risk_count=1,
                accepted_risks=["type coverage accepted locally"],
                residual_risk_reason="type coverage accepted locally",
                attempt_count=1,
                latest_attempt=1,
                updated_at=datetime.now(UTC),
                last_sequence=12,
            )
        ],
    )

    readiness = derive_task_handoff_readiness(detail)

    assert readiness.state == HandoffReadinessState.ACCEPTED_WITH_RISK
    assert readiness.accepted_risks[0].kind == "accepted-risk"
    assert any(
        "Accepted verification risk" in limitation
        for limitation in readiness.limitations
    )


def test_task_handoff_readiness_marks_completed_continue_as_historical() -> None:
    detail = _detail(status=TaskPlanStatus.COMPLETED)

    readiness = derive_task_handoff_readiness(
        detail,
        intent=HandoffIntent.CONTINUE_WORK,
    )

    assert readiness.state == HandoffReadinessState.HISTORICAL_ONLY
    assert any("completed" in limitation for limitation in readiness.limitations)


def _detail(
    *,
    task_id=None,
    status: TaskPlanStatus = TaskPlanStatus.ACTIVE,
    blocked_reason: TaskBlockedReason | None = None,
    blocked_detail: str | None = None,
    verification_summary: TaskVerificationLedgerSummaryView | None = None,
    verification_ledger: list[TaskVerificationLedgerView] | None = None,
    repair_history: TaskRepairHistoryView | None = None,
) -> TaskDetailView:
    resolved_task_id = task_id or new_task_id()
    session_id = new_session_id()
    step_id = new_task_step_id()
    summary = verification_summary or TaskVerificationLedgerSummaryView(
        task_id=resolved_task_id,
        total_count=0,
        passed_count=0,
        failed_count=0,
        running_count=0,
        skipped_count=0,
        accepted_risk_count=0,
        current_posture="missing",
    )
    repair = repair_history or TaskRepairHistoryView(
        task_id=resolved_task_id,
        status="no_verification",
        failure_count=0,
        retry_count=0,
        repaired_count=0,
        repeated_failure_count=0,
        accepted_risk_count=0,
    )
    return TaskDetailView(
        task=TaskSummaryView(
            task_id=resolved_task_id,
            session_id=session_id,
            title="Implement task handoff readiness",
            goal="Explain task continuation posture for local handoff.",
            status=status,
            updated_at=datetime.now(UTC),
            blocked_reason=blocked_reason,
            blocked_detail=blocked_detail,
            current_step_id=step_id if status == TaskPlanStatus.ACTIVE else None,
            step_count=1,
            next_action_summary="continue from current step",
        ),
        steps=[
            TaskStepView(
                step_id=step_id,
                title="Implement service",
                order=0,
                status=TaskStepStatus.RUNNING,
            )
        ],
        verifications=[],
        verification_ledger=verification_ledger or [],
        verification_summary=summary,
        verification_drift=VerificationDriftAssessment(
            task_id=resolved_task_id,
            posture="not_assessed",
            workspace_clean=False,
            changed_paths=[],
            material_changed_paths=[],
            stale_verification_ids=[],
            stale_changed_paths=[],
            changed_path_digest=None,
            reason="workspace root unavailable; drift not assessed",
        ),
        last_known_good=None,
        repair_history=repair,
    )
