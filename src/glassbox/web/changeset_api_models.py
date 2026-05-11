"""HTTP transport models for changeset APIs."""

from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from glassbox.core import ClaimSupport as ClaimSupport
from glassbox.core import EvidenceGraph as EvidenceGraph
from glassbox.core import EvidenceGraphNode as EvidenceGraphNode
from glassbox.runtime.evidence_graph import EvidenceGraphSummary as EvidenceGraphSummary
from glassbox.web.review_loop_api import ChangesetReviewResponseSummaryResponse
from glassbox.web.review_loop_api import ManualEvidenceResponse
from glassbox.web.review_loop_api import ReviewFeedbackResponse


class ChangesetSummaryResponse(BaseModel):
    session_id: str
    changeset_id: str
    objective: str
    summary: str | None = None
    status: str
    created_by: str
    archived_by: str | None = None
    archived_reason: str | None = None
    replacement_changeset_id: str | None = None
    task_id: str | None = None
    turn_id: str | None = None
    branch_search_id: str | None = None
    branch_candidate_id: str | None = None
    latest_inventory_artifact_id: str | None = None
    latest_verification_id: str | None = None
    latest_review_brief_artifact_id: str | None = None
    risk_level: str
    risk_summary: str | None = None
    unresolved_risk_count: int
    accepted_risk_count: int
    created_at: datetime
    updated_at: datetime
    last_sequence: int


class ChangesetSourceResponse(BaseModel):
    session_id: str
    changeset_id: str
    source_kind: str
    source_session_id: str | None = None
    task_id: str | None = None
    turn_id: str | None = None
    branch_search_id: str | None = None
    branch_candidate_id: str | None = None
    verification_id: str | None = None
    artifact_id: str | None = None
    reason: str
    limitation: str | None = None
    created_at: datetime
    last_sequence: int


class ChangesetInventoryResponse(BaseModel):
    session_id: str
    changeset_id: str
    artifact_id: str
    artifact_schema_version: int
    freshness: str
    changed_path_count: int
    source_digest: str | None = None
    previous_artifact_id: str | None = None
    refreshed_by: str
    task_id: str | None = None
    turn_id: str | None = None
    branch_search_id: str | None = None
    branch_candidate_id: str | None = None
    risk_level: str
    risk_summary: str | None = None
    unresolved_risk_count: int
    accepted_risk_count: int
    updated_at: datetime
    last_sequence: int


class ChangesetInventoryStatusResponse(BaseModel):
    freshness: str
    stale: bool
    reason: str | None = None
    recorded_source_digest: str | None = None
    current_source_digest: str | None = None
    safe_next_actions: list[str]


class ChangesetCommandEvidenceItemResponse(BaseModel):
    tool_attempt_id: str
    turn_id: str
    task_id: str | None = None
    tool_name: str
    status: str
    purpose: str
    review_relevance: str
    supports_verification: bool
    summary: str
    output_artifact_id: str | None = None
    environment_captured: bool
    toolchain_count: int
    redaction_notes: list[str]
    policy_summary: str | None = None
    local_only: bool


class ChangesetCommandEvidenceSummaryResponse(BaseModel):
    total_count: int
    verification_count: int
    failed_count: int
    risky_count: int
    environment_captured_count: int
    artifact_count: int
    items: list[ChangesetCommandEvidenceItemResponse]
    limitations: list[str]
    safe_next_actions: list[str]


class ChangesetVerificationPostureResponse(BaseModel):
    session_id: str
    changeset_id: str
    state: str
    summary: str
    verification_id: str | None = None
    artifact_id: str | None = None
    task_id: str | None = None
    turn_id: str | None = None
    stale_count: int
    missing_count: int
    failed_count: int
    accepted_risk_count: int
    updated_at: datetime
    last_sequence: int


class ChangesetReviewBriefResponse(BaseModel):
    session_id: str
    changeset_id: str
    artifact_id: str
    artifact_schema_version: int
    render_targets: list[str]
    inventory_artifact_id: str | None = None
    verification_id: str | None = None
    task_id: str | None = None
    turn_id: str | None = None
    created_by: str
    redacted: bool
    local_only: bool
    created_at: datetime
    last_sequence: int


class ChangesetReadinessResponse(BaseModel):
    session_id: str
    changeset_id: str
    readiness_kind: str
    state: str
    reason: str
    blockers: list[str]
    safe_next_actions: list[str]
    inventory_artifact_id: str | None = None
    review_brief_artifact_id: str | None = None
    verification_id: str | None = None
    task_id: str | None = None
    turn_id: str | None = None
    accepted_risk_count: int
    decided_by: str
    updated_at: datetime
    last_sequence: int


