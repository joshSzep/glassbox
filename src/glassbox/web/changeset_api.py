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
