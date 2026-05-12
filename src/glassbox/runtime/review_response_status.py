"""Review feedback response status derivation helpers."""

from pathlib import Path

from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetVerificationState
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackFixupInventoryRecord
from glassbox.core import ReviewFeedbackFixupPathRecord
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewResponseState
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import TaskVerificationStatus
from glassbox.runtime.changeset_safe_commands import changeset_feedback_show_command
from glassbox.runtime.changeset_safe_commands import changeset_handoff_readiness_command
from glassbox.runtime.changeset_safe_commands import changeset_verification_plan_command
from glassbox.runtime.changeset_safe_commands import show_changeset_command
from glassbox.runtime.review_response_models import ReviewFeedbackResponseStatus
from glassbox.runtime.review_response_models import (
    ReviewFeedbackVerificationPlanEntryStatus,
)
from glassbox.runtime.review_response_models import ReviewFixupInventoryStatus


def review_feedback_response_status(
    *,
    feedback: ReviewFeedbackRecord,
    inventories: list[ReviewFeedbackFixupInventoryRecord],
    paths: list[ReviewFeedbackFixupPathRecord],
    freshness_status: ReviewFixupInventoryStatus | None = None,
    task_ledger: list[TaskVerificationLedgerRecord] | None = None,
) -> ReviewFeedbackResponseStatus:
    """Derive cautious response status from feedback and latest fixup evidence."""

    latest = inventories[0] if inventories else None
    status_stale = (
        latest.stale if freshness_status is None and latest is not None else False
    )
    status_reason = latest.stale_reason if latest is not None else None
    status_freshness = (
        latest.inventory_freshness
        if latest is not None
        else ChangesetInventoryFreshness.UNKNOWN
    )
    if freshness_status is not None:
        status_stale = freshness_status.stale
        status_reason = freshness_status.reason
        status_freshness = freshness_status.freshness
    (
        verification_state,
        verification_reason,
        verification_ids,
        verification_actions,
        verification_plan_entries,
        newly_required_check_count,
        verification_limitations,
    ) = _response_verification_state(
        feedback=feedback,
        latest=latest,
        paths=paths,
        task_ledger=task_ledger,
        freshness_stale=status_stale,
        freshness_reason=status_reason,
    )
    response_state = _response_state(
        feedback,
        has_fixup=latest is not None,
        stale=status_stale,
        verification_state=verification_state,
    )
    blockers = _response_blockers(
        feedback,
        latest=latest,
        stale=status_stale,
        stale_reason=status_reason,
        verification_state=verification_state,
        verification_reason=verification_reason,
    )
    safe_next_actions = [
        changeset_feedback_show_command(feedback.feedback_id),
        show_changeset_command(feedback.changeset_id),
        changeset_verification_plan_command(feedback.changeset_id),
        *verification_actions,
    ]
    if response_state == ReviewResponseState.READY_FOR_HANDOFF:
        safe_next_actions.append(
            changeset_handoff_readiness_command(feedback.changeset_id)
        )
    return ReviewFeedbackResponseStatus(
        feedback_id=feedback.feedback_id,
        changeset_id=feedback.changeset_id,
        response_state=response_state,
        disposition=feedback.disposition,
        summary=feedback.summary,
        fixup_inventory_count=len(inventories),
        latest_fixup_inventory_artifact_id=(
            latest.artifact_id if latest is not None else None
        ),
        latest_fixup_inventory_sequence=(
            latest.last_sequence if latest is not None else None
        ),
        latest_fixup_inventory_at=latest.created_at if latest is not None else None,
        latest_source_kind=latest.source_kind if latest is not None else None,
        latest_source_summary=latest.source_summary if latest is not None else None,
        inventory_freshness=status_freshness,
        stale=status_stale,
        stale_reason=status_reason,
        changed_path_count=latest.changed_path_count if latest is not None else 0,
        matched_scope_path_count=(
            latest.matched_scope_path_count if latest is not None else 0
        ),
        path_summaries=[path.summary for path in paths[:8]],
        verification_state=verification_state,
        verification_reason=verification_reason,
        verification_requirement_ids=verification_ids,
        verification_safe_next_actions=verification_actions,
        verification_plan_entries=verification_plan_entries,
        selected_plan_entry_count=sum(
            1 for entry in verification_plan_entries if entry.status == "planned"
        ),
        stale_plan_entry_count=sum(
            1 for entry in verification_plan_entries if entry.relationship == "stale"
        ),
        skipped_plan_entry_count=sum(
            1 for entry in verification_plan_entries if entry.status == "skipped"
        ),
        accepted_risk_plan_entry_count=sum(
            1
            for entry in verification_plan_entries
            if entry.status == "accepted_with_risk"
        ),
        newly_required_check_count=newly_required_check_count,
        verification_limitations=verification_limitations,
        blockers=blockers,
        safe_next_actions=list(dict.fromkeys(safe_next_actions)),
        non_claims=review_response_non_claims(),
    )


