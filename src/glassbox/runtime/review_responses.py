"""Review response and fixup inventory artifact helpers."""

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetVerificationState
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackFixupInventoryRecord
from glassbox.core import ReviewFeedbackFixupPathRecord
from glassbox.core import ReviewFeedbackFixupPathSummary
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.core import ReviewFixupSourceKind
from glassbox.core import ReviewResponseState
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import TaskVerificationStatus
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.change_inventory import ChangeInventoryPathEntry
from glassbox.runtime.changeset_safe_commands import changeset_feedback_show_command
from glassbox.runtime.changeset_safe_commands import changeset_handoff_readiness_command
from glassbox.runtime.changeset_safe_commands import changeset_verification_plan_command
from glassbox.runtime.changeset_safe_commands import show_changeset_command

REVIEW_FIXUP_INVENTORY_ARTIFACT_KIND = "review_feedback_fixup_inventory"
REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION = 1


class ReviewFixupInventoryStatus(BaseModel):
    """Freshness posture for response-linked fixup inventory."""

    model_config = ConfigDict(extra="forbid")

    freshness: ChangesetInventoryFreshness
    stale: bool = False
    reason: str | None = Field(default=None, max_length=2000)
    recorded_source_digest: str | None = Field(default=None, max_length=256)
    current_source_digest: str | None = Field(default=None, max_length=256)
    safe_next_actions: list[str] = Field(default_factory=list)


class ReviewFixupInventoryArtifact(BaseModel):
    """Artifact describing bounded fixup paths linked to one feedback item."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["review_feedback_fixup_inventory"] = (
        REVIEW_FIXUP_INVENTORY_ARTIFACT_KIND
    )
    schema_version: Literal[1] = REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION
    changeset_id: ChangesetId
    feedback_id: ReviewFeedbackId
    source_kind: ReviewFixupSourceKind
    source_summary: str = Field(min_length=1, max_length=2000)
    latest_changeset_inventory_artifact_id: str | None = None
    source_digest: str | None = Field(default=None, max_length=256)
    inventory_freshness: ChangesetInventoryFreshness
    changed_path_count: int = Field(ge=0)
    matched_scope_path_count: int = Field(ge=0)
    paths: list[ReviewFeedbackFixupPathSummary] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ReviewFeedbackResponseStatus(BaseModel):
    """Derived response posture for one feedback item."""

    model_config = ConfigDict(extra="forbid")

    feedback_id: ReviewFeedbackId
    changeset_id: ChangesetId
    response_state: ReviewResponseState
    disposition: ReviewFeedbackDisposition
    summary: str
    fixup_inventory_count: int = Field(ge=0)
    latest_fixup_inventory_artifact_id: ArtifactId | None = None
    latest_fixup_inventory_sequence: int | None = None
    latest_fixup_inventory_at: datetime | None = None
    latest_source_kind: ReviewFixupSourceKind | None = None
    latest_source_summary: str | None = None
    inventory_freshness: ChangesetInventoryFreshness
    stale: bool = False
    stale_reason: str | None = Field(default=None, max_length=2000)
    changed_path_count: int = Field(default=0, ge=0)
    matched_scope_path_count: int = Field(default=0, ge=0)
    path_summaries: list[str] = Field(default_factory=list)
    verification_state: ChangesetVerificationState = (
        ChangesetVerificationState.NOT_APPLICABLE
    )
    verification_reason: str | None = Field(default=None, max_length=2000)
    verification_requirement_ids: list[str] = Field(default_factory=list)
    verification_safe_next_actions: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ChangesetReviewResponseSummary(BaseModel):
    """Derived response summary for all feedback on one changeset."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    total_feedback_count: int = Field(ge=0)
    open_count: int = Field(ge=0)
    responded_count: int = Field(ge=0)
    unresolved_count: int = Field(ge=0)
    stale_response_count: int = Field(ge=0)
    accepted_risk_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    items: list[ReviewFeedbackResponseStatus] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


