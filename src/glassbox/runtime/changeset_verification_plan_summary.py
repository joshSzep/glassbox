"""Shared verification-plan lifecycle summaries for changeset surfaces."""

from collections.abc import Sequence

from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import TaskVerificationStatus
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanLifecycleState
from glassbox.runtime.changeset_models import ChangesetVerificationPlanEntrySummary
from glassbox.runtime.changeset_models import ChangesetVerificationPlanLifecycleSummary
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.review_readiness_signals import dedupe_actions


def build_changeset_verification_plan_summary(
    *,
    plan_entries: Sequence[VerificationPlanEntry] = (),
    task_ledger: Sequence[TaskVerificationLedgerRecord] = (),
    readiness: ChangesetVerificationReadiness | None = None,
    safe_next_actions: Sequence[str] = (),
) -> ChangesetVerificationPlanLifecycleSummary:
    """Build a bounded lifecycle story without raw command output."""

    entries: dict[str, ChangesetVerificationPlanEntrySummary] = {}
    for entry in plan_entries:
        _upsert(entries, _summary_from_plan_entry(entry))
    if readiness is not None:
        for requirement in readiness.requirements:
            if requirement.verification_id is None:
                continue
            _upsert(
                entries,
                ChangesetVerificationPlanEntrySummary(
                    verification_id=requirement.verification_id,
                    check_name=requirement.check_name,
                    status=requirement.state.value,
                    lifecycle_state=_lifecycle_for_readiness_state(
                        requirement.state.value
                    ),
                    kind=requirement.kind.value
                    if requirement.kind is not None
                    else None,
                    source=(
                        requirement.source.value
                        if requirement.source is not None
                        else None
                    ),
                    command=[str(part) for part in requirement.command],
                    changed_paths=list(requirement.changed_paths),
                    blocking=requirement.blocking,
                    reason=requirement.reason,
                    artifact_id=requirement.artifact_id,
                    failure_summary=requirement.evidence_summary,
                ),
            )
    for record in task_ledger:
        _upsert(entries, _summary_from_ledger(record))

    ordered_entries = sorted(
        entries.values(),
        key=lambda item: (
            item.last_sequence is None,
            -(item.last_sequence or 0),
            item.check_name,
        ),
    )
    latest = next(
        (
            entry
            for entry in ordered_entries
            if entry.last_sequence is not None or entry.artifact_id is not None
        ),
        ordered_entries[0] if ordered_entries else None,
    )
    return ChangesetVerificationPlanLifecycleSummary(
        total_count=len(ordered_entries),
        proposed_count=_count_lifecycle(
            ordered_entries,
            VerificationPlanLifecycleState.PROPOSED.value,
        ),
        selected_count=_count_lifecycle(
            ordered_entries,
            VerificationPlanLifecycleState.SELECTED.value,
        ),
        running_count=_count_status(
            ordered_entries,
            TaskVerificationStatus.RUNNING.value,
        ),
        passed_count=_count_status(
            ordered_entries,
            TaskVerificationStatus.PASSED.value,
        ),
        failed_count=_count_status(
            ordered_entries,
            TaskVerificationStatus.FAILED.value,
        ),
        skipped_count=_count_status(
            ordered_entries,
            TaskVerificationStatus.SKIPPED.value,
        ),
        stale_count=_count_lifecycle(
            ordered_entries,
            VerificationPlanLifecycleState.STALE.value,
        ),
        accepted_risk_count=sum(entry.accepted_risk_count for entry in ordered_entries)
        + _count_status(
            ordered_entries,
            TaskVerificationStatus.ACCEPTED_WITH_RISK.value,
        ),
        manual_only_count=_count_lifecycle(
            ordered_entries,
            VerificationPlanLifecycleState.MANUAL_ONLY.value,
        ),
        command_count=sum(1 for entry in ordered_entries if entry.command),
        latest_verification_id=latest.verification_id if latest is not None else None,
        latest_status=latest.status if latest is not None else None,
        entries=ordered_entries[:20],
        safe_next_actions=dedupe_actions(safe_next_actions)[:20],
        non_claims=[
            "verification plan summary is local evidence, not reviewer approval",
            "passed checks do not imply publication, deployment, or release approval",
            "skipped and accepted-risk entries remain visible and are not passes",
        ],
    )


