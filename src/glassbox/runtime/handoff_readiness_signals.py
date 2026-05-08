"""Handoff-readiness signal builders and advisory action helpers."""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetVerificationState
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceState
from glassbox.core import TaskVerificationId
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_safe_commands import changeset_brief_command
from glassbox.runtime.changeset_safe_commands import changeset_evidence_list_command
from glassbox.runtime.changeset_safe_commands import changeset_feedback_status_command
from glassbox.runtime.changeset_safe_commands import changeset_refresh_command
from glassbox.runtime.changeset_safe_commands import changeset_verification_plan_command
from glassbox.runtime.changeset_safe_commands import show_changeset_command
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.runtime.review_readiness_signals import dedupe_actions
from glassbox.runtime.review_readiness_signals import first_blocking_state
from glassbox.runtime.review_readiness_signals import has_signal_state
from glassbox.runtime.review_readiness_signals import latest_readiness
from glassbox.runtime.review_readiness_signals import limitations_for_signal_ids
from glassbox.runtime.review_readiness_signals import signal_ids
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.skipped_evidence import skipped_live_evidence_items

HandoffReadinessState = Literal[
    "not_ready",
    "needs_review_response",
    "needs_verification",
    "stale_inventory",
    "unresolved_risk",
    "handoff_ready",
    "commit_prep_ready",
    "publication_blocked",
    "accepted_with_risk",
]


