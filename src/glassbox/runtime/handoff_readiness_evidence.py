"""Evidence count helpers for advisory handoff readiness."""

from collections.abc import Sequence

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceState
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.skipped_evidence import skipped_live_evidence_counts


class HandoffReadinessEvidenceSummary(BaseModel):
    """Small count summary for the evidence used in handoff readiness."""

    model_config = ConfigDict(extra="forbid")

    feedback_count: int = Field(ge=0)
    unresolved_feedback_count: int = Field(ge=0)
    stale_response_count: int = Field(ge=0)
    manual_evidence_count: int = Field(ge=0)
    local_only_evidence_count: int = Field(ge=0)
    stale_manual_evidence_count: int = Field(ge=0)
    needs_inspection_evidence_count: int = Field(ge=0)
    browser_evidence_count: int = Field(ge=0)
    accessibility_evidence_count: int = Field(ge=0)
    skipped_live_evidence_count: int = Field(ge=0)
    skipped_browser_evidence_count: int = Field(ge=0)
    skipped_accessibility_evidence_count: int = Field(ge=0)
    review_brief_count: int = Field(ge=0)
    accepted_risk_count: int = Field(ge=0)


def build_handoff_evidence_summary(
    *,
    review_response_summary: ChangesetReviewResponseSummary,
    manual_evidence: Sequence[ManualEvidenceRecord],
    review_briefs: Sequence[ChangesetReviewBriefRecord],
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> HandoffReadinessEvidenceSummary:
    """Build the count summary used by handoff API, CLI, and dashboard paths."""

    attached = [
        item for item in manual_evidence if item.state == ManualEvidenceState.ATTACHED
    ]
    (
        skipped_live_evidence_count,
        skipped_browser_evidence_count,
        skipped_accessibility_evidence_count,
    ) = skipped_live_evidence_counts(attached)
    return HandoffReadinessEvidenceSummary(
        feedback_count=review_response_summary.total_feedback_count,
        unresolved_feedback_count=review_response_summary.unresolved_count,
        stale_response_count=review_response_summary.stale_response_count,
        manual_evidence_count=len(attached),
        local_only_evidence_count=sum(1 for item in attached if item.local_only),
        stale_manual_evidence_count=sum(
            1 for item in attached if item.freshness == ManualEvidenceFreshness.STALE
        ),
        needs_inspection_evidence_count=sum(
            1
            for item in attached
            if item.freshness == ManualEvidenceFreshness.NEEDS_INSPECTION
        ),
        browser_evidence_count=sum(
            1
            for item in attached
            if item.evidence_kind
            in {ManualEvidenceKind.BROWSER_OBSERVATION, ManualEvidenceKind.SCREENSHOT}
        ),
        accessibility_evidence_count=sum(
            1
            for item in attached
            if item.evidence_kind == ManualEvidenceKind.ACCESSIBILITY_NOTE
        ),
        skipped_live_evidence_count=skipped_live_evidence_count,
        skipped_browser_evidence_count=skipped_browser_evidence_count,
        skipped_accessibility_evidence_count=skipped_accessibility_evidence_count,
        review_brief_count=len(review_briefs),
        accepted_risk_count=(
            changeset.accepted_risk_count
            + verification_plan.readiness.accepted_risk_count
            + review_response_summary.accepted_risk_count
        ),
    )


__all__ = [
    "HandoffReadinessEvidenceSummary",
    "build_handoff_evidence_summary",
]
