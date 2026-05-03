"""HTTP transport models for changeset APIs."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from glassbox.core.models import ChangesetInventoryRecord
from glassbox.core.models import ChangesetReadinessRecord
from glassbox.core.models import ChangesetRecord
from glassbox.core.models import ChangesetReviewBriefRecord
from glassbox.core.models import ChangesetSourceRecord
from glassbox.core.models import ChangesetVerificationPostureRecord
from glassbox.core.models import ManualEvidenceRecord
from glassbox.core.models import ReviewFeedbackRecord
from glassbox.core.models import ReviewFeedbackScopeRecord
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetReviewBriefGenerationResult
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.changesets import ManualEvidenceRecordResult
from glassbox.runtime.changesets import ReviewFeedbackRecordResult
from glassbox.runtime.commit_messages import CommitMessageSuggestion
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary
from glassbox.runtime.review_responses import ReviewFeedbackResponseStatus


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


class ReviewFeedbackScopeResponse(BaseModel):
    session_id: str
    feedback_id: str
    changeset_id: str
    scope_kind: str
    reason: str
    source_session_id: str | None = None
    task_id: str | None = None
    turn_id: str | None = None
    artifact_id: str | None = None
    verification_id: str | None = None
    branch_search_id: str | None = None
    branch_candidate_id: str | None = None
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    created_at: datetime
    last_sequence: int


class ReviewFeedbackResponse(BaseModel):
    session_id: str
    feedback_id: str
    changeset_id: str
    feedback_kind: str
    provenance: str
    disposition: str
    summary: str
    body: str | None = None
    source_label: str | None = None
    reviewer_label: str | None = None
    created_by: str
    updated_by: str | None = None
    resolved_by: str | None = None
    archived_by: str | None = None
    accepted_by: str | None = None
    source_session_id: str | None = None
    task_id: str | None = None
    turn_id: str | None = None
    artifact_id: str | None = None
    verification_id: str | None = None
    resolution_summary: str | None = None
    residual_risk: str | None = None
    risk_summary: str | None = None
    acceptance_reason: str | None = None
    archived_reason: str | None = None
    replacement_feedback_id: str | None = None
    reopened_count: int
    created_at: datetime
    updated_at: datetime
    last_sequence: int


class ReviewFeedbackResponseStatusResponse(BaseModel):
    feedback_id: str
    changeset_id: str
    response_state: str
    disposition: str
    summary: str
    fixup_inventory_count: int
    latest_fixup_inventory_artifact_id: str | None = None
    latest_fixup_inventory_sequence: int | None = None
    latest_fixup_inventory_at: datetime | None = None
    latest_source_kind: str | None = None
    latest_source_summary: str | None = None
    inventory_freshness: str
    stale: bool
    stale_reason: str | None = None
    changed_path_count: int
    matched_scope_path_count: int
    path_summaries: list[str]
    blockers: list[str]
    safe_next_actions: list[str]
    non_claims: list[str]


class ChangesetReviewResponseSummaryResponse(BaseModel):
    changeset_id: str
    total_feedback_count: int
    open_count: int
    responded_count: int
    unresolved_count: int
    stale_response_count: int
    accepted_risk_count: int
    blocked_count: int
    items: list[ReviewFeedbackResponseStatusResponse]
    blockers: list[str]
    safe_next_actions: list[str]
    non_claims: list[str]


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


class ManualEvidenceResponse(BaseModel):
    session_id: str
    evidence_id: str
    evidence_kind: str
    state: str
    target_kind: str
    target_id: str
    changeset_id: str | None = None
    feedback_id: str | None = None
    artifact_id: str | None = None
    artifact_schema_version: int | None = None
    summary: str
    source_label: str
    observed_at: datetime | None = None
    created_by: str
    local_only: bool
    redaction_status: str
    freshness: str
    limitations: list[str]
    non_claims: list[str]
    rejected_reason: str | None = None
    archived_reason: str | None = None
    superseded_reason: str | None = None
    replacement_evidence_id: str | None = None
    task_id: str | None = None
    turn_id: str | None = None
    verification_id: str | None = None
    created_at: datetime
    updated_at: datetime
    last_sequence: int


class ChangesetListPageResponse(BaseModel):
    items: list[ChangesetSummaryResponse]


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


class ReviewFeedbackCreateRequest(BaseModel):
    feedback_kind: str = Field(
        pattern="^(requested_change|reviewer_question|operator_note|observation|risk)$"
    )
    summary: str = Field(min_length=1, max_length=1000)
    provenance: str = Field(
        default="manual",
        pattern="^(reviewer|operator|manual|imported|unknown)$",
    )
    body: str | None = Field(default=None, max_length=4000)
    source_label: str | None = Field(default=None, max_length=200)
    reviewer_label: str | None = Field(default=None, max_length=200)
    actor: str = Field(default="operator", min_length=1, max_length=200)
    scope_kind: str = Field(
        default="changeset",
        pattern="^(changeset|file|task|turn|artifact|verification|branch_candidate)$",
    )
    scope_reason: str | None = Field(default=None, max_length=2000)
    file_path: str | None = Field(default=None, max_length=2000)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)


class ManualEvidenceAttachRequest(BaseModel):
    evidence_kind: str = Field(
        pattern=(
            "^(manual_command|external_check|reviewer_note|screenshot|"
            "browser_observation|accessibility_note|local_file_reference|"
            "sanitized_log|operator_assertion)$"
        )
    )
    summary: str = Field(min_length=1, max_length=1000)
    source_label: str = Field(min_length=1, max_length=200)
    actor: str = Field(default="operator", min_length=1, max_length=200)
    target_kind: str = Field(
        default="changeset",
        pattern=(
            "^(changeset|feedback|response|verification_requirement|review_brief|"
            "publication_boundary|unknown)$"
        ),
    )
    target_id: str | None = Field(default=None, max_length=200)
    feedback_id: str | None = None
    note: str | None = Field(default=None, max_length=12000)
    command_text: str | None = Field(default=None, max_length=500)
    external_url_label: str | None = Field(default=None, max_length=300)
    local_file_label: str | None = Field(default=None, max_length=200)
    local_file_path_hint: str | None = Field(default=None, max_length=500)
    freshness: str = Field(
        default="unknown",
        pattern="^(current|needs_inspection|stale|unknown)$",
    )


class ManualEvidenceListPageResponse(BaseModel):
    items: list[ManualEvidenceResponse]


class ManualEvidenceActionResponse(BaseModel):
    evidence: ManualEvidenceResponse
    artifact_id: str | None = None
    artifact_path: str | None = None
    event_sequence: int
    safe_next_actions: list[str]
    non_claims: list[str]


class ReviewFeedbackResolveRequest(BaseModel):
    summary: str = Field(min_length=1, max_length=4000)
    residual_risk: str | None = Field(default=None, max_length=2000)
    actor: str = Field(default="operator", min_length=1, max_length=200)


class ReviewFeedbackReopenRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    actor: str = Field(default="operator", min_length=1, max_length=200)


class ReviewFeedbackArchiveRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    actor: str = Field(default="operator", min_length=1, max_length=200)
    replacement_feedback_id: str | None = None


class ReviewFeedbackAcceptRiskRequest(BaseModel):
    risk_summary: str = Field(min_length=1, max_length=4000)
    reason: str = Field(min_length=1, max_length=2000)
    actor: str = Field(default="operator", min_length=1, max_length=200)


class ReviewFeedbackListPageResponse(BaseModel):
    items: list[ReviewFeedbackResponse]
    response_summary: ChangesetReviewResponseSummaryResponse | None = None


class ReviewFeedbackDetailResponse(BaseModel):
    feedback: ReviewFeedbackResponse
    scopes: list[ReviewFeedbackScopeResponse]
    response_status: ReviewFeedbackResponseStatusResponse
    safe_next_actions: list[str]
    non_claims: list[str]


class ReviewFeedbackActionResponse(BaseModel):
    feedback: ReviewFeedbackResponse
    scopes: list[ReviewFeedbackScopeResponse]
    event_sequences: list[int]
    safe_next_actions: list[str]
    non_claims: list[str]


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


class ChangesetVerificationPlanPreviewResponse(BaseModel):
    changeset_id: str
    session_id: str
    inventory_artifact_id: str | None = None
    inventory_freshness: str
    changed_paths: list[str]
    recommended_commands: list[str]
    eval_profiles: list[str]
    recipes: list[ChangesetVerificationRecipePreviewResponse]
    topology_impacts: list[ChangesetTopologyImpactResponse]
    reason_groups: list[ChangesetVerificationReasonGroupResponse]
    expected_scope: list[str]
    retained_artifact_ids: list[str]
    readiness: ChangesetVerificationReadinessResponse
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
    accepted_risk_count: int
    git: CommitReadinessGitSummaryResponse
    signals: list[CommitReadinessSignalResponse]
    non_claims: list[str]


def build_changeset_summary_response(
    changeset: ChangesetRecord,
) -> ChangesetSummaryResponse:
    return ChangesetSummaryResponse(
        session_id=str(changeset.session_id),
        changeset_id=str(changeset.changeset_id),
        objective=changeset.objective,
        summary=changeset.summary,
        status=changeset.status,
        created_by=changeset.created_by,
        archived_by=changeset.archived_by,
        archived_reason=changeset.archived_reason,
        replacement_changeset_id=_optional_str(changeset.replacement_changeset_id),
        task_id=_optional_str(changeset.task_id),
        turn_id=_optional_str(changeset.turn_id),
        branch_search_id=_optional_str(changeset.branch_search_id),
        branch_candidate_id=_optional_str(changeset.branch_candidate_id),
        latest_inventory_artifact_id=_optional_str(
            changeset.latest_inventory_artifact_id
        ),
        latest_verification_id=_optional_str(changeset.latest_verification_id),
        latest_review_brief_artifact_id=_optional_str(
            changeset.latest_review_brief_artifact_id
        ),
        risk_level=changeset.risk_level.value,
        risk_summary=changeset.risk_summary,
        unresolved_risk_count=changeset.unresolved_risk_count,
        accepted_risk_count=changeset.accepted_risk_count,
        created_at=changeset.created_at,
        updated_at=changeset.updated_at,
        last_sequence=changeset.last_sequence,
    )


def build_changeset_summary_responses(
    changesets: Sequence[ChangesetRecord],
) -> list[ChangesetSummaryResponse]:
    return [build_changeset_summary_response(item) for item in changesets]


def build_changeset_detail_response(
    detail: ChangesetDetailView,
) -> ChangesetDetailResponse:
    return ChangesetDetailResponse(
        changeset=build_changeset_summary_response(detail.changeset),
        sources=[build_changeset_source_response(item) for item in detail.sources],
        inventory=(
            build_changeset_inventory_response(detail.inventory)
            if detail.inventory is not None
            else None
        ),
        inventory_status=ChangesetInventoryStatusResponse(
            freshness=detail.inventory_status.freshness.value,
            stale=detail.inventory_status.stale,
            reason=detail.inventory_status.reason,
            recorded_source_digest=detail.inventory_status.recorded_source_digest,
            current_source_digest=detail.inventory_status.current_source_digest,
            safe_next_actions=detail.inventory_status.safe_next_actions,
        ),
        verification_posture=(
            build_changeset_verification_posture_response(detail.verification_posture)
            if detail.verification_posture is not None
            else None
        ),
        review_briefs=[
            build_changeset_review_brief_response(item) for item in detail.review_briefs
        ],
        review_feedback=[
            build_review_feedback_response(item) for item in detail.review_feedback
        ],
        manual_evidence=[
            build_manual_evidence_response(item) for item in detail.manual_evidence
        ],
        review_response_summary=build_review_response_summary_response(
            detail.review_response_summary
        ),
        readiness=[
            build_changeset_readiness_response(item) for item in detail.readiness
        ],
        command_evidence=ChangesetCommandEvidenceSummaryResponse(
            total_count=detail.command_evidence.total_count,
            verification_count=detail.command_evidence.verification_count,
            failed_count=detail.command_evidence.failed_count,
            risky_count=detail.command_evidence.risky_count,
            environment_captured_count=(
                detail.command_evidence.environment_captured_count
            ),
            artifact_count=detail.command_evidence.artifact_count,
            items=[
                ChangesetCommandEvidenceItemResponse(
                    tool_attempt_id=item.tool_attempt_id,
                    turn_id=item.turn_id,
                    task_id=item.task_id,
                    tool_name=item.tool_name,
                    status=item.status,
                    purpose=item.purpose,
                    review_relevance=item.review_relevance,
                    supports_verification=item.supports_verification,
                    summary=item.summary,
                    output_artifact_id=_optional_str(item.output_artifact_id),
                    environment_captured=item.environment_captured,
                    toolchain_count=item.toolchain_count,
                    redaction_notes=item.redaction_notes,
                    policy_summary=item.policy_summary,
                    local_only=item.local_only,
                )
                for item in detail.command_evidence.items
            ],
            limitations=detail.command_evidence.limitations,
            safe_next_actions=detail.command_evidence.safe_next_actions,
        ),
        limitations=detail.limitations,
        safe_next_actions=detail.safe_next_actions,
    )


def build_changeset_verification_plan_response(
    preview: ChangesetVerificationPlanPreview,
) -> ChangesetVerificationPlanPreviewResponse:
    return ChangesetVerificationPlanPreviewResponse(
        changeset_id=str(preview.changeset_id),
        session_id=str(preview.session_id),
        inventory_artifact_id=_optional_str(preview.inventory_artifact_id),
        inventory_freshness=preview.inventory_freshness.value,
        changed_paths=preview.changed_paths,
        recommended_commands=preview.recommended_commands,
        eval_profiles=preview.eval_profiles,
        recipes=[
            ChangesetVerificationRecipePreviewResponse(
                recipe_id=recipe.recipe_id,
                title=recipe.title,
                confidence=recipe.confidence,
                source=recipe.source,
                matched_paths=recipe.matched_paths,
                component_ids=recipe.component_ids,
                commands=recipe.commands,
                profile_ids=recipe.profile_ids,
                case_ids=recipe.case_ids,
                notes=recipe.notes,
                limitations=recipe.limitations,
            )
            for recipe in preview.recipes
        ],
        topology_impacts=[
            ChangesetTopologyImpactResponse(
                component_id=impact.component_id,
                name=impact.name,
                kind=impact.kind,
                root_path=impact.root_path,
                matched_paths=impact.matched_paths,
                test_roots=impact.test_roots,
                ownership_hints=impact.ownership_hints,
                dependency_hints=impact.dependency_hints,
                topology_freshness=impact.topology_freshness,
                recommendation_posture=impact.recommendation_posture,
                limitations=impact.limitations,
            )
            for impact in preview.topology_impacts
        ],
        reason_groups=[
            ChangesetVerificationReasonGroupResponse(
                group=group.group,
                title=group.title,
                summaries=group.summaries,
                matched_paths=group.matched_paths,
                rule_ids=group.rule_ids,
                recommended_case_ids=group.recommended_case_ids,
                recommended_profile_ids=group.recommended_profile_ids,
                release_gate_commands=group.release_gate_commands,
            )
            for group in preview.reason_groups
        ],
        expected_scope=preview.expected_scope,
        retained_artifact_ids=[
            str(artifact_id) for artifact_id in preview.retained_artifact_ids
        ],
        readiness=build_changeset_verification_readiness_response(preview.readiness),
        limitations=preview.limitations,
        safe_next_actions=preview.safe_next_actions,
        non_claims=preview.non_claims,
    )


def build_changeset_verification_readiness_response(
    readiness,
) -> ChangesetVerificationReadinessResponse:
    return ChangesetVerificationReadinessResponse(
        state=readiness.state.value,
        summary=readiness.summary,
        requirements=[
            ChangesetVerificationRequirementResponse(
                requirement_id=requirement.requirement_id,
                state=requirement.state.value,
                check_name=requirement.check_name,
                reason=requirement.reason,
                source=(
                    requirement.source.value if requirement.source is not None else None
                ),
                kind=requirement.kind.value if requirement.kind is not None else None,
                command=requirement.command,
                changed_paths=requirement.changed_paths,
                verification_id=_optional_str(requirement.verification_id),
                artifact_id=_optional_str(requirement.artifact_id),
                blocking=requirement.blocking,
                evidence_summary=requirement.evidence_summary,
                safe_next_actions=requirement.safe_next_actions,
            )
            for requirement in readiness.requirements
        ],
        stale_count=readiness.stale_count,
        missing_count=readiness.missing_count,
        failed_count=readiness.failed_count,
        accepted_risk_count=readiness.accepted_risk_count,
        safe_next_actions=readiness.safe_next_actions,
        non_claims=readiness.non_claims,
    )


def build_changeset_review_brief_generate_response(
    result: ChangesetReviewBriefGenerationResult,
    detail: ChangesetDetailView,
    *,
    include_markdown: bool = False,
) -> ChangesetReviewBriefGenerateResponse:
    return ChangesetReviewBriefGenerateResponse(
        changeset_id=str(result.changeset_id),
        session_id=str(result.session_id),
        artifact_id=str(result.artifact.artifact_id),
        artifact_path=result.artifact.relative_path.as_posix(),
        event_sequence=result.event.sequence,
        readiness_event_sequence=result.readiness_event.sequence,
        brief=result.brief.model_dump(mode="json"),
        markdown=result.markdown if include_markdown else None,
        limitations=result.limitations,
        detail=build_changeset_detail_response(detail),
    )


def build_commit_message_suggestion_response(
    suggestion: CommitMessageSuggestion,
) -> CommitMessageSuggestionResponse:
    return CommitMessageSuggestionResponse(
        suggestion_kind=suggestion.suggestion_kind,
        schema_version=suggestion.schema_version,
        suggestion_label=suggestion.suggestion_label,
        changeset_id=str(suggestion.changeset_id),
        session_id=str(suggestion.session_id),
        style=suggestion.style,
        subject=suggestion.subject,
        body=suggestion.body,
        message=suggestion.message,
        deterministic=suggestion.deterministic,
        commit_readiness_state=suggestion.commit_readiness_state,
        evidence=[
            CommitMessageEvidenceLineResponse(
                kind=line.kind,
                summary=line.summary,
                references=line.references,
            )
            for line in suggestion.evidence
        ],
        limitations=suggestion.limitations,
        non_claims=suggestion.non_claims,
    )


def build_commit_readiness_response(
    readiness: CommitReadinessAssessment,
) -> CommitReadinessResponse:
    return CommitReadinessResponse(
        changeset_id=str(readiness.changeset_id),
        session_id=str(readiness.session_id),
        readiness_kind=readiness.readiness_kind.value,
        state=readiness.state.value,
        reason=readiness.reason,
        blockers=readiness.blockers,
        safe_next_actions=readiness.safe_next_actions,
        inventory_artifact_id=_optional_str(readiness.inventory_artifact_id),
        review_brief_artifact_id=_optional_str(readiness.review_brief_artifact_id),
        verification_id=_optional_str(readiness.verification_id),
        accepted_risk_count=readiness.accepted_risk_count,
        git=CommitReadinessGitSummaryResponse(
            branch=readiness.git.branch,
            ahead=readiness.git.ahead,
            behind=readiness.git.behind,
            staged_paths=readiness.git.staged_paths,
            unstaged_paths=readiness.git.unstaged_paths,
            untracked_paths=readiness.git.untracked_paths,
            workspace_path_count=readiness.git.workspace_path_count,
            staged_path_count=readiness.git.staged_path_count,
            policy_sensitive_paths=readiness.git.policy_sensitive_paths,
            generated_paths=readiness.git.generated_paths,
            clean=readiness.git.clean,
            error=readiness.git.error,
        ),
        signals=[
            CommitReadinessSignalResponse(
                signal_id=signal.signal_id,
                state=signal.state.value,
                summary=signal.summary,
                blocking=signal.blocking,
                paths=signal.paths,
            )
            for signal in readiness.signals
        ],
        non_claims=readiness.non_claims,
    )


def build_changeset_source_response(
    source: ChangesetSourceRecord,
) -> ChangesetSourceResponse:
    return ChangesetSourceResponse(
        session_id=str(source.session_id),
        changeset_id=str(source.changeset_id),
        source_kind=source.source_kind.value,
        source_session_id=_optional_str(source.source_session_id),
        task_id=_optional_str(source.task_id),
        turn_id=_optional_str(source.turn_id),
        branch_search_id=_optional_str(source.branch_search_id),
        branch_candidate_id=_optional_str(source.branch_candidate_id),
        verification_id=_optional_str(source.verification_id),
        artifact_id=_optional_str(source.artifact_id),
        reason=source.reason,
        limitation=source.limitation,
        created_at=source.created_at,
        last_sequence=source.last_sequence,
    )


def build_changeset_inventory_response(
    inventory: ChangesetInventoryRecord,
) -> ChangesetInventoryResponse:
    return ChangesetInventoryResponse(
        session_id=str(inventory.session_id),
        changeset_id=str(inventory.changeset_id),
        artifact_id=str(inventory.artifact_id),
        artifact_schema_version=inventory.artifact_schema_version,
        freshness=inventory.freshness.value,
        changed_path_count=inventory.changed_path_count,
        source_digest=inventory.source_digest,
        previous_artifact_id=_optional_str(inventory.previous_artifact_id),
        refreshed_by=inventory.refreshed_by,
        task_id=_optional_str(inventory.task_id),
        turn_id=_optional_str(inventory.turn_id),
        branch_search_id=_optional_str(inventory.branch_search_id),
        branch_candidate_id=_optional_str(inventory.branch_candidate_id),
        risk_level=inventory.risk_level.value,
        risk_summary=inventory.risk_summary,
        unresolved_risk_count=inventory.unresolved_risk_count,
        accepted_risk_count=inventory.accepted_risk_count,
        updated_at=inventory.updated_at,
        last_sequence=inventory.last_sequence,
    )


def build_changeset_verification_posture_response(
    posture: ChangesetVerificationPostureRecord,
) -> ChangesetVerificationPostureResponse:
    return ChangesetVerificationPostureResponse(
        session_id=str(posture.session_id),
        changeset_id=str(posture.changeset_id),
        state=posture.state.value,
        summary=posture.summary,
        verification_id=_optional_str(posture.verification_id),
        artifact_id=_optional_str(posture.artifact_id),
        task_id=_optional_str(posture.task_id),
        turn_id=_optional_str(posture.turn_id),
        stale_count=posture.stale_count,
        missing_count=posture.missing_count,
        failed_count=posture.failed_count,
        accepted_risk_count=posture.accepted_risk_count,
        updated_at=posture.updated_at,
        last_sequence=posture.last_sequence,
    )


def build_changeset_review_brief_response(
    brief: ChangesetReviewBriefRecord,
) -> ChangesetReviewBriefResponse:
    return ChangesetReviewBriefResponse(
        session_id=str(brief.session_id),
        changeset_id=str(brief.changeset_id),
        artifact_id=str(brief.artifact_id),
        artifact_schema_version=brief.artifact_schema_version,
        render_targets=brief.render_targets,
        inventory_artifact_id=_optional_str(brief.inventory_artifact_id),
        verification_id=_optional_str(brief.verification_id),
        task_id=_optional_str(brief.task_id),
        turn_id=_optional_str(brief.turn_id),
        created_by=brief.created_by,
        redacted=brief.redacted,
        local_only=brief.local_only,
        created_at=brief.created_at,
        last_sequence=brief.last_sequence,
    )


def build_review_feedback_response(
    feedback: ReviewFeedbackRecord,
) -> ReviewFeedbackResponse:
    return ReviewFeedbackResponse(
        session_id=str(feedback.session_id),
        feedback_id=str(feedback.feedback_id),
        changeset_id=str(feedback.changeset_id),
        feedback_kind=feedback.feedback_kind.value,
        provenance=feedback.provenance.value,
        disposition=feedback.disposition.value,
        summary=feedback.summary,
        body=feedback.body,
        source_label=feedback.source_label,
        reviewer_label=feedback.reviewer_label,
        created_by=feedback.created_by,
        updated_by=feedback.updated_by,
        resolved_by=feedback.resolved_by,
        archived_by=feedback.archived_by,
        accepted_by=feedback.accepted_by,
        source_session_id=_optional_str(feedback.source_session_id),
        task_id=_optional_str(feedback.task_id),
        turn_id=_optional_str(feedback.turn_id),
        artifact_id=_optional_str(feedback.artifact_id),
        verification_id=_optional_str(feedback.verification_id),
        resolution_summary=feedback.resolution_summary,
        residual_risk=feedback.residual_risk,
        risk_summary=feedback.risk_summary,
        acceptance_reason=feedback.acceptance_reason,
        archived_reason=feedback.archived_reason,
        replacement_feedback_id=_optional_str(feedback.replacement_feedback_id),
        reopened_count=feedback.reopened_count,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
        last_sequence=feedback.last_sequence,
    )


def build_manual_evidence_response(
    evidence: ManualEvidenceRecord,
) -> ManualEvidenceResponse:
    return ManualEvidenceResponse(
        session_id=str(evidence.session_id),
        evidence_id=str(evidence.evidence_id),
        evidence_kind=evidence.evidence_kind.value,
        state=evidence.state.value,
        target_kind=evidence.target_kind.value,
        target_id=evidence.target_id,
        changeset_id=_optional_str(evidence.changeset_id),
        feedback_id=_optional_str(evidence.feedback_id),
        artifact_id=_optional_str(evidence.artifact_id),
        artifact_schema_version=evidence.artifact_schema_version,
        summary=evidence.summary,
        source_label=evidence.source_label,
        observed_at=evidence.observed_at,
        created_by=evidence.created_by,
        local_only=evidence.local_only,
        redaction_status=evidence.redaction_status.value,
        freshness=evidence.freshness.value,
        limitations=evidence.limitations,
        non_claims=evidence.non_claims,
        rejected_reason=evidence.rejected_reason,
        archived_reason=evidence.archived_reason,
        superseded_reason=evidence.superseded_reason,
        replacement_evidence_id=_optional_str(evidence.replacement_evidence_id),
        task_id=_optional_str(evidence.task_id),
        turn_id=_optional_str(evidence.turn_id),
        verification_id=_optional_str(evidence.verification_id),
        created_at=evidence.created_at,
        updated_at=evidence.updated_at,
        last_sequence=evidence.last_sequence,
    )


def build_manual_evidence_action_response(
    result: ManualEvidenceRecordResult,
) -> ManualEvidenceActionResponse:
    return ManualEvidenceActionResponse(
        evidence=build_manual_evidence_response(result.evidence),
        artifact_id=(
            str(result.artifact.artifact_id) if result.artifact is not None else None
        ),
        artifact_path=(
            result.artifact.relative_path.as_posix()
            if result.artifact is not None
            else None
        ),
        event_sequence=result.event.sequence,
        safe_next_actions=result.safe_next_actions,
        non_claims=result.non_claims,
    )


def build_review_feedback_scope_response(
    scope: ReviewFeedbackScopeRecord,
) -> ReviewFeedbackScopeResponse:
    return ReviewFeedbackScopeResponse(
        session_id=str(scope.session_id),
        feedback_id=str(scope.feedback_id),
        changeset_id=str(scope.changeset_id),
        scope_kind=scope.scope_kind.value,
        reason=scope.reason,
        source_session_id=_optional_str(scope.source_session_id),
        task_id=_optional_str(scope.task_id),
        turn_id=_optional_str(scope.turn_id),
        artifact_id=_optional_str(scope.artifact_id),
        verification_id=_optional_str(scope.verification_id),
        branch_search_id=_optional_str(scope.branch_search_id),
        branch_candidate_id=_optional_str(scope.branch_candidate_id),
        file_path=scope.file_path,
        line_start=scope.line_start,
        line_end=scope.line_end,
        created_at=scope.created_at,
        last_sequence=scope.last_sequence,
    )


def build_review_feedback_response_status_response(
    status: ReviewFeedbackResponseStatus,
) -> ReviewFeedbackResponseStatusResponse:
    return ReviewFeedbackResponseStatusResponse(
        feedback_id=str(status.feedback_id),
        changeset_id=str(status.changeset_id),
        response_state=status.response_state.value,
        disposition=status.disposition.value,
        summary=status.summary,
        fixup_inventory_count=status.fixup_inventory_count,
        latest_fixup_inventory_artifact_id=_optional_str(
            status.latest_fixup_inventory_artifact_id
        ),
        latest_fixup_inventory_sequence=status.latest_fixup_inventory_sequence,
        latest_fixup_inventory_at=status.latest_fixup_inventory_at,
        latest_source_kind=(
            status.latest_source_kind.value
            if status.latest_source_kind is not None
            else None
        ),
        latest_source_summary=status.latest_source_summary,
        inventory_freshness=status.inventory_freshness.value,
        stale=status.stale,
        stale_reason=status.stale_reason,
        changed_path_count=status.changed_path_count,
        matched_scope_path_count=status.matched_scope_path_count,
        path_summaries=status.path_summaries,
        blockers=status.blockers,
        safe_next_actions=status.safe_next_actions,
        non_claims=status.non_claims,
    )


def build_review_response_summary_response(
    summary: ChangesetReviewResponseSummary,
) -> ChangesetReviewResponseSummaryResponse:
    return ChangesetReviewResponseSummaryResponse(
        changeset_id=str(summary.changeset_id),
        total_feedback_count=summary.total_feedback_count,
        open_count=summary.open_count,
        responded_count=summary.responded_count,
        unresolved_count=summary.unresolved_count,
        stale_response_count=summary.stale_response_count,
        accepted_risk_count=summary.accepted_risk_count,
        blocked_count=summary.blocked_count,
        items=[
            build_review_feedback_response_status_response(item)
            for item in summary.items
        ],
        blockers=summary.blockers,
        safe_next_actions=summary.safe_next_actions,
        non_claims=summary.non_claims,
    )


def build_review_feedback_detail_response(
    feedback: ReviewFeedbackRecord,
    scopes: Sequence[ReviewFeedbackScopeRecord],
    response_status: ReviewFeedbackResponseStatus,
) -> ReviewFeedbackDetailResponse:
    return ReviewFeedbackDetailResponse(
        feedback=build_review_feedback_response(feedback),
        scopes=[build_review_feedback_scope_response(scope) for scope in scopes],
        response_status=build_review_feedback_response_status_response(response_status),
        safe_next_actions=[
            f"glassbox changeset feedback show {feedback.feedback_id} --cwd .",
            f"glassbox changeset show {feedback.changeset_id} --cwd .",
        ],
        non_claims=_review_feedback_non_claims(),
    )


def build_review_feedback_action_response(
    result: ReviewFeedbackRecordResult,
) -> ReviewFeedbackActionResponse:
    return ReviewFeedbackActionResponse(
        feedback=build_review_feedback_response(result.feedback),
        scopes=[build_review_feedback_scope_response(scope) for scope in result.scopes],
        event_sequences=[event.sequence for event in result.events],
        safe_next_actions=result.safe_next_actions,
        non_claims=result.non_claims,
    )


def build_changeset_readiness_response(
    readiness: ChangesetReadinessRecord,
) -> ChangesetReadinessResponse:
    return ChangesetReadinessResponse(
        session_id=str(readiness.session_id),
        changeset_id=str(readiness.changeset_id),
        readiness_kind=readiness.readiness_kind.value,
        state=readiness.state.value,
        reason=readiness.reason,
        blockers=readiness.blockers,
        safe_next_actions=readiness.safe_next_actions,
        inventory_artifact_id=_optional_str(readiness.inventory_artifact_id),
        review_brief_artifact_id=_optional_str(readiness.review_brief_artifact_id),
        verification_id=_optional_str(readiness.verification_id),
        task_id=_optional_str(readiness.task_id),
        turn_id=_optional_str(readiness.turn_id),
        accepted_risk_count=readiness.accepted_risk_count,
        decided_by=readiness.decided_by,
        updated_at=readiness.updated_at,
        last_sequence=readiness.last_sequence,
    )


def _optional_str(value: object | None) -> str | None:
    return str(value) if value is not None else None


def _review_feedback_non_claims() -> list[str]:
    return [
        "review feedback is local evidence, not approval",
        "Glassbox did not stage, commit, push, open a PR, or merge",
    ]
