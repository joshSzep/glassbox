"""Review-readiness state derivation for changeset review briefs."""

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetVerificationState
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary


def review_readiness_state(
    *,
    inventory_status: ChangesetInventoryStatus,
    verification_plan: ChangesetVerificationPlanPreview,
    changeset: ChangesetRecord,
    review_response_summary: ChangesetReviewResponseSummary,
) -> tuple[ChangesetReadinessState, list[str]]:
    blockers: list[str] = []
    if review_response_summary.blockers:
        blockers.extend(review_response_summary.blockers)
    if review_response_summary.stale_response_count > 0:
        blockers.append(
            f"{review_response_summary.stale_response_count} review response(s) "
            "need fresh verification"
        )
        return ChangesetReadinessState.NEEDS_VERIFICATION, blockers
    if review_response_summary.unresolved_count > 0:
        blockers.append(
            f"{review_response_summary.unresolved_count} review feedback item(s) "
            "remain unresolved"
        )
        return ChangesetReadinessState.NEEDS_REVIEW, blockers
    readiness = verification_plan.readiness
    if inventory_status.stale:
        blockers.append(
            inventory_status.reason
            or "structured change inventory is stale against the current workspace"
        )
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if inventory_status.freshness == ChangesetInventoryFreshness.UNKNOWN:
        blockers.append(
            inventory_status.reason
            or "structured change inventory freshness is unknown"
        )
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if readiness.state == ChangesetVerificationState.FAILED:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.FAILED_CHECKS, blockers
    if readiness.state == ChangesetVerificationState.STALE:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if readiness.state in {
        ChangesetVerificationState.MISSING,
        ChangesetVerificationState.PLANNED,
        ChangesetVerificationState.RUNNING,
        ChangesetVerificationState.SKIPPED,
    }:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.NEEDS_VERIFICATION, blockers
    if readiness.state == ChangesetVerificationState.ACCEPTED_WITH_RISK:
        return ChangesetReadinessState.ACCEPTED_WITH_RISK, [readiness.summary]
    return ChangesetReadinessState.READY, blockers


def review_readiness_reason(
    state: ChangesetReadinessState,
    blockers: list[str],
) -> str:
    if blockers:
        return "; ".join(blockers)
    if state == ChangesetReadinessState.READY:
        return "deterministic changeset evidence is ready for reviewer inspection"
    return f"review readiness is {state.value}"


__all__ = [
    "review_readiness_reason",
    "review_readiness_state",
]