def review_fixup_inventory_status(
    *,
    feedback_id: ReviewFeedbackId,
    changeset_id: ChangesetId,
    recorded_source_digest: str | None,
    current_source_digest: str | None,
    current_error: str | None = None,
) -> ReviewFixupInventoryStatus:
    """Compare response-linked inventory evidence against current workspace state."""

    safe_next_actions = [
        changeset_feedback_show_command(feedback_id),
        changeset_verification_plan_command(changeset_id),
    ]
    if current_error is not None:
        return ReviewFixupInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason=f"workspace source digest unavailable: {current_error}",
            recorded_source_digest=recorded_source_digest,
            current_source_digest=current_source_digest,
            safe_next_actions=safe_next_actions,
        )
    if recorded_source_digest is None:
        return ReviewFixupInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason="fixup inventory has no recorded workspace source digest",
            recorded_source_digest=recorded_source_digest,
            current_source_digest=current_source_digest,
            safe_next_actions=safe_next_actions,
        )
    if recorded_source_digest != current_source_digest:
        return ReviewFixupInventoryStatus(
            freshness=ChangesetInventoryFreshness.STALE,
            stale=True,
            reason=(
                "workspace diff source digest changed since fixup inventory "
                "was recorded"
            ),
            recorded_source_digest=recorded_source_digest,
            current_source_digest=current_source_digest,
            safe_next_actions=safe_next_actions,
        )
    return ReviewFixupInventoryStatus(
        freshness=ChangesetInventoryFreshness.FRESH,
        stale=False,
        recorded_source_digest=recorded_source_digest,
        current_source_digest=current_source_digest,
        safe_next_actions=safe_next_actions,
    )


def review_response_non_claims() -> list[str]:
    """Return publication-boundary non-claims for review response surfaces."""

    return [
        "review response status is local evidence, not reviewer acceptance",
        "response inventory does not retain raw diffs or file contents",
        "Glassbox did not stage, commit, push, open a PR, or merge",
    ]


def _response_state(
    feedback: ReviewFeedbackRecord,
    *,
    has_fixup: bool,
    stale: bool,
    verification_state: ChangesetVerificationState,
) -> ReviewResponseState:
    disposition = feedback.disposition
    if disposition == ReviewFeedbackDisposition.ACCEPTED_WITH_RISK:
        return ReviewResponseState.ACCEPTED_WITH_RISK
    if disposition == ReviewFeedbackDisposition.ARCHIVED:
        return ReviewResponseState.NOT_APPLICABLE
    if stale:
        return ReviewResponseState.BLOCKED
    if verification_state in {
        ChangesetVerificationState.STALE,
        ChangesetVerificationState.FAILED,
    }:
        return ReviewResponseState.BLOCKED
    if verification_state == ChangesetVerificationState.MISSING and disposition in {
        ReviewFeedbackDisposition.RESPONDED,
        ReviewFeedbackDisposition.RESOLVED_LOCALLY,
    }:
        return ReviewResponseState.BLOCKED
    if disposition == ReviewFeedbackDisposition.OPEN and feedback.reopened_count > 0:
        return ReviewResponseState.REOPENED
    if disposition == ReviewFeedbackDisposition.RESOLVED_LOCALLY:
        if has_fixup and verification_state == ChangesetVerificationState.PASSED:
            return ReviewResponseState.READY_FOR_HANDOFF
        return (
            ReviewResponseState.RESOLVED if has_fixup else ReviewResponseState.BLOCKED
        )
    if disposition == ReviewFeedbackDisposition.RESPONDED:
        return (
            ReviewResponseState.RESPONDED if has_fixup else ReviewResponseState.BLOCKED
        )
    if disposition == ReviewFeedbackDisposition.IN_PROGRESS:
        return ReviewResponseState.IN_PROGRESS
    if has_fixup:
        return ReviewResponseState.RESPONDED
    return ReviewResponseState.PLANNED


