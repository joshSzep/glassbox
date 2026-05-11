"""Action response helpers for changeset dashboard routes."""

from uuid import UUID

from glassbox.core import ClaimSupport
from glassbox.core import EvidenceGraph
from glassbox.core import EvidenceGraphNode
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.evidence_graph import EvidenceGraphSummary
from glassbox.runtime.evidence_graph import build_changeset_evidence_graph
from glassbox.runtime.evidence_graph import claim_support
from glassbox.runtime.evidence_graph import evidence_neighborhood
from glassbox.runtime.evidence_graph import reviewer_safe_graph_slice
from glassbox.runtime.evidence_graph import summarize_evidence_graph
from glassbox.web.changeset_api import AccessibilityEvidenceAttachRequest
from glassbox.web.changeset_api import BrowserEvidenceAttachRequest
from glassbox.web.changeset_api import ChangesetActionResponse
from glassbox.web.changeset_api import ChangesetArchiveRequest
from glassbox.web.changeset_api import ChangesetCreateRequest
from glassbox.web.changeset_api import ChangesetCreateResponse
from glassbox.web.changeset_api import ChangesetDetailResponse
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
from glassbox.web.changeset_api import build_changeset_detail_response
from glassbox.web.changeset_api import build_changeset_review_brief_generate_response
from glassbox.web.changeset_api import build_changeset_verification_plan_response
from glassbox.web.changeset_api import build_changeset_verification_readiness_response
from glassbox.web.changeset_api import build_commit_message_suggestion_response
from glassbox.web.changeset_api import build_commit_readiness_response
from glassbox.web.changeset_api import build_handoff_readiness_response
from glassbox.web.changeset_api import build_manual_evidence_action_response
from glassbox.web.routes.changeset_route_errors import raise_not_found_from_value_error
from glassbox.web.routes.changeset_route_errors import (
    raise_validation_or_not_found_from_value_error,
)
from glassbox.web.routes.changeset_route_requests import create_changeset_from_request
from glassbox.web.routes.changeset_route_requests import manual_evidence_freshness
from glassbox.web.routes.changeset_route_requests import manual_evidence_kind
from glassbox.web.routes.changeset_route_requests import manual_evidence_target_kind
from glassbox.web.routes.changeset_route_requests import optional_uuid
from glassbox.web.routes.changeset_route_requests import record_verification_id
from glassbox.web.routes.changeset_route_requests import record_verification_task_id
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
from glassbox.web.routes.changeset_route_services import workspace_root_for_changeset


def _changeset_detail_response(
    *,
    context: RuntimeContext,
    changeset_id: UUID,
) -> ChangesetDetailResponse:
    repository = changeset_repository(context)
    detail = changeset_query_service(repository).get_detail(
        changeset_id,
        workspace_root=workspace_root_for_changeset(repository, changeset_id),
    )
    return build_changeset_detail_response(detail)


def create_changeset_response(
    *,
    request: ChangesetCreateRequest,
    context: RuntimeContext,
) -> ChangesetCreateResponse:
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


def get_changeset_detail_response(
    *,
    changeset_id: UUID,
    context: RuntimeContext,
) -> ChangesetDetailResponse:
    try:
        return _changeset_detail_response(context=context, changeset_id=changeset_id)
    except ValueError as exc:
        raise_not_found_from_value_error(exc)


