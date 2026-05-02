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
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetReviewBriefGenerationResult
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.commit_messages import CommitMessageSuggestion


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


class ChangesetDetailResponse(BaseModel):
    changeset: ChangesetSummaryResponse
    sources: list[ChangesetSourceResponse]
    inventory: ChangesetInventoryResponse | None = None
    inventory_status: ChangesetInventoryStatusResponse
    verification_posture: ChangesetVerificationPostureResponse | None = None
    review_briefs: list[ChangesetReviewBriefResponse]
    readiness: list[ChangesetReadinessResponse]
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
    matched_paths: list[str]
    commands: list[str]
    profile_ids: list[str]
    case_ids: list[str]
    notes: str | None = None


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
        readiness=[
            build_changeset_readiness_response(item) for item in detail.readiness
        ],
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
                matched_paths=recipe.matched_paths,
                commands=recipe.commands,
                profile_ids=recipe.profile_ids,
                case_ids=recipe.case_ids,
                notes=recipe.notes,
            )
            for recipe in preview.recipes
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