class ChangesetListPageResponse(BaseModel):
    items: list[ChangesetSummaryResponse]


class ChangesetVerificationPlanEntrySummaryResponse(BaseModel):
    verification_id: str
    check_name: str
    status: str
    lifecycle_state: str
    kind: str | None = None
    source: str | None = None
    command: list[str]
    changed_paths: list[str]
    blocking: bool
    reason: str | None = None
    artifact_id: str | None = None
    failed_artifact_id: str | None = None
    failure_summary: str | None = None
    accepted_risk_count: int
    accepted_risks: list[str]
    stale_reasons: list[str]
    last_sequence: int | None = None


class ChangesetVerificationPlanLifecycleSummaryResponse(BaseModel):
    total_count: int
    proposed_count: int
    selected_count: int
    running_count: int
    passed_count: int
    failed_count: int
    skipped_count: int
    stale_count: int
    accepted_risk_count: int
    manual_only_count: int
    command_count: int
    latest_verification_id: str | None = None
    latest_status: str | None = None
    entries: list[ChangesetVerificationPlanEntrySummaryResponse]
    safe_next_actions: list[str]
    non_claims: list[str]


class ChangesetDetailResponse(BaseModel):
    changeset: ChangesetSummaryResponse
    sources: list[ChangesetSourceResponse]
    inventory: ChangesetInventoryResponse | None = None
    inventory_status: ChangesetInventoryStatusResponse
    verification_posture: ChangesetVerificationPostureResponse | None = None
    review_briefs: list[ChangesetReviewBriefResponse]
    review_feedback: list[ReviewFeedbackResponse]
    manual_evidence: list[ManualEvidenceResponse]
    review_response_summary: ChangesetReviewResponseSummaryResponse
    readiness: list[ChangesetReadinessResponse]
    command_evidence: ChangesetCommandEvidenceSummaryResponse
    verification_plan_summary: ChangesetVerificationPlanLifecycleSummaryResponse
    limitations: list[str]
    safe_next_actions: list[str]


class ChangesetCreateRequest(BaseModel):
    source_kind: str = Field(pattern="^(session|task|branch-candidate|workspace-diff)$")
    session_id: str | None = None
    task_id: str | None = None
    branch_search_id: str | None = None
    candidate_id: str | None = None
    objective: str | None = None


class ChangesetCreateResponse(BaseModel):
    changeset_id: str
    session_id: str
    limitations: list[str]
    event_count: int


class ChangesetArchiveRequest(BaseModel):
    actor: str = "operator"
    reason: str = Field(min_length=1, max_length=2000)
    replacement_changeset_id: str | None = None


class ChangesetRefreshRequest(BaseModel):
    actor: str = "operator"


class ChangesetActionResponse(BaseModel):
    changeset_id: str
    status: str
    event_sequence: int
    detail: ChangesetDetailResponse


class ChangesetVerificationRecipePreviewResponse(BaseModel):
    recipe_id: str
    title: str
    confidence: str
    source: str
    matched_paths: list[str]
    component_ids: list[str]
    commands: list[str]
    profile_ids: list[str]
    case_ids: list[str]
    notes: str | None = None
    limitations: list[str]


class ChangesetTopologyImpactResponse(BaseModel):
    component_id: str
    name: str
    kind: str
    root_path: str
    matched_paths: list[str]
    test_roots: list[str]
    ownership_hints: list[str]
    dependency_hints: list[str]
    topology_freshness: str
    recommendation_posture: str
    limitations: list[str]


class ChangesetVerificationReasonGroupResponse(BaseModel):
    group: str
    title: str
    summaries: list[str]
    matched_paths: list[str]
    rule_ids: list[str]
    recommended_case_ids: list[str]
    recommended_profile_ids: list[str]
    release_gate_commands: list[str]


class ChangesetVerificationRequirementResponse(BaseModel):
    requirement_id: str
    state: str
    check_name: str
    reason: str
    source: str | None = None
    kind: str | None = None
    command: list[str]
    changed_paths: list[str]
    verification_id: str | None = None
    artifact_id: str | None = None
    blocking: bool
    evidence_summary: str | None = None
    safe_next_actions: list[str]


class ChangesetVerificationReadinessResponse(BaseModel):
    state: str
    summary: str
    requirements: list[ChangesetVerificationRequirementResponse]
    stale_count: int
    missing_count: int
    failed_count: int
    accepted_risk_count: int
    safe_next_actions: list[str]
    non_claims: list[str]


