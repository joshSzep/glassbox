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
from glassbox.web.changeset_api import build_changeset_detail_response
from glassbox.web.changeset_api import build_changeset_review_brief_generate_response
from glassbox.web.changeset_api import build_changeset_summary_responses
from glassbox.web.changeset_api import build_changeset_verification_plan_response
from glassbox.web.changeset_api import build_changeset_verification_readiness_response
from glassbox.web.changeset_api import build_commit_message_suggestion_response
from glassbox.web.changeset_api import build_commit_readiness_response
from glassbox.web.changeset_api import build_handoff_readiness_response
from glassbox.web.changeset_api import build_manual_evidence_action_response
from glassbox.web.changeset_api import build_manual_evidence_response
from glassbox.web.changeset_api import build_review_feedback_action_response
from glassbox.web.changeset_api import build_review_feedback_detail_response
from glassbox.web.changeset_api import build_review_feedback_response
from glassbox.web.changeset_api import build_review_response_summary_response
from glassbox.web.routes.changeset_route_errors import raise_not_found_from_value_error
from glassbox.web.routes.changeset_route_errors import raise_unknown_review_feedback
from glassbox.web.routes.changeset_route_errors import (
    raise_validation_or_not_found_from_value_error,
)
from glassbox.web.routes.changeset_route_feedback import (
    record_review_feedback_fixup_inventory_response,
)
from glassbox.web.routes.changeset_route_requests import create_changeset_from_request
from glassbox.web.routes.changeset_route_requests import manual_evidence_freshness
from glassbox.web.routes.changeset_route_requests import manual_evidence_kind
from glassbox.web.routes.changeset_route_requests import manual_evidence_state
from glassbox.web.routes.changeset_route_requests import manual_evidence_target_kind
from glassbox.web.routes.changeset_route_requests import optional_uuid
from glassbox.web.routes.changeset_route_requests import record_verification_id
from glassbox.web.routes.changeset_route_requests import record_verification_task_id
from glassbox.web.routes.changeset_route_requests import review_feedback_disposition
from glassbox.web.routes.changeset_route_requests import review_feedback_kind
from glassbox.web.routes.changeset_route_requests import review_feedback_provenance
from glassbox.web.routes.changeset_route_requests import review_feedback_scope_kind
from glassbox.web.routes.changeset_route_services import (
    accessibility_evidence_action_service,
)
from glassbox.web.routes.changeset_route_services import browser_evidence_action_service
from glassbox.web.routes.changeset_route_services import changeset_action_service
from glassbox.web.routes.changeset_route_services import changeset_derivation_service
from glassbox.web.routes.changeset_route_services import changeset_query_service
from glassbox.web.routes.changeset_route_services import changeset_repository
from glassbox.web.routes.changeset_route_services import changeset_review_brief_service
from glassbox.web.routes.changeset_route_services import changeset_verification_service
from glassbox.web.routes.changeset_route_services import (
    commit_message_suggestion_service,
)
from glassbox.web.routes.changeset_route_services import commit_readiness_service
from glassbox.web.routes.changeset_route_services import handoff_readiness_service
from glassbox.web.routes.changeset_route_services import manual_evidence_action_service
from glassbox.web.routes.changeset_route_services import review_feedback_action_service
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

    repository = changeset_repository(context)
    service = changeset_derivation_service(repository)
    try:
        result = create_changeset_from_request(
            request,
            repository=repository,
            service=service,
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return ChangesetCreateResponse(
        changeset_id=str(result.changeset_id),
        session_id=str(result.session_id),
        limitations=result.limitations,
        event_count=len(result.stored_events),
    )


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

    repository = changeset_repository(context)
    service = changeset_query_service(repository)
    feedback = service.get_review_feedback(feedback_id)
    if feedback is None:
        raise_unknown_review_feedback(feedback_id)
    scopes = service.list_review_feedback_scopes(
        feedback.session_id, feedback.feedback_id
    )
    response_status = service.get_review_feedback_response_status(
        feedback.feedback_id,
        workspace_root=workspace_root_for_changeset(repository, feedback.changeset_id),
    )
    return build_review_feedback_detail_response(feedback, scopes, response_status)


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

    repository = changeset_repository(context)
    try:
        result = manual_evidence_action_service(context, repository).attach(
            changeset_id,
            evidence_kind=manual_evidence_kind(request),
            summary=request.summary,
            source_label=request.source_label,
            actor=request.actor,
            target_kind=manual_evidence_target_kind(request),
            target_id=request.target_id,
            feedback_id=optional_uuid(request.feedback_id),
            note=request.note,
            command_text=request.command_text,
            external_url_label=request.external_url_label,
            local_file_label=request.local_file_label,
            local_file_path_hint=request.local_file_path_hint,
            freshness=manual_evidence_freshness(request),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_manual_evidence_action_response(result)


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

    repository = changeset_repository(context)
    try:
        result = browser_evidence_action_service(context, repository).attach(
            changeset_id,
            capture_state=request.capture_state,
            capture_kind=request.capture_kind,
            summary=request.summary,
            source_label=request.source_label,
            route_label=request.route_label,
            environment=request.environment,
            browser=request.browser,
            viewport_width=request.viewport_width,
            viewport_height=request.viewport_height,
            observed_at=request.observed_at,
            input_method=request.input_method,
            console_checked=request.console_checked,
            skip_reason=request.skip_reason,
            screenshot_path_hint=request.screenshot_path_hint,
            screenshot_label=request.screenshot_label,
            screenshot_media_type=request.screenshot_media_type,
            screenshot_size_bytes=request.screenshot_size_bytes,
            screenshot_width=request.screenshot_width,
            screenshot_height=request.screenshot_height,
            skipped_cases=request.skipped_cases,
            limitations=request.limitations,
            actor=request.actor,
            target_kind=manual_evidence_target_kind(request),
            target_id=request.target_id,
            feedback_id=optional_uuid(request.feedback_id),
            freshness=manual_evidence_freshness(request),
        )
    except ValueError as exc:
        raise_validation_or_not_found_from_value_error(exc)
    return build_manual_evidence_action_response(result)


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

    repository = changeset_repository(context)
    try:
        result = accessibility_evidence_action_service(context, repository).attach(
            changeset_id,
            capture_state=request.capture_state,
            observation_kind=request.observation_kind,
            summary=request.summary,
            source_label=request.source_label,
            environment=request.environment,
            observed_issue=request.observed_issue,
            tool=request.tool,
            route_label=request.route_label,
            reviewer_label=request.reviewer_label,
            severity=request.severity,
            disposition=request.disposition,
            follow_up=request.follow_up,
            paired_tool_output_label=request.paired_tool_output_label,
            skip_reason=request.skip_reason,
            skipped_cases=request.skipped_cases,
            limitations=request.limitations,
            actor=request.actor,
            target_kind=manual_evidence_target_kind(request),
            target_id=request.target_id,
            feedback_id=optional_uuid(request.feedback_id),
            freshness=manual_evidence_freshness(request),
        )
    except ValueError as exc:
        raise_validation_or_not_found_from_value_error(exc)
    return build_manual_evidence_action_response(result)


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

    repository = changeset_repository(context)
    try:
        detail = changeset_query_service(repository).get_detail(
            changeset_id,
            workspace_root=workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_changeset_detail_response(detail)


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

    repository = changeset_repository(context)
    try:
        result = review_feedback_action_service(repository).add_feedback(
            changeset_id,
            feedback_kind=review_feedback_kind(request),
            provenance=review_feedback_provenance(request),
            summary=request.summary,
            body=request.body,
            source_label=request.source_label,
            reviewer_label=request.reviewer_label,
            created_by=request.actor,
            scope_kind=review_feedback_scope_kind(request),
            scope_reason=request.scope_reason,
            file_path=request.file_path,
            line_start=request.line_start,
            line_end=request.line_end,
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_review_feedback_action_response(result)


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

    repository = changeset_repository(context)
    try:
        result = review_feedback_action_service(repository).resolve_feedback(
            feedback_id,
            resolution_summary=request.summary,
            residual_risk=request.residual_risk,
            resolved_by=request.actor,
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_review_feedback_action_response(result)


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

    repository = changeset_repository(context)
    try:
        result = review_feedback_action_service(repository).reopen_feedback(
            feedback_id,
            reason=request.reason,
            reopened_by=request.actor,
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_review_feedback_action_response(result)


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

    repository = changeset_repository(context)
    try:
        result = review_feedback_action_service(repository).archive_feedback(
            feedback_id,
            reason=request.reason,
            archived_by=request.actor,
            replacement_feedback_id=optional_uuid(request.replacement_feedback_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_review_feedback_action_response(result)


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

    repository = changeset_repository(context)
    try:
        result = review_feedback_action_service(repository).accept_risk(
            feedback_id,
            risk_summary=request.risk_summary,
            acceptance_reason=request.reason,
            accepted_by=request.actor,
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_review_feedback_action_response(result)


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

    repository = changeset_repository(context)
    try:
        result = await changeset_action_service(context, repository).refresh_inventory(
            changeset_id,
            workspace_root_for_changeset(repository, changeset_id),
            refreshed_by=request.actor,
        )
        detail = changeset_query_service(repository).get_detail(
            changeset_id,
            workspace_root=workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return ChangesetActionResponse(
        changeset_id=str(changeset_id),
        status="refreshed",
        event_sequence=result.event.sequence,
        detail=build_changeset_detail_response(detail),
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

    repository = changeset_repository(context)
    try:
        preview = changeset_verification_service(context, repository).preview_plan(
            changeset_id,
            workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_changeset_verification_plan_response(preview)


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

    repository = changeset_repository(context)
    try:
        result = changeset_verification_service(
            context,
            repository,
        ).record_existing_evidence(
            changeset_id,
            workspace_root_for_changeset(repository, changeset_id),
            task_id=record_verification_task_id(request),
            verification_id=record_verification_id(request),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return ChangesetRecordVerificationResponse(
        changeset_id=str(result.changeset_id),
        session_id=str(result.session_id),
        selected_verification_ids=[
            str(verification_id) for verification_id in result.selected_verification_ids
        ],
        retained_artifact_ids=[
            str(artifact_id) for artifact_id in result.retained_artifact_ids
        ],
        readiness=build_changeset_verification_readiness_response(result.readiness),
        event_sequence=result.event.sequence,
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

    repository = changeset_repository(context)
    try:
        workspace_root = workspace_root_for_changeset(repository, changeset_id)
        result = changeset_review_brief_service(context, repository).generate(
            changeset_id,
            workspace_root,
            created_by=request.actor,
        )
        detail = changeset_query_service(repository).get_detail(
            changeset_id,
            workspace_root=workspace_root,
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_changeset_review_brief_generate_response(
        result,
        detail,
        include_markdown=request.include_markdown,
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

    repository = changeset_repository(context)
    try:
        suggestion = await commit_message_suggestion_service(
            context,
            repository,
        ).suggest(
            changeset_id,
            workspace_root_for_changeset(repository, changeset_id),
            style=style,
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_commit_message_suggestion_response(suggestion)


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

    repository = changeset_repository(context)
    try:
        readiness = await commit_readiness_service(context, repository).preview(
            changeset_id,
            workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_commit_readiness_response(readiness)


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

    repository = changeset_repository(context)
    try:
        readiness = await handoff_readiness_service(context, repository).preview(
            changeset_id,
            workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_handoff_readiness_response(readiness)


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

    repository = changeset_repository(context)
    try:
        event = changeset_action_service(context, repository).archive_changeset(
            changeset_id,
            reason=request.reason,
            archived_by=request.actor,
            replacement_changeset_id=optional_uuid(request.replacement_changeset_id),
        )
        detail = changeset_query_service(repository).get_detail(
            changeset_id,
            workspace_root=workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return ChangesetActionResponse(
        changeset_id=str(changeset_id),
        status="archived",
        event_sequence=event.sequence,
        detail=build_changeset_detail_response(detail),
    )
