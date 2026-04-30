"""Repair-history derivation helpers for task queries."""

from typing import Literal

from glassbox.core.events import EventEnvelope
from glassbox.core.events import TaskVerificationRetried
from glassbox.core.ids import TaskId
from glassbox.core.models import TaskVerificationLedgerRecord
from glassbox.core.models import TaskVerificationLedgerSummary
from glassbox.core.types import TaskVerificationStatus
from glassbox.runtime.task_query_models import TaskRepairAttemptView
from glassbox.runtime.task_query_models import TaskRepairHistoryView

TaskRepairHistoryStatus = Literal[
    "no_verification",
    "clean",
    "partial",
    "failed",
    "repairing",
    "repaired",
    "accepted_with_risk",
    "regressed",
]


def repair_history_view(
    *,
    task_id: TaskId,
    ledger: list[TaskVerificationLedgerRecord],
    events: list[EventEnvelope],
    summary: TaskVerificationLedgerSummary,
) -> TaskRepairHistoryView:
    ledger_by_id = {entry.verification_id: entry for entry in ledger}
    failed_entries = [
        entry for entry in ledger if entry.latest_failed_sequence is not None
    ]
    attempts: list[TaskRepairAttemptView] = []
    for event in events:
        payload = event.payload
        if not isinstance(payload, TaskVerificationRetried):
            continue
        failed_entry = ledger_by_id.get(payload.verification_id)
        next_entry = ledger_by_id.get(payload.next_verification_id)
        attempts.append(
            TaskRepairAttemptView(
                verification_id=payload.verification_id,
                next_verification_id=payload.next_verification_id,
                attempt=payload.attempt,
                reason=payload.reason,
                source_sequence=event.sequence,
                failed_summary=(
                    failed_entry.latest_failed_summary if failed_entry else None
                ),
                failed_artifact_id=(
                    str(failed_entry.latest_failed_artifact_id)
                    if failed_entry and failed_entry.latest_failed_artifact_id
                    else None
                ),
                repaired=(
                    next_entry is not None
                    and next_entry.status == TaskVerificationStatus.PASSED
                ),
                accepted_risk_count=(
                    next_entry.accepted_risk_count if next_entry else 0
                ),
            )
        )

    latest_failure = max(
        failed_entries,
        key=lambda entry: entry.latest_failed_sequence or entry.last_sequence,
        default=None,
    )
    repaired_count = sum(1 for attempt in attempts if attempt.repaired)
    repeated_failure_count = repeated_failure_count_for_entries(failed_entries)
    status = repair_history_status(
        ledger=ledger,
        summary=summary,
        latest_failure=latest_failure,
        retry_count=len(attempts),
        repaired_count=repaired_count,
    )
    return TaskRepairHistoryView(
        task_id=task_id,
        status=status,
        failure_count=len(failed_entries),
        retry_count=len(attempts),
        repaired_count=repaired_count,
        repeated_failure_count=repeated_failure_count,
        accepted_risk_count=summary.accepted_risk_count,
        latest_failure_sequence=(
            latest_failure.latest_failed_sequence if latest_failure else None
        ),
        latest_failure_summary=(
            latest_failure.latest_failed_summary if latest_failure else None
        ),
        attempts=attempts,
    )


def repair_history_status(
    *,
    ledger: list[TaskVerificationLedgerRecord],
    summary: TaskVerificationLedgerSummary,
    latest_failure: TaskVerificationLedgerRecord | None,
    retry_count: int,
    repaired_count: int,
) -> TaskRepairHistoryStatus:
    if not ledger:
        return "no_verification"
    if summary.running_count:
        return "repairing"
    if summary.accepted_risk_count:
        return "accepted_with_risk"
    latest_failure_sequence = (
        latest_failure.latest_failed_sequence if latest_failure else None
    )
    latest_success_sequence = summary.latest_success_sequence
    if latest_failure_sequence is not None and (
        latest_success_sequence is None
        or latest_failure_sequence > latest_success_sequence
    ):
        return "regressed" if latest_success_sequence is not None else "failed"
    if retry_count and repaired_count:
        return "repaired"
    if summary.passed_count == summary.total_count:
        return "clean"
    return "partial"


def repeated_failure_count_for_entries(
    entries: list[TaskVerificationLedgerRecord],
) -> int:
    seen: set[tuple[str | None, str | None]] = set()
    repeated = 0
    for entry in entries:
        category = (
            entry.latest_failed_category.value if entry.latest_failed_category else None
        )
        signature = (
            category,
            entry.latest_failed_summary,
        )
        if signature in seen:
            repeated += 1
        seen.add(signature)
    return repeated