def _summary_from_plan_entry(
    entry: VerificationPlanEntry,
) -> ChangesetVerificationPlanEntrySummary:
    return ChangesetVerificationPlanEntrySummary(
        verification_id=entry.verification_id,
        check_name=entry.check_name,
        status=entry.lifecycle_state.value,
        lifecycle_state=entry.lifecycle_state.value,
        kind=entry.kind.value,
        source=entry.source.value,
        command=[str(part) for part in entry.command],
        changed_paths=[path.as_posix() for path in entry.changed_paths],
        blocking=entry.blocking,
        reason=entry.selection_rationale or entry.rationale,
        stale_reasons=list(entry.stale_reasons),
    )


def _summary_from_ledger(
    record: TaskVerificationLedgerRecord,
) -> ChangesetVerificationPlanEntrySummary:
    return ChangesetVerificationPlanEntrySummary(
        verification_id=record.verification_id,
        check_name=record.check_name,
        status=record.status.value,
        lifecycle_state=_lifecycle_for_ledger_status(record.status),
        kind=record.kind.value if record.kind is not None else None,
        source=record.source.value if record.source is not None else None,
        command=[str(part) for part in record.command],
        changed_paths=[path.as_posix() for path in record.changed_paths],
        blocking=record.blocking,
        reason=record.summary or record.latest_failed_summary,
        artifact_id=record.latest_artifact_id,
        failed_artifact_id=record.latest_failed_artifact_id,
        failure_summary=record.latest_failed_summary,
        accepted_risk_count=record.accepted_risk_count,
        accepted_risks=list(record.accepted_risks),
        last_sequence=record.last_sequence,
    )


def _upsert(
    entries: dict[str, ChangesetVerificationPlanEntrySummary],
    incoming: ChangesetVerificationPlanEntrySummary,
) -> None:
    key = str(incoming.verification_id)
    existing = entries.get(key)
    if existing is None:
        entries[key] = incoming
        return
    entries[key] = existing.model_copy(
        update={
            "status": incoming.status,
            "lifecycle_state": incoming.lifecycle_state,
            "kind": incoming.kind or existing.kind,
            "source": incoming.source or existing.source,
            "command": incoming.command or existing.command,
            "changed_paths": incoming.changed_paths or existing.changed_paths,
            "blocking": incoming.blocking,
            "reason": incoming.reason or existing.reason,
            "artifact_id": incoming.artifact_id or existing.artifact_id,
            "failed_artifact_id": (
                incoming.failed_artifact_id or existing.failed_artifact_id
            ),
            "failure_summary": incoming.failure_summary or existing.failure_summary,
            "accepted_risk_count": max(
                incoming.accepted_risk_count,
                existing.accepted_risk_count,
            ),
            "accepted_risks": incoming.accepted_risks or existing.accepted_risks,
            "stale_reasons": incoming.stale_reasons or existing.stale_reasons,
            "last_sequence": incoming.last_sequence or existing.last_sequence,
        }
    )


def _lifecycle_for_readiness_state(state: str) -> str:
    return {
        "passed": VerificationPlanLifecycleState.PASSED.value,
        "failed": VerificationPlanLifecycleState.FAILED.value,
        "stale": VerificationPlanLifecycleState.STALE.value,
        "accepted_with_risk": VerificationPlanLifecycleState.ACCEPTED_RISK.value,
    }.get(state, VerificationPlanLifecycleState.PROPOSED.value)


def _lifecycle_for_ledger_status(status: TaskVerificationStatus) -> str:
    return {
        TaskVerificationStatus.PLANNED: VerificationPlanLifecycleState.SELECTED.value,
        TaskVerificationStatus.RUNNING: VerificationPlanLifecycleState.RUNNING.value,
        TaskVerificationStatus.PASSED: VerificationPlanLifecycleState.PASSED.value,
        TaskVerificationStatus.FAILED: VerificationPlanLifecycleState.FAILED.value,
        TaskVerificationStatus.SKIPPED: VerificationPlanLifecycleState.SKIPPED.value,
        TaskVerificationStatus.CANCELLED: VerificationPlanLifecycleState.BLOCKED.value,
        TaskVerificationStatus.RETRIED: VerificationPlanLifecycleState.SUPERSEDED.value,
        TaskVerificationStatus.ACCEPTED_WITH_RISK: (
            VerificationPlanLifecycleState.ACCEPTED_RISK.value
        ),
    }[status]


def _count_lifecycle(
    entries: Sequence[ChangesetVerificationPlanEntrySummary],
    lifecycle_state: str,
) -> int:
    return sum(1 for entry in entries if entry.lifecycle_state == lifecycle_state)


def _count_status(
    entries: Sequence[ChangesetVerificationPlanEntrySummary],
    status: str,
) -> int:
    return sum(1 for entry in entries if entry.status == status)


__all__ = ["build_changeset_verification_plan_summary"]