class ChangesetVerificationReviewLoopSummaryResponse(BaseModel):
    feedback_count: int
    open_feedback_count: int
    response_state_counts: dict[str, int]
    stale_response_count: int
    missing_response_verification_count: int
    failed_response_verification_count: int
    accepted_risk_response_count: int
    manual_evidence_count: int
    manual_evidence_kind_counts: dict[str, int]
    browser_evidence_count: int
    accessibility_evidence_count: int
    skipped_live_evidence_count: int
    skipped_browser_evidence_count: int
    skipped_accessibility_evidence_count: int
    stale_check_count: int
    topology_impact_count: int
    retained_verification_state: str
    safe_next_actions: list[str]
    limitations: list[str]
    non_claims: list[str]


class VerificationPlanEvidenceRefResponse(BaseModel):
    kind: str
    ref_id: str
    summary: str
    source_path: str | None = None
    freshness: str | None = None
    redaction: str | None = None
    reviewer_safe: bool


class VerificationPlanCommandRecipeResponse(BaseModel):
    command: list[str]
    display: str
    purpose: str
    safety_class: str
    requires_approval: bool
    expected_exit_codes: list[int]
    timeout_seconds: int | None = None
    cwd_hint: str | None = None


class VerificationPlanTargetResponse(BaseModel):
    kind: str
    target_id: str | None = None
    label: str | None = None


class VerificationPlanEntryResponse(BaseModel):
    verification_id: str
    check_name: str
    kind: str
    lifecycle_state: str
    target: VerificationPlanTargetResponse | None = None
    command: list[str]
    command_recipe: VerificationPlanCommandRecipeResponse | None = None
    source: str
    rationale: str
    selection_rationale: str | None = None
    blocking: bool
    timeout_seconds: int
    expected_exit_codes: list[int]
    changed_paths: list[str]
    eval_case_id: str | None = None
    eval_profile_id: str | None = None
    release_surfaces: list[str]
    evidence_references: list[VerificationPlanEvidenceRefResponse]
    stale_reasons: list[str]
    manual_evidence_required: bool
    execution_requires_approval: bool
    superseded_by_verification_id: str | None = None


class ChangesetVerificationSkippedCheckResponse(BaseModel):
    target_id: str
    target_kind: str
    reason: str
    explanation: str
    matched_paths: list[str]
    safe_next_actions: list[str]


class ChangesetVerificationPlanPreviewResponse(BaseModel):
    changeset_id: str
    session_id: str
    inventory_artifact_id: str | None = None
    inventory_freshness: str
    changed_paths: list[str]
    plan_entries: list[VerificationPlanEntryResponse]
    skipped_checks: list[ChangesetVerificationSkippedCheckResponse]
    recommended_commands: list[str]
    eval_profiles: list[str]
    recipes: list[ChangesetVerificationRecipePreviewResponse]
    topology_impacts: list[ChangesetTopologyImpactResponse]
    review_loop_summary: ChangesetVerificationReviewLoopSummaryResponse
    reason_groups: list[ChangesetVerificationReasonGroupResponse]
    expected_scope: list[str]
    retained_artifact_ids: list[str]
    readiness: ChangesetVerificationReadinessResponse
    plan_summary: ChangesetVerificationPlanLifecycleSummaryResponse
    limitations: list[str]
    safe_next_actions: list[str]
    non_claims: list[str]


class ChangesetRecordVerificationRequest(BaseModel):
    task_id: str | None = None
    verification_id: str | None = None


class ChangesetRecordVerificationResponse(BaseModel):
    changeset_id: str
    session_id: str
    selected_verification_ids: list[str]
    retained_artifact_ids: list[str]
    readiness: ChangesetVerificationReadinessResponse
    event_sequence: int


class ChangesetReviewBriefRequest(BaseModel):
    actor: str = "operator"
    include_markdown: bool = False


class ReviewBriefLimitationSummaryResponse(BaseModel):
    summarized: bool
    total_count: int = Field(ge=0)
    visible_count: int = Field(ge=0)
    overflow_count: int = Field(ge=0)
    reason: str | None = None


class ChangesetReviewBriefGenerateResponse(BaseModel):
    changeset_id: str
    session_id: str
    artifact_id: str
    artifact_path: str
    event_sequence: int
    readiness_event_sequence: int
    brief: dict[str, object]
    markdown: str | None = None
    limitations: list[str]
    limitation_summary: ReviewBriefLimitationSummaryResponse | None = None
    detail: ChangesetDetailResponse


class CommitMessageEvidenceLineResponse(BaseModel):
    kind: str
    summary: str
    references: list[str]