class HandoffReadinessSignal(BaseModel):
    """One evidence-backed reason contributing to handoff readiness."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1, max_length=200)
    state: HandoffReadinessState
    summary: str = Field(min_length=1, max_length=2000)
    blocking: bool = True
    paths: list[str] = Field(default_factory=list, max_length=100)


def build_handoff_readiness_signals(
    *,
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
    inventory_status: ChangesetInventoryStatus,
    verification_plan: ChangesetVerificationPlanPreview,
    review_briefs: Sequence[ChangesetReviewBriefRecord],
    review_response_summary: ChangesetReviewResponseSummary,
    manual_evidence: Sequence[ManualEvidenceRecord],
    readiness: Sequence[ChangesetReadinessRecord],
    commit_readiness: CommitReadinessAssessment,
) -> list[HandoffReadinessSignal]:
    """Build all handoff-readiness signals in stable product order."""

    signals: list[HandoffReadinessSignal] = []
    signals.extend(_publication_boundary_signals(changeset, commit_readiness))
    signals.extend(_provenance_signals(changeset, inventory))
    signals.extend(_inventory_signals(inventory, inventory_status))
    signals.extend(_review_response_signals(changeset, review_response_summary))
    signals.extend(_verification_signals(verification_plan))
    signals.extend(
        _brief_signals(changeset, inventory, verification_plan, review_briefs)
    )
    signals.extend(_risk_signals(changeset, verification_plan, review_response_summary))
    signals.extend(_manual_evidence_signals(changeset, manual_evidence))
    signals.extend(_prior_readiness_signals(readiness))
    return signals


def aggregate_handoff_state(
    signals: Sequence[HandoffReadinessSignal],
    commit_readiness: CommitReadinessAssessment,
) -> HandoffReadinessState:
    """Return the advisory handoff-readiness state for signal precedence."""

    blocking_state = first_blocking_state(
        signals,
        (
            "publication_blocked",
            "stale_inventory",
            "needs_review_response",
            "needs_verification",
            "not_ready",
            "unresolved_risk",
        ),
    )
    if blocking_state is not None:
        return blocking_state
    if has_signal_state(signals, "accepted_with_risk"):
        return "accepted_with_risk"
    if commit_readiness.state == ChangesetReadinessState.READY:
        return "commit_prep_ready"
    return "handoff_ready"


def handoff_safe_next_actions(
    *,
    changeset_id: ChangesetId,
    state: HandoffReadinessState,
    signals: Sequence[HandoffReadinessSignal],
    verification_actions: Sequence[str],
    response_actions: Sequence[str],
) -> list[str]:
    """Return bounded safe next actions for handoff readiness."""

    actions = [
        show_changeset_command(changeset_id),
    ]
    ids = signal_ids(signals)
    if state == "stale_inventory" or "dirty-workspace-ambiguity" in ids:
        actions.append("git status --short")
        actions.append(changeset_refresh_command(changeset_id))
    if state == "needs_review_response":
        actions.append(changeset_feedback_status_command(changeset_id))
        actions.extend(response_actions)
    if state == "needs_verification":
        actions.append(changeset_verification_plan_command(changeset_id))
        actions.extend(verification_actions)
    if "lifecycle-brief-missing" in ids or state == "not_ready":
        actions.append(changeset_brief_command(changeset_id))
    if state in {"handoff_ready", "commit_prep_ready", "accepted_with_risk"}:
        actions.append(f"glassbox changeset handoff-readiness {changeset_id} --cwd .")
        actions.append(f"glassbox changeset commit-prep {changeset_id} --cwd .")
    if "local-only-evidence" in ids:
        actions.append(changeset_evidence_list_command(changeset_id))
    if "skipped-live-evidence" in ids:
        actions.append(changeset_evidence_list_command(changeset_id))
    return dedupe_actions(actions)


def handoff_limitations(signals: Sequence[HandoffReadinessSignal]) -> list[str]:
    """Return handoff limitations implied by non-blocking advisory signals."""

    return limitations_for_signal_ids(
        signals,
        {
            "local-only-evidence": (
                "local-only evidence can support local handoff context but must be "
                "reviewed before export or publication"
            ),
            "stale-manual-evidence": (
                "stale manual evidence is advisory context and should be inspected "
                "before it is reused outside the local handoff"
            ),
            "manual-evidence-needs-inspection": (
                "manual evidence marked needs-inspection is advisory context, not "
                "fresh deterministic verification"
            ),
            "no-review-feedback": (
                "no retained review feedback exists; handoff must not claim "
                "reviewer input"
            ),
            "no-manual-evidence": (
                "no retained manual evidence exists; external checks or "
                "observations are not claimed"
            ),
            "skipped-live-evidence": (
                "skipped browser, dashboard, or accessibility evidence remains "
                "advisory context and is not a pass"
            ),
        }.items(),
    )


def _publication_boundary_signals(
    changeset: ChangesetRecord,
    commit_readiness: CommitReadinessAssessment,
) -> list[HandoffReadinessSignal]:
    signals: list[HandoffReadinessSignal] = []
    if changeset.status != "active":
        signals.append(
            HandoffReadinessSignal(
                signal_id="changeset-not-active",
                state="publication_blocked",
                summary=(
                    f"changeset status is {changeset.status}; inspect archived or "
                    "replacement evidence before handoff"
                ),
            )
        )
    if commit_readiness.git.error is not None:
        signals.append(
            HandoffReadinessSignal(
                signal_id="git-inspection-error",
                state="publication_blocked",
                summary=(
                    f"git status could not be inspected: {commit_readiness.git.error}"
                ),
            )
        )
    dirty_paths = [
        path
        for path in dict.fromkeys(commit_readiness.git.untracked_paths)
        if not path.startswith(".glassbox/")
    ]
    if dirty_paths:
        signals.append(
            HandoffReadinessSignal(
                signal_id="dirty-workspace-ambiguity",
                state="not_ready",
                summary=(
                    "workspace has untracked paths; inspect before "
                    "treating handoff evidence as current"
                ),
                paths=dirty_paths[:100],
            )
        )
    return signals


def _provenance_signals(
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
) -> list[HandoffReadinessSignal]:
    if inventory is None and changeset.latest_inventory_artifact_id is None:
        return [
            HandoffReadinessSignal(
                signal_id="inventory-missing",
                state="stale_inventory",
                summary="handoff requires a structured changeset inventory",
            )
        ]
    return []


def _inventory_signals(
    inventory: ChangesetInventoryRecord | None,
    inventory_status: ChangesetInventoryStatus,
) -> list[HandoffReadinessSignal]:
    if inventory is None:
        return [
            HandoffReadinessSignal(
                signal_id="inventory-missing",
                state="stale_inventory",
                summary="structured changeset inventory is missing",
            )
        ]
    if (
        inventory_status.stale
        or inventory_status.freshness != ChangesetInventoryFreshness.FRESH
    ):
        return [
            HandoffReadinessSignal(
                signal_id="inventory-stale",
                state="stale_inventory",
                summary=(
                    inventory_status.reason
                    or "structured changeset inventory is stale or unknown"
                ),
            )
        ]
    return []


def _review_response_signals(
    changeset: ChangesetRecord,
    summary: ChangesetReviewResponseSummary,
) -> list[HandoffReadinessSignal]:
    signals: list[HandoffReadinessSignal] = []
    if summary.unresolved_count > 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="unresolved-review-feedback",
                state="needs_review_response",
                summary=(
                    f"{summary.unresolved_count} review feedback item"
                    f"{'' if summary.unresolved_count == 1 else 's'} still "
                    "need response"
                ),
            )
        )
    if summary.stale_response_count > 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="stale-review-response",
                state="needs_review_response",
                summary=(
                    f"{summary.stale_response_count} review response"
                    f"{'' if summary.stale_response_count == 1 else 's'} "
                    "need inspection"
                ),
            )
        )
    for blocker in summary.blockers[:5]:
        signals.append(
            HandoffReadinessSignal(
                signal_id="review-response-blocker",
                state="needs_review_response",
                summary=blocker,
            )
        )
    if not signals and summary.total_feedback_count == 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="no-review-feedback",
                state="handoff_ready",
                summary=(
                    f"no local review feedback is attached to changeset "
                    f"{changeset.changeset_id}; handoff summary must not claim review"
                ),
                blocking=False,
            )
        )
    return signals


def _verification_signals(
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[HandoffReadinessSignal]:
    readiness = verification_plan.readiness
    if readiness.state == ChangesetVerificationState.PASSED:
        return []
    return [
        HandoffReadinessSignal(
            signal_id="verification-not-passed",
            state="needs_verification",
            summary=(
                f"verification readiness is {readiness.state.value}: "
                f"{readiness.summary}"
            ),
            paths=verification_plan.changed_paths[:100],
        )
    ]


def _brief_signals(
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
    review_briefs: Sequence[ChangesetReviewBriefRecord],
) -> list[HandoffReadinessSignal]:
    if not review_briefs:
        return [
            HandoffReadinessSignal(
                signal_id="lifecycle-brief-missing",
                state="not_ready",
                summary="handoff needs a current lifecycle review brief",
            )
        ]
    latest = review_briefs[0]
    if inventory is not None and latest.inventory_artifact_id != inventory.artifact_id:
        return [
            HandoffReadinessSignal(
                signal_id="lifecycle-brief-stale-inventory",
                state="not_ready",
                summary="latest lifecycle review brief does not cite current inventory",
            )
        ]
    verification_id = _verification_id(changeset, verification_plan)
    if verification_id is not None and latest.verification_id != verification_id:
        return [
            HandoffReadinessSignal(
                signal_id="lifecycle-brief-stale-verification",
                state="not_ready",
                summary=(
                    "latest lifecycle review brief does not cite current verification"
                ),
            )
        ]
    return []


def _risk_signals(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
    review_response_summary: ChangesetReviewResponseSummary,
) -> list[HandoffReadinessSignal]:
    signals: list[HandoffReadinessSignal] = []
    if changeset.unresolved_risk_count > 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="unresolved-risk",
                state="unresolved_risk",
                summary=(
                    f"{changeset.unresolved_risk_count} unresolved changeset risk"
                    f"{'' if changeset.unresolved_risk_count == 1 else 's'} remain"
                ),
            )
        )
    accepted_count = (
        changeset.accepted_risk_count
        + verification_plan.readiness.accepted_risk_count
        + review_response_summary.accepted_risk_count
    )
    if accepted_count > 0:
        signals.append(
            HandoffReadinessSignal(
                signal_id="accepted-risk",
                state="accepted_with_risk",
                summary=(
                    f"{accepted_count} accepted risk"
                    f"{'' if accepted_count == 1 else 's'} must be visible in handoff"
                ),
                blocking=False,
            )
        )
    return signals


def _manual_evidence_signals(
    changeset: ChangesetRecord,
    manual_evidence: Sequence[ManualEvidenceRecord],
) -> list[HandoffReadinessSignal]:
    attached = [
        item for item in manual_evidence if item.state == ManualEvidenceState.ATTACHED
    ]
    signals: list[HandoffReadinessSignal] = []
    stale = [
        item for item in attached if item.freshness == ManualEvidenceFreshness.STALE
    ]
    needs_inspection = [
        item
        for item in attached
        if item.freshness == ManualEvidenceFreshness.NEEDS_INSPECTION
    ]
    if stale:
        signals.append(
            HandoffReadinessSignal(
                signal_id="stale-manual-evidence",
                state="handoff_ready",
                summary=(
                    f"{len(stale)} manual evidence item"
                    f"{'' if len(stale) == 1 else 's'} are stale"
                ),
                blocking=False,
            )
        )
    if needs_inspection:
        signals.append(
            HandoffReadinessSignal(
                signal_id="manual-evidence-needs-inspection",
                state="handoff_ready",
                summary=(
                    f"{len(needs_inspection)} manual evidence item"
                    f"{'' if len(needs_inspection) == 1 else 's'} need inspection"
                ),
                blocking=False,
            )
        )
    local_only = [item for item in attached if item.local_only]
    skipped_live = skipped_live_evidence_items(attached)
    if local_only:
        signals.append(
            HandoffReadinessSignal(
                signal_id="local-only-evidence",
                state="handoff_ready",
                summary=(
                    f"{len(local_only)} local-only evidence item"
                    f"{'' if len(local_only) == 1 else 's'} must remain labeled"
                ),
                blocking=False,
            )
        )
    if skipped_live:
        signals.append(
            HandoffReadinessSignal(
                signal_id="skipped-live-evidence",
                state="handoff_ready",
                summary=(
                    f"{len(skipped_live)} skipped live evidence item"
                    f"{'' if len(skipped_live) == 1 else 's'} remain visible "
                    "as limitations, not passes"
                ),
                blocking=False,
            )
        )
    if not attached:
        signals.append(
            HandoffReadinessSignal(
                signal_id="no-manual-evidence",
                state="handoff_ready",
                summary=(
                    f"changeset {changeset.changeset_id} has no manual evidence; "
                    "do not imply external checks or reviewer observations"
                ),
                blocking=False,
            )
        )
    return signals


def _prior_readiness_signals(
    readiness: Sequence[ChangesetReadinessRecord],
) -> list[HandoffReadinessSignal]:
    signals: list[HandoffReadinessSignal] = []
    review = latest_readiness(readiness, ChangesetReadinessKind.REVIEW)
    if review is not None and review.state != ChangesetReadinessState.READY:
        signals.append(
            HandoffReadinessSignal(
                signal_id="review-readiness-not-ready",
                state="not_ready",
                summary=(
                    f"latest review readiness is {review.state.value}: {review.reason}"
                ),
            )
        )
    return signals


def _verification_id(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> TaskVerificationId | None:
    for requirement in verification_plan.readiness.requirements:
        if requirement.verification_id is not None:
            return requirement.verification_id
    return changeset.latest_verification_id


__all__ = [
    "HandoffReadinessSignal",
    "HandoffReadinessState",
    "aggregate_handoff_state",
    "build_handoff_readiness_signals",
    "handoff_limitations",
    "handoff_safe_next_actions",
]