def review_fixup_inventory_from_change_inventory(
    inventory: ChangeInventoryArtifact,
    *,
    feedback: ReviewFeedbackRecord,
    scopes: list[ReviewFeedbackScopeRecord],
    source_kind: ReviewFixupSourceKind,
    source_summary: str,
    source_digest: str | None,
    inventory_freshness: ChangesetInventoryFreshness,
    latest_changeset_inventory_artifact_id: str | None = None,
) -> ReviewFixupInventoryArtifact:
    """Build a bounded response-linked inventory artifact from a change inventory."""

    scope_paths = _feedback_scope_paths(scopes)
    paths = [
        _path_summary(entry, matches_feedback_scope=_matches_scope(entry, scope_paths))
        for entry in inventory.paths[:100]
    ]
    matched_scope_path_count = sum(1 for path in paths if path.matches_feedback_scope)
    limitations = [
        *inventory.limitations,
        (
            "fixup inventory is summary-only and does not include raw diffs or "
            "file contents"
        ),
    ]
    if not scope_paths:
        limitations.append("feedback has no file scope; all changed paths need review")
    elif matched_scope_path_count == 0 and paths:
        limitations.append(
            "no changed path directly matched the feedback file scope; inspect "
            "response context"
        )
    return ReviewFixupInventoryArtifact(
        changeset_id=feedback.changeset_id,
        feedback_id=feedback.feedback_id,
        source_kind=source_kind,
        source_summary=source_summary,
        latest_changeset_inventory_artifact_id=latest_changeset_inventory_artifact_id,
        source_digest=source_digest,
        inventory_freshness=inventory_freshness,
        changed_path_count=inventory.summary.changed_path_count,
        matched_scope_path_count=matched_scope_path_count,
        paths=paths,
        limitations=list(dict.fromkeys(limitations)),
        non_claims=[
            "fixup inventory is response evidence, not reviewer acceptance",
            (
                "manual or external edits remain manual unless retained "
                "instrumentation says otherwise"
            ),
            "Glassbox did not stage, commit, push, open a PR, or merge",
        ],
    )


def review_fixup_inventory_artifact_json(
    artifact: ReviewFixupInventoryArtifact,
) -> str:
    """Serialize a response-linked inventory artifact with stable key ordering."""

    return json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


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
    verification_state, verification_reason, verification_ids, verification_actions = (
        _response_verification_state(
            feedback=feedback,
            latest=latest,
            paths=paths,
            task_ledger=task_ledger,
            freshness_stale=status_stale,
            freshness_reason=status_reason,
        )
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
        blockers=blockers,
        safe_next_actions=list(dict.fromkeys(safe_next_actions)),
        non_claims=_review_response_non_claims(),
    )


def changeset_review_response_summary(
    *,
    changeset_id: ChangesetId,
    items: list[ReviewFeedbackResponseStatus],
) -> ChangesetReviewResponseSummary:
    """Summarize derived response status rows for one changeset."""

    unresolved_states = {
        ReviewResponseState.PLANNED,
        ReviewResponseState.IN_PROGRESS,
        ReviewResponseState.RESPONDED,
        ReviewResponseState.REOPENED,
        ReviewResponseState.BLOCKED,
    }
    blockers = [
        f"{item.feedback_id}: {blocker}" for item in items for blocker in item.blockers
    ]
    return ChangesetReviewResponseSummary(
        changeset_id=changeset_id,
        total_feedback_count=len(items),
        open_count=sum(
            1
            for item in items
            if item.disposition
            in {
                ReviewFeedbackDisposition.OPEN,
                ReviewFeedbackDisposition.IN_PROGRESS,
            }
        ),
        responded_count=sum(
            1
            for item in items
            if item.response_state
            in {
                ReviewResponseState.RESPONDED,
                ReviewResponseState.RESOLVED,
                ReviewResponseState.READY_FOR_HANDOFF,
            }
        ),
        unresolved_count=sum(
            1 for item in items if item.response_state in unresolved_states
        ),
        stale_response_count=sum(
            1
            for item in items
            if item.stale or item.verification_state == ChangesetVerificationState.STALE
        ),
        accepted_risk_count=sum(
            1
            for item in items
            if item.response_state == ReviewResponseState.ACCEPTED_WITH_RISK
        ),
        blocked_count=sum(
            1 for item in items if item.response_state == ReviewResponseState.BLOCKED
        ),
        items=items,
        blockers=blockers,
        safe_next_actions=[
            f"glassbox changeset feedback list --changeset {changeset_id} --cwd .",
            show_changeset_command(changeset_id),
        ],
        non_claims=_review_response_non_claims(),
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
) -> tuple[ChangesetVerificationState, str | None, list[str], list[str]]:
    if feedback.disposition == ReviewFeedbackDisposition.ACCEPTED_WITH_RISK:
        return (
            ChangesetVerificationState.ACCEPTED_WITH_RISK,
            "feedback response is accepted with local risk",
            [],
            [changeset_feedback_show_command(feedback.feedback_id)],
        )
    if latest is None:
        return (
            ChangesetVerificationState.MISSING,
            "feedback has no response-linked fixup inventory to verify",
            [],
            [changeset_verification_plan_command(feedback.changeset_id)],
        )
    if freshness_stale:
        return (
            ChangesetVerificationState.STALE,
            freshness_reason
            or "response-linked fixup inventory is stale against workspace state",
            [f"fixup-inventory:{latest.artifact_id}"],
            [changeset_verification_plan_command(feedback.changeset_id)],
        )
    if latest.changed_path_count > 0 and latest.matched_scope_path_count == 0:
        return (
            ChangesetVerificationState.MISSING,
            "fixup inventory has no path records matching feedback scope",
            [f"fixup-inventory:{latest.artifact_id}"],
            [changeset_feedback_show_command(feedback.feedback_id)],
        )
    if task_ledger is None:
        return (
            ChangesetVerificationState.NOT_APPLICABLE,
            "verification ledger was not available for this response surface",
            [],
            [changeset_verification_plan_command(feedback.changeset_id)],
        )

    response_paths = {_normalize_path(path.path) for path in paths}
    if latest.changed_path_count > 0 and not response_paths:
        return (
            ChangesetVerificationState.MISSING,
            "fixup inventory has no path records, so verification cannot be mapped",
            [f"fixup-inventory:{latest.artifact_id}"],
            [changeset_verification_plan_command(feedback.changeset_id)],
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
            [changeset_verification_plan_command(feedback.changeset_id)],
        )
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


