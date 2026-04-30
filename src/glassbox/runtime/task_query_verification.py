"""Verification-ledger derivation helpers for task queries."""

from typing import Literal

from glassbox.core.ids import TaskId
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import TaskVerificationLedgerRecord
from glassbox.core.models import TaskVerificationLedgerSummary
from glassbox.core.types import TaskVerificationStatus
from glassbox.runtime.task_query_models import TaskLastKnownGoodView
from glassbox.runtime.task_query_models import TaskVerificationLedgerSummaryView
from glassbox.runtime.task_query_models import TaskVerificationLedgerView
from glassbox.runtime.verification_drift import VerificationDriftAssessment


def verification_ledger_view_from_record(
    record: TaskVerificationLedgerRecord,
) -> TaskVerificationLedgerView:
    return TaskVerificationLedgerView(
        verification_id=record.verification_id,
        check_name=record.check_name,
        status=record.status,
        step_id=record.step_id,
        kind=record.kind,
        source=record.source,
        command=record.command,
        changed_paths=[str(path) for path in record.changed_paths],
        eval_case_id=record.eval_case_id,
        eval_profile_id=record.eval_profile_id,
        blocking=record.blocking,
        attempt_count=record.attempt_count,
        latest_attempt=record.latest_attempt,
        planned_sequence=record.planned_sequence,
        started_sequence=record.started_sequence,
        last_success_sequence=record.last_success_sequence,
        latest_failed_sequence=record.latest_failed_sequence,
        latest_failed_summary=record.latest_failed_summary,
        latest_failed_category=record.latest_failed_category,
        latest_failed_artifact_id=(
            str(record.latest_failed_artifact_id)
            if record.latest_failed_artifact_id
            else None
        ),
        latest_artifact_id=(
            str(record.latest_artifact_id) if record.latest_artifact_id else None
        ),
        accepted_risk_count=record.accepted_risk_count,
        accepted_risks=record.accepted_risks,
        residual_risk_reason=record.residual_risk_reason,
        summary=record.summary,
        updated_at=record.updated_at,
        last_sequence=record.last_sequence,
    )


def verification_summary_view_from_record(
    record: TaskVerificationLedgerSummary,
) -> TaskVerificationLedgerSummaryView:
    return TaskVerificationLedgerSummaryView.model_validate(
        record.model_dump(mode="python")
    )


def last_known_good_view(
    *,
    task_id: TaskId,
    ledger: list[TaskVerificationLedgerRecord],
    checkpoints: list[TaskCheckpointRecord],
    drift: VerificationDriftAssessment,
) -> TaskLastKnownGoodView | None:
    latest_success = max(
        (
            entry
            for entry in ledger
            if entry.status == TaskVerificationStatus.PASSED
            and entry.last_success_sequence is not None
        ),
        key=lambda entry: entry.last_success_sequence or entry.last_sequence,
        default=None,
    )
    if latest_success is None or latest_success.last_success_sequence is None:
        return None
    checkpoint = checkpoint_for_sequence(
        checkpoints,
        latest_success.last_success_sequence,
    )
    evidence_status: Literal["fresh", "stale", "unknown"] = "fresh"
    if drift.posture in {"unknown", "not_assessed"}:
        evidence_status = "unknown"
    elif (
        drift.posture in {"stale", "missing_coverage"}
        or latest_success.verification_id in drift.stale_verification_ids
    ):
        evidence_status = "stale"
    return TaskLastKnownGoodView(
        task_id=task_id,
        verification_id=latest_success.verification_id,
        check_name=latest_success.check_name,
        sequence=latest_success.last_success_sequence,
        summary=latest_success.summary,
        artifact_id=(
            str(latest_success.latest_artifact_id)
            if latest_success.latest_artifact_id
            else None
        ),
        checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
        checkpoint_sequence=checkpoint.last_sequence if checkpoint else None,
        checkpoint_objective=checkpoint.objective if checkpoint else None,
        changed_paths=[str(path) for path in latest_success.changed_paths],
        changed_path_digest=drift.changed_path_digest,
        drift_posture=drift.posture,
        evidence_status=evidence_status,
        stale_paths=drift.stale_changed_paths,
    )


def checkpoint_for_sequence(
    checkpoints: list[TaskCheckpointRecord],
    sequence: int,
) -> TaskCheckpointRecord | None:
    containing = [
        checkpoint
        for checkpoint in checkpoints
        if (
            checkpoint.source_start_sequence
            <= sequence
            <= checkpoint.source_end_sequence
        )
    ]
    if containing:
        return max(containing, key=lambda checkpoint: checkpoint.last_sequence)
    preceding = [
        checkpoint for checkpoint in checkpoints if checkpoint.last_sequence <= sequence
    ]
    if preceding:
        return max(preceding, key=lambda checkpoint: checkpoint.last_sequence)
    return checkpoints[0] if checkpoints else None
