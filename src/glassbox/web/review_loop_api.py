"""HTTP transport models for changeset review-loop APIs."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


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
    verification_state: str
    verification_reason: str | None = None
    verification_requirement_ids: list[str]
    verification_safe_next_actions: list[str]
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


class BrowserEvidenceAttachRequest(BaseModel):
    capture_kind: Literal["browser_check", "dashboard_walkthrough"]
    summary: str = Field(min_length=1, max_length=1000)
    source_label: str = Field(min_length=1, max_length=200)
    route_label: str = Field(min_length=1, max_length=300)
    environment: str = Field(min_length=1, max_length=200)
    browser: str = Field(default="unknown", min_length=1, max_length=200)
    viewport_width: int = Field(ge=1, le=10000)
    viewport_height: int = Field(ge=1, le=10000)
    observed_at: datetime | None = None
    input_method: str = Field(default="unknown", min_length=1, max_length=100)
    console_checked: bool | None = None
    screenshot_path_hint: str | None = Field(default=None, max_length=500)
    screenshot_label: str = Field(
        default="local screenshot metadata",
        min_length=1,
        max_length=200,
    )
    screenshot_media_type: str = Field(
        default="image/png", min_length=1, max_length=100
    )
    screenshot_size_bytes: int | None = Field(default=None, ge=0)
    screenshot_width: int | None = Field(default=None, ge=1, le=10000)
    screenshot_height: int | None = Field(default=None, ge=1, le=10000)
    skipped_cases: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)
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
    freshness: str = Field(
        default="unknown",
        pattern="^(current|needs_inspection|stale|unknown)$",
    )


class AccessibilityEvidenceAttachRequest(BaseModel):
    observation_kind: Literal[
        "keyboard_pass",
        "screen_reader_note",
        "focus_order_issue",
        "wrapping_issue",
        "contrast_observation",
        "responsive_review",
    ]
    summary: str = Field(min_length=1, max_length=1000)
    source_label: str = Field(min_length=1, max_length=200)
    environment: str = Field(min_length=1, max_length=200)
    observed_issue: str = Field(min_length=1, max_length=2000)
    tool: str = Field(default="manual", min_length=1, max_length=200)
    route_label: str | None = Field(default=None, max_length=300)
    reviewer_label: str | None = Field(default=None, max_length=200)
    severity: Literal["info", "low", "medium", "high", "blocker"] = "medium"
    disposition: Literal[
        "open",
        "paired_with_feedback",
        "resolved_locally",
        "accepted_with_risk",
        "needs_follow_up",
    ] = "open"
    follow_up: str | None = Field(default=None, max_length=2000)
    paired_tool_output_label: str | None = Field(default=None, max_length=300)
    skipped_cases: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)
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


class ReviewFeedbackFixupInventoryRequest(BaseModel):
    from_workspace: bool = True
    paths: list[str] = Field(default_factory=list, max_length=100)
    source_summary: str = Field(
        default="dashboard recorded response-linked workspace inventory",
        min_length=1,
        max_length=2000,
    )
    actor: str = Field(default="operator", min_length=1, max_length=200)


class ReviewFeedbackFixupInventoryStatusResponse(BaseModel):
    freshness: str
    stale: bool
    reason: str | None = None
    recorded_source_digest: str | None = None
    current_source_digest: str | None = None
    safe_next_actions: list[str]


class ReviewFeedbackFixupInventoryActionResponse(BaseModel):
    feedback_id: str
    changeset_id: str
    session_id: str
    artifact_id: str
    artifact_path: str
    event_sequence: int
    changed_path_count: int
    matched_scope_path_count: int
    inventory_freshness: str
    path_summaries: list[str]
    status: ReviewFeedbackFixupInventoryStatusResponse
    response_status: ReviewFeedbackResponseStatusResponse
    safe_next_actions: list[str]
    non_claims: list[str]


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


__all__ = (
    "ReviewFeedbackScopeResponse",
    "ReviewFeedbackResponse",
    "ReviewFeedbackResponseStatusResponse",
    "ChangesetReviewResponseSummaryResponse",
    "ManualEvidenceResponse",
    "ReviewFeedbackCreateRequest",
    "ManualEvidenceAttachRequest",
    "BrowserEvidenceAttachRequest",
    "AccessibilityEvidenceAttachRequest",
    "ManualEvidenceListPageResponse",
    "ManualEvidenceActionResponse",
    "ReviewFeedbackResolveRequest",
    "ReviewFeedbackReopenRequest",
    "ReviewFeedbackArchiveRequest",
    "ReviewFeedbackAcceptRiskRequest",
    "ReviewFeedbackFixupInventoryRequest",
    "ReviewFeedbackFixupInventoryStatusResponse",
    "ReviewFeedbackFixupInventoryActionResponse",
    "ReviewFeedbackListPageResponse",
    "ReviewFeedbackDetailResponse",
    "ReviewFeedbackActionResponse",
)
