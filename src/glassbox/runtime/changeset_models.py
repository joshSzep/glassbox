"""Runtime-only changeset result and view models."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetSourceRecord
from glassbox.core import ChangesetVerificationPostureRecord
from glassbox.core import ChangesetVerificationState
from glassbox.core import EventEnvelope
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ReviewFeedbackId
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.core import SessionId
from glassbox.core import TaskId
from glassbox.core import TaskVerificationId
from glassbox.core import VerificationPlanEntry
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.changeset_topology import ChangesetTopologyImpact
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReasonGroup
from glassbox.runtime.review_briefs import ReviewBriefArtifact
from glassbox.runtime.review_briefs import ReviewBriefLimitationSummary
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFixupInventoryArtifact
from glassbox.runtime.review_responses import ReviewFixupInventoryStatus
from glassbox.services import StoredArtifact
from glassbox.tools.workflow import DiffSummaryScope


class ChangesetDerivationResult(BaseModel):
    """Result of explicitly deriving one changeset."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    limitations: list[str] = Field(default_factory=list)
    stored_events: list[EventEnvelope] = Field(default_factory=list)


class ChangesetInventoryStatus(BaseModel):
    """Current workspace comparison for the latest changeset inventory."""

    model_config = ConfigDict(extra="forbid")

    freshness: ChangesetInventoryFreshness
    stale: bool = False
    reason: str | None = Field(default=None, max_length=2000)
    recorded_source_digest: str | None = Field(default=None, max_length=256)
    current_source_digest: str | None = Field(default=None, max_length=256)
    safe_next_actions: list[str] = Field(default_factory=list)


class ChangesetCommandEvidenceItem(BaseModel):
    """One bounded command-evidence row relevant to a changeset."""

    model_config = ConfigDict(extra="forbid")

    tool_attempt_id: str
    turn_id: str
    task_id: str | None = None
    tool_name: str
    status: str
    purpose: str
    review_relevance: str
    supports_verification: bool
    summary: str
    output_artifact_id: ArtifactId | None = None
    environment_captured: bool = False
    toolchain_count: int = Field(default=0, ge=0)
    redaction_notes: list[str] = Field(default_factory=list)
    policy_summary: str | None = None
    local_only: bool = False


class ChangesetCommandEvidenceSummary(BaseModel):
    """Bounded command-evidence summary for changeset review surfaces."""

    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(default=0, ge=0)
    verification_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    risky_count: int = Field(default=0, ge=0)
    environment_captured_count: int = Field(default=0, ge=0)
    artifact_count: int = Field(default=0, ge=0)
    items: list[ChangesetCommandEvidenceItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)


class ChangesetVerificationPlanEntrySummary(BaseModel):
    """Bounded lifecycle summary for one verification plan entry."""

    model_config = ConfigDict(extra="forbid")

    verification_id: TaskVerificationId
    check_name: str
    status: str
    lifecycle_state: str
    kind: str | None = None
    source: str | None = None
    command: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    blocking: bool = True
    reason: str | None = None
    artifact_id: ArtifactId | None = None
    failed_artifact_id: ArtifactId | None = None
    failure_summary: str | None = None
    accepted_risk_count: int = Field(default=0, ge=0)
    accepted_risks: list[str] = Field(default_factory=list)
    stale_reasons: list[str] = Field(default_factory=list)
    last_sequence: int | None = Field(default=None, ge=0)