class CommitMessageSuggestionResponse(BaseModel):
    suggestion_kind: str
    schema_version: int
    suggestion_label: str
    changeset_id: str
    session_id: str
    style: str
    subject: str
    body: list[str]
    message: str
    deterministic: bool
    commit_readiness_state: str
    evidence: list[CommitMessageEvidenceLineResponse]
    limitations: list[str]
    non_claims: list[str]


class CommitReadinessSignalResponse(BaseModel):
    signal_id: str
    state: str
    summary: str
    blocking: bool
    paths: list[str]


class CommitReadinessGitSummaryResponse(BaseModel):
    branch: str | None = None
    ahead: int
    behind: int
    staged_paths: list[str]
    unstaged_paths: list[str]
    untracked_paths: list[str]
    workspace_path_count: int
    staged_path_count: int
    policy_sensitive_paths: list[str]
    generated_paths: list[str]
    clean: bool
    error: str | None = None


class CommitReadinessResponse(BaseModel):
    changeset_id: str
    session_id: str
    readiness_kind: str
    state: str
    reason: str
    blockers: list[str]
    safe_next_actions: list[str]
    inventory_artifact_id: str | None = None
    review_brief_artifact_id: str | None = None
    verification_id: str | None = None
    review_feedback_count: int
    unresolved_feedback_count: int
    stale_response_count: int
    manual_evidence_count: int
    local_only_evidence_count: int
    accepted_risk_count: int
    git: CommitReadinessGitSummaryResponse
    signals: list[CommitReadinessSignalResponse]
    non_claims: list[str]


class HandoffReadinessSignalResponse(BaseModel):
    signal_id: str
    state: str
    summary: str
    blocking: bool
    paths: list[str]


class HandoffReadinessEvidenceSummaryResponse(BaseModel):
    feedback_count: int
    unresolved_feedback_count: int
    stale_response_count: int
    manual_evidence_count: int
    local_only_evidence_count: int
    stale_manual_evidence_count: int
    needs_inspection_evidence_count: int
    browser_evidence_count: int
    accessibility_evidence_count: int
    skipped_live_evidence_count: int
    skipped_browser_evidence_count: int
    skipped_accessibility_evidence_count: int
    review_brief_count: int
    accepted_risk_count: int


class HandoffReadinessResponse(BaseModel):
    changeset_id: str
    session_id: str
    readiness_kind: str
    state: str
    reason: str
    blockers: list[str]
    limitations: list[str]
    safe_next_actions: list[str]
    inventory_artifact_id: str | None = None
    review_brief_artifact_id: str | None = None
    verification_id: str | None = None
    verification_plan_summary: ChangesetVerificationPlanLifecycleSummaryResponse
    commit_readiness_state: str
    evidence: HandoffReadinessEvidenceSummaryResponse
    git: CommitReadinessGitSummaryResponse
    signals: list[HandoffReadinessSignalResponse]
    non_claims: list[str]


__all__ = (
    "ChangesetSummaryResponse",
    "ChangesetSourceResponse",
    "ChangesetInventoryResponse",
    "ChangesetInventoryStatusResponse",
    "ChangesetCommandEvidenceItemResponse",
    "ChangesetCommandEvidenceSummaryResponse",
    "ChangesetVerificationPostureResponse",
    "ChangesetReviewBriefResponse",
    "ChangesetReadinessResponse",
    "ChangesetVerificationPlanEntrySummaryResponse",
    "ChangesetVerificationPlanLifecycleSummaryResponse",
    "ChangesetListPageResponse",
    "ChangesetDetailResponse",
    "ChangesetCreateRequest",
    "ChangesetCreateResponse",
    "ChangesetArchiveRequest",
    "ChangesetRefreshRequest",
    "ChangesetActionResponse",
    "ChangesetVerificationRecipePreviewResponse",
    "ChangesetTopologyImpactResponse",
    "ChangesetVerificationReasonGroupResponse",
    "ChangesetVerificationRequirementResponse",
    "ChangesetVerificationReadinessResponse",
    "ChangesetVerificationReviewLoopSummaryResponse",
    "ChangesetVerificationPlanPreviewResponse",
    "ChangesetRecordVerificationRequest",
    "ChangesetRecordVerificationResponse",
    "ChangesetReviewBriefRequest",
    "ReviewBriefLimitationSummaryResponse",
    "ChangesetReviewBriefGenerateResponse",
    "CommitMessageEvidenceLineResponse",
    "CommitMessageSuggestionResponse",
    "CommitReadinessSignalResponse",
    "CommitReadinessGitSummaryResponse",
    "CommitReadinessResponse",
    "HandoffReadinessSignalResponse",
    "HandoffReadinessEvidenceSummaryResponse",
    "HandoffReadinessResponse",
)
