"""Feedback route helpers for changeset dashboard APIs."""

from uuid import UUID

from fastapi import HTTPException

from glassbox.runtime.context import RuntimeContext
from glassbox.web.changeset_api import ReviewFeedbackAcceptRiskRequest
from glassbox.web.changeset_api import ReviewFeedbackActionResponse
from glassbox.web.changeset_api import ReviewFeedbackArchiveRequest
from glassbox.web.changeset_api import ReviewFeedbackCreateRequest
from glassbox.web.changeset_api import ReviewFeedbackDetailResponse
from glassbox.web.changeset_api import ReviewFeedbackFixupInventoryActionResponse
from glassbox.web.changeset_api import ReviewFeedbackFixupInventoryRequest
from glassbox.web.changeset_api import ReviewFeedbackReopenRequest
from glassbox.web.changeset_api import ReviewFeedbackResolveRequest
from glassbox.web.changeset_api import build_review_feedback_action_response
from glassbox.web.changeset_api import build_review_feedback_detail_response
from glassbox.web.changeset_api import (
    build_review_feedback_fixup_inventory_action_response,
)
from glassbox.web.routes.changeset_route_errors import raise_not_found_from_value_error
from glassbox.web.routes.changeset_route_errors import raise_unknown_review_feedback
from glassbox.web.routes.changeset_route_requests import optional_uuid
from glassbox.web.routes.changeset_route_requests import review_feedback_kind
from glassbox.web.routes.changeset_route_requests import review_feedback_provenance
from glassbox.web.routes.changeset_route_requests import review_feedback_scope_kind
from glassbox.web.routes.changeset_route_services import changeset_query_service
from glassbox.web.routes.changeset_route_services import changeset_repository
from glassbox.web.routes.changeset_route_services import review_feedback_action_service
from glassbox.web.routes.changeset_route_services import (
    review_feedback_fixup_inventory_service,
)
from glassbox.web.routes.changeset_route_services import workspace_root_for_changeset


def get_review_feedback_detail_response(
    *,
    feedback_id: UUID,
    context: RuntimeContext,
) -> ReviewFeedbackDetailResponse:
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


def add_review_feedback_response(
    *,
    changeset_id: UUID,
    request: ReviewFeedbackCreateRequest,
    context: RuntimeContext,
) -> ReviewFeedbackActionResponse:
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


def resolve_review_feedback_response(
    *,
    feedback_id: UUID,
    request: ReviewFeedbackResolveRequest,
    context: RuntimeContext,
) -> ReviewFeedbackActionResponse:
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


def reopen_review_feedback_response(
    *,
    feedback_id: UUID,
    request: ReviewFeedbackReopenRequest,
    context: RuntimeContext,
) -> ReviewFeedbackActionResponse:
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


def archive_review_feedback_response(
    *,
    feedback_id: UUID,
    request: ReviewFeedbackArchiveRequest,
    context: RuntimeContext,
) -> ReviewFeedbackActionResponse:
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


def accept_review_feedback_risk_response(
    *,
    feedback_id: UUID,
    request: ReviewFeedbackAcceptRiskRequest,
    context: RuntimeContext,
) -> ReviewFeedbackActionResponse:
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


async def record_review_feedback_fixup_inventory_response(
    *,
    feedback_id: UUID,
    request: ReviewFeedbackFixupInventoryRequest,
    context: RuntimeContext,
) -> ReviewFeedbackFixupInventoryActionResponse:
    """Record response-linked fixup inventory and build an HTTP response."""

    if request.from_workspace and request.paths:
        raise HTTPException(
            status_code=422,
            detail="feedback fixup accepts either from_workspace or paths",
        )
    if not request.from_workspace and not request.paths:
        raise HTTPException(
            status_code=422,
            detail="feedback fixup requires from_workspace or at least one path",
        )
    repository = changeset_repository(context)
    service = review_feedback_fixup_inventory_service(context, repository)
    feedback = changeset_query_service(repository).get_review_feedback(feedback_id)
    if feedback is None:
        raise_unknown_review_feedback(feedback_id)
    workspace_root = workspace_root_for_changeset(repository, feedback.changeset_id)
    try:
        if request.paths:
            result = service.record_explicit_paths(
                feedback_id,
                workspace_root,
                paths=request.paths,
                source_summary=request.source_summary,
                recorded_by=request.actor,
            )
        else:
            result = await service.record_workspace_inventory(
                feedback_id,
                workspace_root,
                source_summary=request.source_summary,
                recorded_by=request.actor,
            )
        response_status = changeset_query_service(
            repository
        ).get_review_feedback_response_status(
            feedback_id,
            workspace_root=workspace_root,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("unknown "):
            raise_not_found_from_value_error(exc)
        raise HTTPException(status_code=422, detail=message) from exc
    return build_review_feedback_fixup_inventory_action_response(
        result,
        response_status=response_status,
    )


__all__ = [
    "accept_review_feedback_risk_response",
    "add_review_feedback_response",
    "archive_review_feedback_response",
    "get_review_feedback_detail_response",
    "record_review_feedback_fixup_inventory_response",
    "reopen_review_feedback_response",
    "resolve_review_feedback_response",
]