def _response_blockers(
    feedback: ReviewFeedbackRecord,
    *,
    latest: ReviewFeedbackFixupInventoryRecord | None,
    stale: bool,
    stale_reason: str | None,
    verification_state: ChangesetVerificationState,
    verification_reason: str | None,
) -> list[str]:
    blockers: list[str] = []
    if stale:
        blockers.append(stale_reason or "response-linked fixup inventory is stale")
    if verification_state in {
        ChangesetVerificationState.STALE,
        ChangesetVerificationState.FAILED,
    }:
        blockers.append(
            verification_reason
            or f"response verification is {verification_state.value}"
        )
    if (
        verification_state == ChangesetVerificationState.MISSING
        and latest is not None
        and feedback.disposition
        in {
            ReviewFeedbackDisposition.RESPONDED,
            ReviewFeedbackDisposition.RESOLVED_LOCALLY,
        }
    ):
        blockers.append(verification_reason or "response verification is missing")
    if latest is None and feedback.disposition in {
        ReviewFeedbackDisposition.RESPONDED,
        ReviewFeedbackDisposition.RESOLVED_LOCALLY,
    }:
        blockers.append(
            "feedback disposition cites a response but no fixup inventory is linked"
        )
    if latest is None and feedback.disposition == ReviewFeedbackDisposition.OPEN:
        blockers.append("feedback has no response-linked fixup inventory yet")
    return blockers