class ChangesetVerificationPlanLifecycleSummary(BaseModel):
    """Shared lifecycle summary for changeset verification plan surfaces."""

    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(default=0, ge=0)
    proposed_count: int = Field(default=0, ge=0)
    selected_count: int = Field(default=0, ge=0)
    running_count: int = Field(default=0, ge=0)
    passed_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)
    accepted_risk_count: int = Field(default=0, ge=0)
    manual_only_count: int = Field(default=0, ge=0)
    command_count: int = Field(default=0, ge=0)
    latest_verification_id: TaskVerificationId | None = None
    latest_status: str | None = None
    entries: list[ChangesetVerificationPlanEntrySummary] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ChangesetDetailView(BaseModel):
    """Read model for one changeset and its currently retained evidence refs."""

    model_config = ConfigDict(extra="forbid")

    changeset: ChangesetRecord
    sources: list[ChangesetSourceRecord] = Field(default_factory=list)
    inventory: ChangesetInventoryRecord | None = None
    verification_posture: ChangesetVerificationPostureRecord | None = None
    inventory_status: ChangesetInventoryStatus
    review_briefs: list[ChangesetReviewBriefRecord] = Field(default_factory=list)
    review_feedback: list[ReviewFeedbackRecord] = Field(default_factory=list)
    manual_evidence: list[ManualEvidenceRecord] = Field(default_factory=list)
    review_response_summary: ChangesetReviewResponseSummary
    readiness: list[ChangesetReadinessRecord] = Field(default_factory=list)
    command_evidence: ChangesetCommandEvidenceSummary
    verification_plan_summary: ChangesetVerificationPlanLifecycleSummary = Field(
        default_factory=lambda: ChangesetVerificationPlanLifecycleSummary()
    )
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)


class ChangesetInventoryRefreshResult(BaseModel):
    """Result of explicitly refreshing one structured changeset inventory."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    artifact: StoredArtifact
    inventory: ChangeInventoryArtifact
    event: EventEnvelope
    superseded_event: EventEnvelope | None = None
    freshness: ChangesetInventoryFreshness
    source_digest: str | None = None


class ChangesetVerificationRecipePreview(BaseModel):
    """One recipe row in a changeset verification plan preview."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    title: str
    confidence: str = "direct"
    source: str = "recipe"
    matched_paths: list[str] = Field(default_factory=list)
    component_ids: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    profile_ids: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    notes: str | None = None
    limitations: list[str] = Field(default_factory=list)


class ChangesetPathVerificationTargetPreview(BaseModel):
    """One path-to-verification target shown in changeset review surfaces."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    target_kind: str
    title: str
    confidence: str
    freshness: str = "unknown"
    matched_paths: list[str] = Field(default_factory=list)
    command: str | None = None
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)


class ChangesetVerificationReviewLoopSummary(BaseModel):
    """Review-loop context included in a verification plan preview."""

    model_config = ConfigDict(extra="forbid")

    feedback_count: int = Field(default=0, ge=0)
    open_feedback_count: int = Field(default=0, ge=0)
    response_state_counts: dict[str, int] = Field(default_factory=dict)
    stale_response_count: int = Field(default=0, ge=0)
    missing_response_verification_count: int = Field(default=0, ge=0)
    failed_response_verification_count: int = Field(default=0, ge=0)
    accepted_risk_response_count: int = Field(default=0, ge=0)
    manual_evidence_count: int = Field(default=0, ge=0)
    manual_evidence_kind_counts: dict[str, int] = Field(default_factory=dict)
    browser_evidence_count: int = Field(default=0, ge=0)
    accessibility_evidence_count: int = Field(default=0, ge=0)
    skipped_live_evidence_count: int = Field(default=0, ge=0)
    skipped_browser_evidence_count: int = Field(default=0, ge=0)
    skipped_accessibility_evidence_count: int = Field(default=0, ge=0)
    stale_check_count: int = Field(default=0, ge=0)
    topology_impact_count: int = Field(default=0, ge=0)
    retained_verification_state: ChangesetVerificationState
    safe_next_actions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ChangesetVerificationSkippedCheckPreview(BaseModel):
    """A recommended check that stays out of the executable preview plan."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    target_kind: str
    reason: str
    explanation: str
    matched_paths: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)


