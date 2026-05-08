"""Lifecycle brief limitation collection and reviewer-safe summarization."""

from glassbox.core import ChangesetSourceRecord
from glassbox.core import ChangesetVerificationState
from glassbox.core import ManualEvidenceRecord
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.changeset_models import ChangesetCommandEvidenceSummary
from glassbox.runtime.changeset_models import ChangesetInventoryStatus
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.review_briefs import ReviewBriefLimitationSummary
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary

_REVIEW_BRIEF_LIMITATION_CAP = 20
_REVIEW_BRIEF_OVERFLOW_SUMMARY_SLOT = 1


def collect_review_brief_limitations(
    *,
    sources: list[ChangesetSourceRecord],
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
    inventory_limitations: list[str],
    verification_plan: ChangesetVerificationPlanPreview,
    command_evidence: ChangesetCommandEvidenceSummary,
    review_response_summary: ChangesetReviewResponseSummary,
    manual_evidence: list[ManualEvidenceRecord],
) -> tuple[list[str], ReviewBriefLimitationSummary | None]:
    limitations = [
        source.limitation for source in sources if source.limitation is not None
    ]
    limitations.extend(inventory_limitations)
    if inventory_status.reason is not None:
        limitations.append(inventory_status.reason)
    if inventory is not None:
        limitations.extend(inventory.limitations)
    limitations.extend(verification_plan.limitations)
    limitations.extend(command_evidence.limitations)
    limitations.extend(review_response_summary.blockers)
    for evidence in manual_evidence:
        limitations.extend(evidence.limitations)
    if verification_plan.readiness.state != ChangesetVerificationState.PASSED:
        limitations.append(
            f"verification readiness is {verification_plan.readiness.state.value}"
        )
    if review_response_summary.unresolved_count > 0:
        limitations.append(
            f"{review_response_summary.unresolved_count} review feedback item(s) "
            "remain unresolved"
        )
    if review_response_summary.stale_response_count > 0:
        limitations.append(
            f"{review_response_summary.stale_response_count} review response(s) "
            "need fresh verification"
        )
    return summarize_review_brief_limitations(limitations)


def summarize_review_brief_limitations(
    limitations: list[str],
) -> tuple[list[str], ReviewBriefLimitationSummary | None]:
    """Keep reviewer-safe limitations within the artifact cap."""

    deduped = list(dict.fromkeys(limitations))
    if len(deduped) <= _REVIEW_BRIEF_LIMITATION_CAP:
        return deduped, None

    visible_limit = _REVIEW_BRIEF_LIMITATION_CAP - _REVIEW_BRIEF_OVERFLOW_SUMMARY_SLOT
    prioritized = sorted(
        enumerate(deduped),
        key=lambda item: (_review_brief_limitation_priority(item[1]), item[0]),
    )
    visible_indexes = {index for index, _limitation in prioritized[:visible_limit]}
    visible = [
        limitation
        for index, limitation in enumerate(deduped)
        if index in visible_indexes
    ]
    overflow_count = len(deduped) - len(visible)
    reason = "rich-evidence limitations exceeded the reviewer-safe 20-item artifact cap"
    visible.append(
        "rich-evidence limitations summarized: "
        f"{overflow_count} additional retained limitation(s) are summarized "
        "to keep the reviewer-safe brief within the 20-item artifact cap; "
        "inspect retained changeset evidence for the full limitation set"
    )
    return visible, ReviewBriefLimitationSummary(
        summarized=True,
        total_count=len(deduped),
        visible_count=len(visible),
        overflow_count=overflow_count,
        reason=reason,
    )


def _review_brief_limitation_priority(limitation: str) -> int:
    lowered = limitation.lower()
    high_priority_terms = (
        "blocker",
        "failed",
        "failure",
        "unresolved",
        "verification readiness",
        "need fresh verification",
        "stale",
        "accepted risk",
        "skipped",
        "publication",
        "raw evidence",
        "raw command",
        "raw manual evidence",
        "raw diff",
        "raw file",
    )
    if any(term in lowered for term in high_priority_terms):
        return 0
    return 1


__all__ = [
    "collect_review_brief_limitations",
    "summarize_review_brief_limitations",
]
