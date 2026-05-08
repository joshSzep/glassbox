"""Review response and fixup inventory artifact helpers."""

from glassbox.core import ChangesetId
from glassbox.core import ChangesetVerificationState
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewResponseState
from glassbox.runtime.changeset_safe_commands import show_changeset_command
from glassbox.runtime.review_fixup_artifacts import review_fixup_inventory_artifact_json
from glassbox.runtime.review_fixup_artifacts import (
    review_fixup_inventory_from_change_inventory,
)
from glassbox.runtime.review_response_models import REVIEW_FIXUP_INVENTORY_ARTIFACT_KIND
from glassbox.runtime.review_response_models import (
    REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION,
)
from glassbox.runtime.review_response_models import ChangesetReviewResponseSummary
from glassbox.runtime.review_response_models import ReviewFeedbackResponseStatus
from glassbox.runtime.review_response_models import ReviewFixupInventoryArtifact
from glassbox.runtime.review_response_models import ReviewFixupInventoryStatus
from glassbox.runtime.review_response_status import review_feedback_response_status
from glassbox.runtime.review_response_status import review_fixup_inventory_status
from glassbox.runtime.review_response_status import review_response_non_claims


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
        non_claims=review_response_non_claims(),
    )


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