class ChangesetVerificationPlanPreview(BaseModel):
    """Preview-only verification plan for one changeset."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    inventory_artifact_id: ArtifactId | None = None
    inventory_freshness: ChangesetInventoryFreshness
    changed_paths: list[str] = Field(default_factory=list)
    plan_entries: list[VerificationPlanEntry] = Field(default_factory=list)
    skipped_checks: list[ChangesetVerificationSkippedCheckPreview] = Field(
        default_factory=list
    )
    recommended_commands: list[str] = Field(default_factory=list)
    eval_profiles: list[str] = Field(default_factory=list)
    recipes: list[ChangesetVerificationRecipePreview] = Field(default_factory=list)
    recommended_targets: list[ChangesetPathVerificationTargetPreview] = Field(
        default_factory=list
    )
    release_surfaces: list[ChangesetPathVerificationTargetPreview] = Field(
        default_factory=list
    )
    stale_evidence: list[ChangesetPathVerificationTargetPreview] = Field(
        default_factory=list
    )
    topology_impacts: list[ChangesetTopologyImpact] = Field(default_factory=list)
    review_loop_summary: ChangesetVerificationReviewLoopSummary = Field(
        default_factory=lambda: ChangesetVerificationReviewLoopSummary(
            retained_verification_state=ChangesetVerificationState.NOT_APPLICABLE
        )
    )
    reason_groups: list[EvalRecommendationReasonGroup] = Field(default_factory=list)
    expected_scope: list[str] = Field(default_factory=list)
    retained_artifact_ids: list[ArtifactId] = Field(default_factory=list)
    readiness: ChangesetVerificationReadiness
    plan_summary: ChangesetVerificationPlanLifecycleSummary = Field(
        default_factory=lambda: ChangesetVerificationPlanLifecycleSummary()
    )
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class PathVerificationPlanPreview(BaseModel):
    """Preview-only verification plan for an explicit changed-path set."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: str
    changed_paths: list[str] = Field(default_factory=list)
    plan_entries: list[VerificationPlanEntry] = Field(default_factory=list)
    skipped_checks: list[ChangesetVerificationSkippedCheckPreview] = Field(
        default_factory=list
    )
    recommended_commands: list[str] = Field(default_factory=list)
    eval_profiles: list[str] = Field(default_factory=list)
    recipes: list[ChangesetVerificationRecipePreview] = Field(default_factory=list)
    recommended_targets: list[ChangesetPathVerificationTargetPreview] = Field(
        default_factory=list
    )
    release_surfaces: list[ChangesetPathVerificationTargetPreview] = Field(
        default_factory=list
    )
    reason_groups: list[EvalRecommendationReasonGroup] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ChangesetWorkupCandidateGrouping(BaseModel):
    """Non-mutating candidate grouping for local workspace changes."""

    model_config = ConfigDict(extra="forbid")

    source_kind: str = "workspace-diff"
    title: str
    changed_path_count: int = Field(ge=0)
    generated_path_count: int = Field(default=0, ge=0)
    test_path_count: int = Field(default=0, ge=0)
    docs_path_count: int = Field(default=0, ge=0)
    policy_sensitive_path_count: int = Field(default=0, ge=0)
    risk_level: str = "unknown"
    create_command: str | None = None
    limitations: list[str] = Field(default_factory=list)


class ChangesetWorkupReviewRisk(BaseModel):
    """Review risk surfaced before a changeset is created."""

    model_config = ConfigDict(extra="forbid")

    level: str
    summary: str
    paths: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)