def _review_response_non_claims() -> list[str]:
    return [
        "review response status is local evidence, not reviewer acceptance",
        "response inventory does not retain raw diffs or file contents",
        "Glassbox did not stage, commit, push, open a PR, or merge",
    ]


def _feedback_scope_paths(scopes: list[ReviewFeedbackScopeRecord]) -> set[str]:
    return {
        _normalize_path(scope.file_path)
        for scope in scopes
        if scope.file_path is not None
    }


def _matches_scope(
    entry: ChangeInventoryPathEntry,
    scope_paths: set[str],
) -> bool:
    if not scope_paths:
        return False
    path = _normalize_path(entry.path)
    return path in scope_paths or any(
        path.startswith(f"{scope_path}/") for scope_path in scope_paths
    )


def _path_summary(
    entry: ChangeInventoryPathEntry,
    *,
    matches_feedback_scope: bool,
) -> ReviewFeedbackFixupPathSummary:
    return ReviewFeedbackFixupPathSummary(
        path=entry.path,
        change_kind=entry.change_kind,
        generated=entry.generated,
        test_file=entry.test_file,
        docs_file=entry.docs_file,
        policy_sensitive=entry.policy_sensitive,
        risk_level=entry.risk_level,
        provenance_confidence=entry.provenance_confidence,
        matches_feedback_scope=matches_feedback_scope,
        summary=_safe_path_summary(
            entry, matches_feedback_scope=matches_feedback_scope
        ),
    )


def _safe_path_summary(
    entry: ChangeInventoryPathEntry,
    *,
    matches_feedback_scope: bool,
) -> str:
    labels: list[str] = []
    if matches_feedback_scope:
        labels.append("matches feedback scope")
    if entry.generated:
        labels.append("generated output")
    if entry.test_file:
        labels.append("test path")
    if entry.docs_file:
        labels.append("docs path")
    if entry.policy_sensitive:
        labels.append("policy-sensitive path")
    if entry.risk_level in {"high", "medium"}:
        labels.append(f"{entry.risk_level} risk")
    if entry.provenance_confidence == "unknown":
        labels.append("manual or external provenance")
    if not labels:
        labels.append("changed path")
    return f"{entry.path}: {', '.join(labels)}"


def _normalize_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").strip().lstrip("./")


__all__ = [
    "REVIEW_FIXUP_INVENTORY_ARTIFACT_KIND",
    "REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION",
    "ReviewFixupInventoryArtifact",
    "ReviewFixupInventoryStatus",
    "ReviewFeedbackResponseStatus",
    "ChangesetReviewResponseSummary",
    "changeset_review_response_summary",
    "review_feedback_response_status",
    "review_fixup_inventory_artifact_json",
    "review_fixup_inventory_from_change_inventory",
    "review_fixup_inventory_status",
]