def get_changeset_evidence_graph(
    *,
    changeset_id: UUID,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> EvidenceGraph:
    repository = changeset_repository(context)
    try:
        workspace_root = workspace_root_for_changeset(repository, changeset_id)
        detail = changeset_query_service(repository).get_detail(
            changeset_id,
            workspace_root=workspace_root,
        )
        verification_plan = changeset_verification_service(
            context,
            repository,
        ).preview_plan(changeset_id, workspace_root)
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    graph = build_changeset_evidence_graph(detail, verification_plan=verification_plan)
    return reviewer_safe_graph_slice(graph) if reviewer_safe else graph


def get_changeset_evidence_graph_summary(
    *,
    changeset_id: UUID,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> EvidenceGraphSummary:
    return summarize_evidence_graph(
        get_changeset_evidence_graph(
            changeset_id=changeset_id,
            context=context,
            reviewer_safe=reviewer_safe,
        )
    )


def get_changeset_evidence_graph_claim(
    *,
    changeset_id: UUID,
    claim_id: str,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> ClaimSupport:
    graph = get_changeset_evidence_graph(
        changeset_id=changeset_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )
    support = claim_support(graph, claim_id)
    if support is None:
        raise_not_found_from_value_error(
            ValueError(f"unknown evidence graph claim: {claim_id}")
        )
    return support


def get_changeset_evidence_graph_node(
    *,
    changeset_id: UUID,
    node_id: str,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> EvidenceGraphNode:
    graph = get_changeset_evidence_graph(
        changeset_id=changeset_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )
    for node in graph.nodes:
        if node.node_id == node_id:
            return node
    raise_not_found_from_value_error(
        ValueError(f"unknown evidence graph node: {node_id}")
    )


def get_changeset_evidence_graph_neighborhood(
    *,
    changeset_id: UUID,
    node_id: str,
    depth: int,
    context: RuntimeContext,
    reviewer_safe: bool = False,
) -> EvidenceGraph:
    graph = get_changeset_evidence_graph(
        changeset_id=changeset_id,
        context=context,
        reviewer_safe=reviewer_safe,
    )
    return evidence_neighborhood(graph, node_id, depth=depth)


def attach_manual_evidence_response(
    *,
    changeset_id: UUID,
    request: ManualEvidenceAttachRequest,
    context: RuntimeContext,
) -> ManualEvidenceActionResponse:
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


def attach_browser_evidence_response(
    *,
    changeset_id: UUID,
    request: BrowserEvidenceAttachRequest,
    context: RuntimeContext,
) -> ManualEvidenceActionResponse:
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


def attach_accessibility_evidence_response(
    *,
    changeset_id: UUID,
    request: AccessibilityEvidenceAttachRequest,
    context: RuntimeContext,
) -> ManualEvidenceActionResponse:
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


async def refresh_changeset_response(
    *,
    changeset_id: UUID,
    request: ChangesetRefreshRequest,
    context: RuntimeContext,
) -> ChangesetActionResponse:
    repository = changeset_repository(context)
    try:
        workspace_root = workspace_root_for_changeset(repository, changeset_id)
        result = await changeset_action_service(context, repository).refresh_inventory(
            changeset_id,
            workspace_root,
            refreshed_by=request.actor,
        )
        detail = changeset_query_service(repository).get_detail(
            changeset_id,
            workspace_root=workspace_root,
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return ChangesetActionResponse(
        changeset_id=str(changeset_id),
        status="refreshed",
        event_sequence=result.event.sequence,
        detail=build_changeset_detail_response(detail),
    )


def preview_changeset_verification_plan_response(
    *,
    changeset_id: UUID,
    context: RuntimeContext,
) -> ChangesetVerificationPlanPreviewResponse:
    repository = changeset_repository(context)
    try:
        preview = changeset_verification_service(context, repository).preview_plan(
            changeset_id,
            workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_changeset_verification_plan_response(preview)


def record_changeset_verification_response(
    *,
    changeset_id: UUID,
    request: ChangesetRecordVerificationRequest,
    context: RuntimeContext,
) -> ChangesetRecordVerificationResponse:
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


def generate_changeset_review_brief_response(
    *,
    changeset_id: UUID,
    request: ChangesetReviewBriefRequest,
    context: RuntimeContext,
) -> ChangesetReviewBriefGenerateResponse:
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


async def suggest_changeset_commit_message_response(
    *,
    changeset_id: UUID,
    context: RuntimeContext,
    style: str,
) -> CommitMessageSuggestionResponse:
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


async def preview_changeset_commit_readiness_response(
    *,
    changeset_id: UUID,
    context: RuntimeContext,
) -> CommitReadinessResponse:
    repository = changeset_repository(context)
    try:
        readiness = await commit_readiness_service(context, repository).preview(
            changeset_id,
            workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_commit_readiness_response(readiness)


async def preview_changeset_handoff_readiness_response(
    *,
    changeset_id: UUID,
    context: RuntimeContext,
) -> HandoffReadinessResponse:
    repository = changeset_repository(context)
    try:
        readiness = await handoff_readiness_service(context, repository).preview(
            changeset_id,
            workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return build_handoff_readiness_response(readiness)


def archive_changeset_response(
    *,
    changeset_id: UUID,
    request: ChangesetArchiveRequest,
    context: RuntimeContext,
) -> ChangesetActionResponse:
    repository = changeset_repository(context)
    try:
        workspace_root = workspace_root_for_changeset(repository, changeset_id)
        event = changeset_action_service(context, repository).archive_changeset(
            changeset_id,
            reason=request.reason,
            archived_by=request.actor,
            replacement_changeset_id=optional_uuid(request.replacement_changeset_id),
        )
        detail = changeset_query_service(repository).get_detail(
            changeset_id,
            workspace_root=workspace_root,
        )
    except ValueError as exc:
        raise_not_found_from_value_error(exc)
    return ChangesetActionResponse(
        changeset_id=str(changeset_id),
        status="archived",
        event_sequence=event.sequence,
        detail=build_changeset_detail_response(detail),
    )


__all__ = [
    "archive_changeset_response",
    "attach_accessibility_evidence_response",
    "attach_browser_evidence_response",
    "attach_manual_evidence_response",
    "create_changeset_response",
    "generate_changeset_review_brief_response",
    "get_changeset_detail_response",
    "preview_changeset_commit_readiness_response",
    "preview_changeset_handoff_readiness_response",
    "preview_changeset_verification_plan_response",
    "record_changeset_verification_response",
    "refresh_changeset_response",
    "suggest_changeset_commit_message_response",
]
