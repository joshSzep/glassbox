"""Changeset dashboard API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Query

from glassbox.web.app import RuntimeContextDep
from glassbox.web.changeset_api import AccessibilityEvidenceAttachRequest
from glassbox.web.changeset_api import BrowserEvidenceAttachRequest
from glassbox.web.changeset_api import ChangesetActionResponse
from glassbox.web.changeset_api import ChangesetArchiveRequest
from glassbox.web.changeset_api import ChangesetCreateRequest
from glassbox.web.changeset_api import ChangesetCreateResponse
from glassbox.web.changeset_api import ChangesetDetailResponse
from glassbox.web.changeset_api import ChangesetListPageResponse
from glassbox.web.changeset_api import ChangesetRecordVerificationRequest
from glassbox.web.changeset_api import ChangesetRecordVerificationResponse
from glassbox.web.changeset_api import ChangesetRefreshRequest
from glassbox.web.changeset_api import ChangesetReviewBriefGenerateResponse
from glassbox.web.changeset_api import ChangesetReviewBriefRequest
from glassbox.web.changeset_api import ChangesetVerificationPlanPreviewResponse
from glassbox.web.changeset_api import CommitMessageSuggestionResponse
from glassbox.web.changeset_api import CommitReadinessResponse
from glassbox.web.changeset_api import HandoffReadinessResponse
from glassbox.web.changeset_api import ManualEvidenceActionResponse
from glassbox.web.changeset_api import ManualEvidenceAttachRequest
from glassbox.web.changeset_api import ManualEvidenceListPageResponse
from glassbox.web.changeset_api import ReviewFeedbackAcceptRiskRequest
from glassbox.web.changeset_api import ReviewFeedbackActionResponse
from glassbox.web.changeset_api import ReviewFeedbackArchiveRequest
from glassbox.web.changeset_api import ReviewFeedbackCreateRequest
from glassbox.web.changeset_api import ReviewFeedbackDetailResponse
from glassbox.web.changeset_api import ReviewFeedbackFixupInventoryActionResponse
from glassbox.web.changeset_api import ReviewFeedbackFixupInventoryRequest
from glassbox.web.changeset_api import ReviewFeedbackListPageResponse
from glassbox.web.changeset_api import ReviewFeedbackReopenRequest
from glassbox.web.changeset_api import ReviewFeedbackResolveRequest
from glassbox.web.changeset_api import build_changeset_summary_responses
from glassbox.web.changeset_api import build_manual_evidence_response
from glassbox.web.changeset_api import build_review_feedback_response
from glassbox.web.changeset_api import build_review_response_summary_response
from glassbox.web.routes.changeset_route_actions import archive_changeset_response
from glassbox.web.routes.changeset_route_actions import (
    attach_accessibility_evidence_response,
)
from glassbox.web.routes.changeset_route_actions import attach_browser_evidence_response
from glassbox.web.routes.changeset_route_actions import attach_manual_evidence_response
from glassbox.web.routes.changeset_route_actions import create_changeset_response
from glassbox.web.routes.changeset_route_actions import (
    generate_changeset_review_brief_response,
)
from glassbox.web.routes.changeset_route_actions import get_changeset_detail_response
from glassbox.web.routes.changeset_route_actions import (
    preview_changeset_commit_readiness_response,
)
from glassbox.web.routes.changeset_route_actions import (
    preview_changeset_handoff_readiness_response,
)
from glassbox.web.routes.changeset_route_actions import (
    preview_changeset_verification_plan_response,
)
from glassbox.web.routes.changeset_route_actions import (
    record_changeset_verification_response,
)
from glassbox.web.routes.changeset_route_actions import refresh_changeset_response
from glassbox.web.routes.changeset_route_actions import (
    suggest_changeset_commit_message_response,
)
from glassbox.web.routes.changeset_route_feedback import (
    accept_review_feedback_risk_response,
)
from glassbox.web.routes.changeset_route_feedback import add_review_feedback_response
from glassbox.web.routes.changeset_route_feedback import (
    archive_review_feedback_response,
)
from glassbox.web.routes.changeset_route_feedback import (
    get_review_feedback_detail_response,
)
from glassbox.web.routes.changeset_route_feedback import (
    record_review_feedback_fixup_inventory_response,
)
from glassbox.web.routes.changeset_route_feedback import reopen_review_feedback_response
from glassbox.web.routes.changeset_route_feedback import (
    resolve_review_feedback_response,
)
from glassbox.web.routes.changeset_route_requests import manual_evidence_state
from glassbox.web.routes.changeset_route_requests import review_feedback_disposition
from glassbox.web.routes.changeset_route_services import changeset_query_service
from glassbox.web.routes.changeset_route_services import changeset_repository
from glassbox.web.routes.changeset_route_services import workspace_root_for_changeset
from glassbox.web.session_api import ErrorDetailResponse

router = APIRouter(prefix="/changesets")

LimitParam = Annotated[int | None, Query(ge=1, le=200)]


@router.get("", response_model=ChangesetListPageResponse)
async def list_changesets(
    context: RuntimeContextDep,
    session_id: UUID | None = None,
    include_archived: bool = False,
    limit: LimitParam = 100,
) -> ChangesetListPageResponse:
    """Return recent changesets for dashboard inspection."""

    changesets = changeset_query_service(changeset_repository(context)).list_changesets(
        session_id=session_id,
        include_archived=include_archived,
        limit=limit,
    )
    return ChangesetListPageResponse(
        items=build_changeset_summary_responses(changesets)
    )


@router.post("", response_model=ChangesetCreateResponse)
async def create_changeset(
    request: ChangesetCreateRequest,
    context: RuntimeContextDep,
) -> ChangesetCreateResponse:
    """Create an explicit local changeset from retained evidence."""

    return create_changeset_response(request=request, context=context)


@router.get(
    "/feedback",
    response_model=ReviewFeedbackListPageResponse,
)
async def list_review_feedback(
    context: RuntimeContextDep,
    session_id: UUID | None = None,
    changeset_id: UUID | None = None,
    disposition: str | None = Query(
        default=None,
        pattern="^(open|in_progress|responded|resolved_locally|accepted_with_risk|archived)$",
    ),
    include_archived: bool = False,
    file_path: str | None = None,
    limit: LimitParam = 100,
) -> ReviewFeedbackListPageResponse:
    """Return bounded local review feedback rows for dashboard inspection."""

    repository = changeset_repository(context)
    service = changeset_query_service(repository)
    feedback = service.list_review_feedback(
        session_id=session_id,
        changeset_id=changeset_id,
        disposition=(review_feedback_disposition(disposition)),
        include_archived=include_archived,
        file_path=file_path,
        limit=limit,
    )
    response_summary = (
        service.get_review_response_summary(
            changeset_id,
            workspace_root=workspace_root_for_changeset(repository, changeset_id),
        )
        if changeset_id is not None
        else None
    )
    return ReviewFeedbackListPageResponse(
        items=[build_review_feedback_response(item) for item in feedback],
        response_summary=(
            build_review_response_summary_response(response_summary)
            if response_summary is not None
            else None
        ),
    )


@router.get(
    "/manual-evidence",
    response_model=ManualEvidenceListPageResponse,
)
async def list_manual_evidence(
    context: RuntimeContextDep,
    session_id: UUID | None = None,
    changeset_id: UUID | None = None,
    state: str | None = Query(
        default=None,
        pattern="^(attached|superseded|rejected|archived)$",
    ),
    include_archived: bool = False,
    include_rejected: bool = False,
    include_superseded: bool = False,
    limit: LimitParam = 100,
) -> ManualEvidenceListPageResponse:
    """Return bounded manual evidence rows for dashboard inspection."""

    evidence = changeset_query_service(
        changeset_repository(context)
    ).list_manual_evidence(
        session_id=session_id,
        changeset_id=changeset_id,
        state=manual_evidence_state(state),
        include_archived=include_archived,
        include_rejected=include_rejected,
        include_superseded=include_superseded,
        limit=limit,
    )
    return ManualEvidenceListPageResponse(
        items=[build_manual_evidence_response(item) for item in evidence]
    )


@router.get(
    "/feedback/{feedback_id}",
    response_model=ReviewFeedbackDetailResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_review_feedback_detail(
    feedback_id: UUID,
    context: RuntimeContextDep,
) -> ReviewFeedbackDetailResponse:
    """Return one local review-feedback record with bounded scope metadata."""

    return get_review_feedback_detail_response(
        feedback_id=feedback_id,
        context=context,
    )


@router.post(
    "/{changeset_id}/manual-evidence",
    response_model=ManualEvidenceActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def attach_manual_evidence(
    changeset_id: UUID,
    request: ManualEvidenceAttachRequest,
    context: RuntimeContextDep,
) -> ManualEvidenceActionResponse:
    """Attach summary-first manual evidence to one local changeset."""

    return attach_manual_evidence_response(
        changeset_id=changeset_id,
        request=request,
        context=context,
    )


@router.post(
    "/{changeset_id}/browser-evidence",
    response_model=ManualEvidenceActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def attach_browser_evidence(
    changeset_id: UUID,
    request: BrowserEvidenceAttachRequest,
    context: RuntimeContextDep,
) -> ManualEvidenceActionResponse:
    """Attach advisory browser or dashboard evidence to one local changeset."""

    return attach_browser_evidence_response(
        changeset_id=changeset_id,
        request=request,
        context=context,
    )


@router.post(
    "/{changeset_id}/accessibility-evidence",
    response_model=ManualEvidenceActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def attach_accessibility_evidence(
    changeset_id: UUID,
    request: AccessibilityEvidenceAttachRequest,
    context: RuntimeContextDep,
) -> ManualEvidenceActionResponse:
    """Attach advisory accessibility evidence to one local changeset."""

    return attach_accessibility_evidence_response(
        changeset_id=changeset_id,
        request=request,
        context=context,
    )


@router.get(
    "/{changeset_id}",
    response_model=ChangesetDetailResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_changeset_detail(
    changeset_id: UUID,
    context: RuntimeContextDep,
) -> ChangesetDetailResponse:
    """Return one changeset with source and evidence references."""

    return get_changeset_detail_response(
        changeset_id=changeset_id,
        context=context,
    )


@router.post(
    "/{changeset_id}/feedback",
    response_model=ReviewFeedbackActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def add_review_feedback(
    changeset_id: UUID,
    request: ReviewFeedbackCreateRequest,
    context: RuntimeContextDep,
) -> ReviewFeedbackActionResponse:
    """Record local review feedback evidence for one changeset."""

    return add_review_feedback_response(
        changeset_id=changeset_id,
        request=request,
        context=context,
    )


@router.post(
    "/feedback/{feedback_id}/resolve",
    response_model=ReviewFeedbackActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def resolve_review_feedback(
    feedback_id: UUID,
    request: ReviewFeedbackResolveRequest,
    context: RuntimeContextDep,
) -> ReviewFeedbackActionResponse:
    """Mark local review feedback as resolved locally."""

    return resolve_review_feedback_response(
        feedback_id=feedback_id,
        request=request,
        context=context,
    )


@router.post(
    "/feedback/{feedback_id}/reopen",
    response_model=ReviewFeedbackActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def reopen_review_feedback(
    feedback_id: UUID,
    request: ReviewFeedbackReopenRequest,
    context: RuntimeContextDep,
) -> ReviewFeedbackActionResponse:
    """Reopen local review feedback."""

    return reopen_review_feedback_response(
        feedback_id=feedback_id,
        request=request,
        context=context,
    )


@router.post(
    "/feedback/{feedback_id}/archive",
    response_model=ReviewFeedbackActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def archive_review_feedback(
    feedback_id: UUID,
    request: ReviewFeedbackArchiveRequest,
    context: RuntimeContextDep,
) -> ReviewFeedbackActionResponse:
    """Archive local review feedback after explicit operator intent."""

    return archive_review_feedback_response(
        feedback_id=feedback_id,
        request=request,
        context=context,
    )


@router.post(
    "/feedback/{feedback_id}/accept-risk",
    response_model=ReviewFeedbackActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def accept_review_feedback_risk(
    feedback_id: UUID,
    request: ReviewFeedbackAcceptRiskRequest,
    context: RuntimeContextDep,
) -> ReviewFeedbackActionResponse:
    """Mark local review feedback accepted with explicit residual risk."""

    return accept_review_feedback_risk_response(
        feedback_id=feedback_id,
        request=request,
        context=context,
    )


@router.post(
    "/feedback/{feedback_id}/fixup",
    response_model=ReviewFeedbackFixupInventoryActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def record_review_feedback_fixup_inventory(
    feedback_id: UUID,
    request: ReviewFeedbackFixupInventoryRequest,
    context: RuntimeContextDep,
) -> ReviewFeedbackFixupInventoryActionResponse:
    """Record response-linked fixup inventory for one feedback item."""

    return await record_review_feedback_fixup_inventory_response(
        feedback_id=feedback_id,
        request=request,
        context=context,
    )


@router.post(
    "/{changeset_id}/refresh",
    response_model=ChangesetActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def refresh_changeset(
    changeset_id: UUID,
    request: ChangesetRefreshRequest,
    context: RuntimeContextDep,
) -> ChangesetActionResponse:
    """Refresh structured inventory evidence for a changeset."""

    return await refresh_changeset_response(
        changeset_id=changeset_id,
        request=request,
        context=context,
    )


@router.get(
    "/{changeset_id}/verification-plan",
    response_model=ChangesetVerificationPlanPreviewResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def preview_changeset_verification_plan(
    changeset_id: UUID,
    context: RuntimeContextDep,
) -> ChangesetVerificationPlanPreviewResponse:
    """Preview verification commands and retained evidence for a changeset."""

    return preview_changeset_verification_plan_response(
        changeset_id=changeset_id,
        context=context,
    )


@router.post(
    "/{changeset_id}/record-verification",
    response_model=ChangesetRecordVerificationResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def record_changeset_verification(
    changeset_id: UUID,
    request: ChangesetRecordVerificationRequest,
    context: RuntimeContextDep,
) -> ChangesetRecordVerificationResponse:
    """Record changeset verification posture from existing task evidence."""

    return record_changeset_verification_response(
        changeset_id=changeset_id,
        request=request,
        context=context,
    )


@router.post(
    "/{changeset_id}/brief",
    response_model=ChangesetReviewBriefGenerateResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def generate_changeset_review_brief(
    changeset_id: UUID,
    request: ChangesetReviewBriefRequest,
    context: RuntimeContextDep,
) -> ChangesetReviewBriefGenerateResponse:
    """Generate a reviewer-safe brief artifact for a changeset."""

    return generate_changeset_review_brief_response(
        changeset_id=changeset_id,
        request=request,
        context=context,
    )


@router.get(
    "/{changeset_id}/commit-message",
    response_model=CommitMessageSuggestionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def suggest_changeset_commit_message(
    changeset_id: UUID,
    context: RuntimeContextDep,
    style: str = Query(default="plain", pattern="^(plain|conventional)$"),
) -> CommitMessageSuggestionResponse:
    """Suggest a deterministic commit message without committing."""

    return await suggest_changeset_commit_message_response(
        changeset_id=changeset_id,
        context=context,
        style=style,
    )


@router.get(
    "/{changeset_id}/commit-readiness",
    response_model=CommitReadinessResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def preview_changeset_commit_readiness(
    changeset_id: UUID,
    context: RuntimeContextDep,
) -> CommitReadinessResponse:
    """Preview commit readiness without staging or committing."""

    return await preview_changeset_commit_readiness_response(
        changeset_id=changeset_id,
        context=context,
    )


@router.get(
    "/{changeset_id}/handoff-readiness",
    response_model=HandoffReadinessResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def preview_changeset_handoff_readiness(
    changeset_id: UUID,
    context: RuntimeContextDep,
) -> HandoffReadinessResponse:
    """Preview final handoff readiness without publication mutation."""

    return await preview_changeset_handoff_readiness_response(
        changeset_id=changeset_id,
        context=context,
    )


@router.post(
    "/{changeset_id}/archive",
    response_model=ChangesetActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def archive_changeset(
    changeset_id: UUID,
    request: ChangesetArchiveRequest,
    context: RuntimeContextDep,
) -> ChangesetActionResponse:
    """Archive a changeset after explicit operator intent."""

    return archive_changeset_response(
        changeset_id=changeset_id,
        request=request,
        context=context,
    )
