"""Review response and response-linked fixup inventory models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetVerificationState
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackFixupPathSummary
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFixupSourceKind
from glassbox.core import ReviewResponseState
from glassbox.core import TaskVerificationId

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


class ReviewFeedbackVerificationPlanEntryStatus(BaseModel):
    """A verification plan or ledger entry affected by response-linked paths."""

    model_config = ConfigDict(extra="forbid")

    verification_id: TaskVerificationId
    check_name: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=80)
    relationship: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=2000)
    command: list[str] = Field(default_factory=list, max_length=64)
    changed_paths: list[str] = Field(default_factory=list, max_length=100)
    safe_next_actions: list[str] = Field(default_factory=list, max_length=10)


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
    verification_plan_entries: list[ReviewFeedbackVerificationPlanEntryStatus] = Field(
        default_factory=list
    )
    selected_plan_entry_count: int = Field(default=0, ge=0)
    stale_plan_entry_count: int = Field(default=0, ge=0)
    skipped_plan_entry_count: int = Field(default=0, ge=0)
    accepted_risk_plan_entry_count: int = Field(default=0, ge=0)
    newly_required_check_count: int = Field(default=0, ge=0)
    verification_limitations: list[str] = Field(default_factory=list)
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


__all__ = [
    "REVIEW_FIXUP_INVENTORY_ARTIFACT_KIND",
    "REVIEW_FIXUP_INVENTORY_SCHEMA_VERSION",
    "ChangesetReviewResponseSummary",
    "ReviewFeedbackResponseStatus",
    "ReviewFeedbackVerificationPlanEntryStatus",
    "ReviewFixupInventoryArtifact",
    "ReviewFixupInventoryStatus",
]