class ChangesetWorkupMemoryCandidatePreview(BaseModel):
    """Review-gated memory cue derived from a workup preview."""

    model_config = ConfigDict(extra="forbid")

    source: str
    summary: str
    matched_paths: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ChangesetWorkupPreview(BaseModel):
    """Read-only action map for turning workspace changes into review posture."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: str
    scope: DiffSummaryScope
    path_filters: list[str] = Field(default_factory=list)
    inspected_only: bool = True
    changeset_created: bool = False
    source_mutation_performed: bool = False
    command_execution_performed: bool = False
    changed_paths: list[str] = Field(default_factory=list)
    candidate_groupings: list[ChangesetWorkupCandidateGrouping] = Field(
        default_factory=list
    )
    inventory: ChangeInventoryArtifact
    verification_plan: PathVerificationPlanPreview
    repository_intelligence_impacts: list[ChangesetTopologyImpact] = Field(
        default_factory=list
    )
    review_risks: list[ChangesetWorkupReviewRisk] = Field(default_factory=list)
    memory_candidates: list[ChangesetWorkupMemoryCandidatePreview] = Field(
        default_factory=list
    )
    stale_evidence: list[ChangesetPathVerificationTargetPreview] = Field(
        default_factory=list
    )
    safe_next_actions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ChangesetVerificationEvidenceRecordResult(BaseModel):
    """Result of recording selected retained verification evidence."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    selected_verification_ids: list[TaskVerificationId] = Field(default_factory=list)
    retained_artifact_ids: list[ArtifactId] = Field(default_factory=list)
    readiness: ChangesetVerificationReadiness
    event: EventEnvelope


class ChangesetVerificationPlanDispositionResult(BaseModel):
    """Events recorded for a verification plan entry disposition."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    task_id: TaskId
    action: str
    verification_id: TaskVerificationId
    replacement_verification_id: TaskVerificationId | None = None
    events: list[EventEnvelope] = Field(default_factory=list)
    entry: VerificationPlanEntry
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ChangesetVerificationPlanExecutionResult(BaseModel):
    """Result of explicitly running one selected verification plan command."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    task_id: TaskId
    verification_id: TaskVerificationId
    check_name: str
    status: str
    command: list[str]
    exit_code: int | None = None
    timed_out: bool = False
    output_artifact_id: ArtifactId | None = None
    events: list[EventEnvelope] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ChangesetReviewBriefGenerationResult(BaseModel):
    """Result of generating one deterministic review brief artifact."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    artifact: StoredArtifact
    brief: ReviewBriefArtifact
    markdown: str
    event: EventEnvelope
    readiness_event: EventEnvelope
    limitations: list[str] = Field(default_factory=list)
    limitation_summary: ReviewBriefLimitationSummary | None = None


class ReviewFeedbackRecordResult(BaseModel):
    """Result of recording or updating one local review-feedback item."""

    model_config = ConfigDict(extra="forbid")

    feedback: ReviewFeedbackRecord
    scopes: list[ReviewFeedbackScopeRecord] = Field(default_factory=list)
    events: list[EventEnvelope] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ReviewFeedbackFixupInventoryResult(BaseModel):
    """Result of recording response-linked fixup inventory evidence."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    feedback_id: ReviewFeedbackId
    changeset_id: ChangesetId
    session_id: SessionId
    artifact: StoredArtifact
    inventory: ReviewFixupInventoryArtifact
    event: EventEnvelope
    status: ReviewFixupInventoryStatus


class ManualEvidenceRecordResult(BaseModel):
    """Result of attaching or rejecting one manual evidence item."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    evidence: ManualEvidenceRecord
    artifact: StoredArtifact | None = None
    event: EventEnvelope
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


__all__ = [
    "ChangesetCommandEvidenceItem",
    "ChangesetCommandEvidenceSummary",
    "ChangesetDerivationResult",
    "ChangesetDetailView",
    "ChangesetInventoryRefreshResult",
    "ChangesetInventoryStatus",
    "ChangesetReviewBriefGenerationResult",
    "ChangesetVerificationEvidenceRecordResult",
    "ChangesetVerificationPlanEntrySummary",
    "ChangesetVerificationPlanExecutionResult",
    "ChangesetVerificationPlanLifecycleSummary",
    "ChangesetVerificationPlanDispositionResult",
    "ChangesetVerificationPlanPreview",
    "ChangesetVerificationRecipePreview",
    "ChangesetVerificationReviewLoopSummary",
    "ChangesetVerificationSkippedCheckPreview",
    "ManualEvidenceRecordResult",
    "PathVerificationPlanPreview",
    "ReviewFeedbackFixupInventoryResult",
    "ReviewFeedbackRecordResult",
]