def _response_verification_state(
    *,
    feedback: ReviewFeedbackRecord,
    latest: ReviewFeedbackFixupInventoryRecord | None,
    paths: list[ReviewFeedbackFixupPathRecord],
    task_ledger: list[TaskVerificationLedgerRecord] | None,
    freshness_stale: bool,
    freshness_reason: str | None,
) -> tuple[
    ChangesetVerificationState,
    str | None,
    list[str],
    list[str],
    list[ReviewFeedbackVerificationPlanEntryStatus],
    int,
    list[str],
]:
    if feedback.disposition == ReviewFeedbackDisposition.ACCEPTED_WITH_RISK:
        return (
            ChangesetVerificationState.ACCEPTED_WITH_RISK,
            "feedback response is accepted with local risk",
            [],
            [changeset_feedback_show_command(feedback.feedback_id)],
            [],
            0,
            ["accepted risk is local evidence and does not mark checks passed"],
        )
    if latest is None:
        return (
            ChangesetVerificationState.MISSING,
            "feedback has no response-linked fixup inventory to verify",
            [],
            [changeset_verification_plan_command(feedback.changeset_id)],
            [],
            1,
            ["record response-linked fixup inventory before mapping checks"],
        )
    if freshness_stale:
        return (
            ChangesetVerificationState.STALE,
            freshness_reason
            or "response-linked fixup inventory is stale against workspace state",
            [f"fixup-inventory:{latest.artifact_id}"],
            [changeset_verification_plan_command(feedback.changeset_id)],
            [],
            1,
            ["refresh fixup inventory before trusting response verification"],
        )
    if latest.changed_path_count > 0 and latest.matched_scope_path_count == 0:
        return (
            ChangesetVerificationState.MISSING,
            "fixup inventory has no path records matching feedback scope",
            [f"fixup-inventory:{latest.artifact_id}"],
            [changeset_feedback_show_command(feedback.feedback_id)],
            [],
            1,
            ["verification cannot be mapped until fixup paths match feedback scope"],
        )
    if task_ledger is None:
        return (
            ChangesetVerificationState.NOT_APPLICABLE,
            "verification ledger was not available for this response surface",
            [],
            [changeset_verification_plan_command(feedback.changeset_id)],
            [],
            0,
            ["verification ledger was unavailable for response-plan linking"],
        )

    response_paths = {_normalize_path(path.path) for path in paths}
    if latest.changed_path_count > 0 and not response_paths:
        return (
            ChangesetVerificationState.MISSING,
            "fixup inventory has no path records, so verification cannot be mapped",
            [f"fixup-inventory:{latest.artifact_id}"],
            [changeset_verification_plan_command(feedback.changeset_id)],
            [],
            1,
            ["response-linked evidence has no paths for verification matching"],
        )
    matching_entries = [
        entry
        for entry in task_ledger
        if response_paths.intersection(
            {_normalize_path(path) for path in entry.changed_paths}
        )
    ]
    if not matching_entries:
        return (
            ChangesetVerificationState.MISSING,
            "no retained verification check targets response-linked fixup paths",
            [f"fixup-inventory:{latest.artifact_id}"],
            [
                (
                    "select or record verification for response-linked paths with "
                    f"{changeset_verification_plan_command(feedback.changeset_id)}"
                )
            ],
            [],
            1,
            ["no selected, skipped, or accepted-risk check overlaps fixup paths"],
        )
    plan_entries = [
        _plan_entry_status(
            entry,
            latest=latest,
            response_paths=response_paths,
        )
        for entry in sorted(
            matching_entries,
            key=lambda candidate: candidate.last_sequence,
            reverse=True,
        )[:10]
    ]
    entry = max(matching_entries, key=lambda candidate: candidate.last_sequence)
    state = _verification_state_for_task_status(entry.status)
    evidence_sequence = entry.last_success_sequence or entry.last_sequence
    if (
        state == ChangesetVerificationState.PASSED
        and latest.last_sequence is not None
        and evidence_sequence < latest.last_sequence
    ):
        command = _ledger_command(entry)
        return (
            ChangesetVerificationState.STALE,
            (
                f"{entry.check_name} passed before response-linked fixup inventory "
                "changed overlapping paths"
            ),
            [str(entry.verification_id), f"fixup-inventory:{latest.artifact_id}"],
            [
                (
                    f"rerun {command} because {entry.check_name} predates "
                    "response-linked fixups"
                )
            ],
            plan_entries,
            0,
            ["fresh verification requires evidence newer than the fixup inventory"],
        )
    reason = _verification_reason(entry, state)
    actions = (
        [] if state == ChangesetVerificationState.PASSED else [_retry_action(entry)]
    )
    return (
        state,
        reason,
        [str(entry.verification_id), f"fixup-inventory:{latest.artifact_id}"],
        actions,
        plan_entries,
        0,
        _plan_limitations_for_entries(plan_entries),
    )


def _verification_state_for_task_status(
    status: TaskVerificationStatus,
) -> ChangesetVerificationState:
    if status == TaskVerificationStatus.PLANNED:
        return ChangesetVerificationState.PLANNED
    if status == TaskVerificationStatus.RUNNING:
        return ChangesetVerificationState.RUNNING
    if status == TaskVerificationStatus.PASSED:
        return ChangesetVerificationState.PASSED
    if status in {TaskVerificationStatus.FAILED, TaskVerificationStatus.CANCELLED}:
        return ChangesetVerificationState.FAILED
    if status == TaskVerificationStatus.SKIPPED:
        return ChangesetVerificationState.SKIPPED
    if status == TaskVerificationStatus.ACCEPTED_WITH_RISK:
        return ChangesetVerificationState.ACCEPTED_WITH_RISK
    return ChangesetVerificationState.MISSING


