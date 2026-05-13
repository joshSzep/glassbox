"""Detail and inventory response builders."""

from collections.abc import Sequence

from glassbox.core.models import ChangesetInventoryRecord
from glassbox.core.models import ChangesetReadinessRecord
from glassbox.core.models import ChangesetRecord
from glassbox.core.models import ChangesetReviewBriefRecord
from glassbox.core.models import ChangesetSourceRecord
from glassbox.runtime.changesets import ChangesetDetailView
from glassbox.runtime.changesets import ChangesetReviewBriefGenerationResult
from glassbox.web.changeset_api_builders_review import build_manual_evidence_response
from glassbox.web.changeset_api_builders_review import build_review_feedback_response
from glassbox.web.changeset_api_builders_review import (
    build_review_response_summary_response,
)
from glassbox.web.changeset_api_builders_verification import (
    build_changeset_verification_plan_response,
)
from glassbox.web.changeset_api_builders_verification import (
    build_changeset_verification_plan_summary_response,
)
from glassbox.web.changeset_api_builders_verification import (
    build_changeset_verification_posture_response,
)
from glassbox.web.changeset_api_builders_verification import (
    build_changeset_verification_readiness_response,
)
from glassbox.web.changeset_api_builders_verification import (
    build_verification_review_loop_summary_response,
)
from glassbox.web.changeset_api_models import ChangesetCommandEvidenceItemResponse
from glassbox.web.changeset_api_models import ChangesetCommandEvidenceSummaryResponse
from glassbox.web.changeset_api_models import ChangesetDetailResponse
from glassbox.web.changeset_api_models import ChangesetInventoryResponse
from glassbox.web.changeset_api_models import ChangesetInventoryStatusResponse
from glassbox.web.changeset_api_models import ChangesetReadinessResponse
from glassbox.web.changeset_api_models import ChangesetReviewBriefGenerateResponse
from glassbox.web.changeset_api_models import ChangesetReviewBriefResponse
from glassbox.web.changeset_api_models import ChangesetSourceResponse
from glassbox.web.changeset_api_models import ChangesetSummaryResponse


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
        verification_plan_summary=build_changeset_verification_plan_summary_response(
            detail.verification_plan_summary
        ),
        limitations=detail.limitations,
        safe_next_actions=detail.safe_next_actions,
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
        limitation_summary=(
            result.limitation_summary.model_dump(mode="json")
            if result.limitation_summary is not None
            else None
        ),
        detail=build_changeset_detail_response(detail),
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


__all__ = (
    "build_changeset_summary_response",
    "build_changeset_summary_responses",
    "build_changeset_detail_response",
    "build_changeset_verification_plan_response",
    "build_verification_review_loop_summary_response",
    "build_changeset_verification_readiness_response",
    "build_changeset_review_brief_generate_response",
    "build_changeset_source_response",
    "build_changeset_inventory_response",
    "build_changeset_verification_posture_response",
    "build_changeset_review_brief_response",
    "build_changeset_readiness_response",
    "_optional_str",
)