def _verification_reason(
    entry: TaskVerificationLedgerRecord,
    state: ChangesetVerificationState,
) -> str:
    if state == ChangesetVerificationState.PASSED:
        return f"{entry.check_name} is fresh for response-linked fixup paths"
    if state == ChangesetVerificationState.FAILED:
        return entry.latest_failed_summary or f"{entry.check_name} failed"
    if state == ChangesetVerificationState.SKIPPED:
        return f"{entry.check_name} was skipped for response-linked fixup paths"
    if state == ChangesetVerificationState.ACCEPTED_WITH_RISK:
        return entry.residual_risk_reason or f"{entry.check_name} accepted with risk"
    return f"{entry.check_name} is {state.value} for response-linked fixup paths"


def _retry_action(entry: TaskVerificationLedgerRecord) -> str:
    command = _ledger_command(entry)
    if command:
        return f"rerun {command} for response-linked fixup paths"
    return f"inspect retained verification {entry.verification_id} before retrying"


def _ledger_command(entry: TaskVerificationLedgerRecord) -> str:
    return " ".join(str(part) for part in entry.command).strip()


def _normalize_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").strip().lstrip("./")


def _plan_entry_status(
    entry: TaskVerificationLedgerRecord,
    *,
    latest: ReviewFeedbackFixupInventoryRecord,
    response_paths: set[str],
) -> ReviewFeedbackVerificationPlanEntryStatus:
    relationship = _plan_relationship(entry, latest=latest)
    reason = (
        f"{entry.check_name} passed before response-linked fixup inventory changed "
        "overlapping paths"
        if relationship == "stale"
        else _verification_reason(
            entry,
            _verification_state_for_task_status(entry.status),
        )
    )
    safe_next_actions = []
    if relationship == "stale":
        command = _ledger_command(entry)
        if command:
            safe_next_actions.append(
                f"rerun {command} because response-linked fixups are newer"
            )
    elif entry.status in {
        TaskVerificationStatus.FAILED,
        TaskVerificationStatus.CANCELLED,
        TaskVerificationStatus.SKIPPED,
    }:
        safe_next_actions.append(_retry_action(entry))
    return ReviewFeedbackVerificationPlanEntryStatus(
        verification_id=entry.verification_id,
        check_name=entry.check_name,
        status=entry.status.value,
        relationship=relationship,
        reason=reason,
        command=[str(part) for part in entry.command],
        changed_paths=[
            path.as_posix()
            for path in entry.changed_paths
            if _normalize_path(path) in response_paths
        ],
        safe_next_actions=safe_next_actions,
    )


def _plan_relationship(
    entry: TaskVerificationLedgerRecord,
    *,
    latest: ReviewFeedbackFixupInventoryRecord,
) -> str:
    if (
        entry.status == TaskVerificationStatus.PASSED
        and latest.last_sequence is not None
        and (entry.last_success_sequence or entry.last_sequence) < latest.last_sequence
    ):
        return "stale"
    if entry.status == TaskVerificationStatus.PLANNED:
        return "selected"
    if entry.status == TaskVerificationStatus.SKIPPED:
        return "skipped"
    if entry.status == TaskVerificationStatus.ACCEPTED_WITH_RISK:
        return "accepted-risk"
    if entry.status == TaskVerificationStatus.PASSED:
        return "fresh"
    if entry.status in {
        TaskVerificationStatus.FAILED,
        TaskVerificationStatus.CANCELLED,
    }:
        return "failed"
    return "affected"


def _plan_limitations_for_entries(
    entries: list[ReviewFeedbackVerificationPlanEntryStatus],
) -> list[str]:
    limitations: list[str] = []
    if any(entry.relationship == "stale" for entry in entries):
        limitations.append("one or more checks predate response-linked fixup paths")
    if any(entry.relationship == "skipped" for entry in entries):
        limitations.append("skipped checks remain visible and are not passes")
    if any(entry.relationship == "accepted-risk" for entry in entries):
        limitations.append("accepted-risk checks are local evidence, not approval")
    return limitations


__all__ = [
    "review_feedback_response_status",
    "review_fixup_inventory_status",
    "review_response_non_claims",
]
