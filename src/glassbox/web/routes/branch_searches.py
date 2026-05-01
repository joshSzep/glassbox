"""Branch-search dashboard API routes."""

from typing import Annotated
from typing import cast
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.core.events import BranchCandidateNeedsReview
from glassbox.core.events import BranchCandidateRejected
from glassbox.core.events import BranchCandidateSelected
from glassbox.core.events import EventEnvelope
from glassbox.runtime.branch_decision_support import (
    derive_branch_search_decision_support,
)
from glassbox.runtime.branch_search import BranchSearchQueryService
from glassbox.runtime.branch_search import BranchSearchRepository
from glassbox.web.app import RuntimeContextDep
from glassbox.web.branch_search_api import BranchCandidateActionRequest
from glassbox.web.branch_search_api import BranchCandidateActionResponse
from glassbox.web.branch_search_api import BranchSearchDetailResponse
from glassbox.web.branch_search_api import BranchSearchListPageResponse
from glassbox.web.branch_search_api import build_branch_candidate_response
from glassbox.web.branch_search_api import build_branch_candidate_responses
from glassbox.web.branch_search_api import build_branch_search_decision_support_response
from glassbox.web.branch_search_api import build_branch_search_summary_response
from glassbox.web.branch_search_api import build_branch_search_summary_responses
from glassbox.web.session_api import ErrorDetailResponse

router = APIRouter(prefix="/branch-searches")

LimitParam = Annotated[int | None, Query(ge=1, le=200)]


def _query_service(context: RuntimeContextDep) -> BranchSearchQueryService:
    return BranchSearchQueryService(
        cast(BranchSearchRepository, context.repositories.sessions)
    )


@router.get("", response_model=BranchSearchListPageResponse)
async def list_branch_searches(
    context: RuntimeContextDep,
    session_id: UUID | None = None,
    limit: LimitParam = 100,
) -> BranchSearchListPageResponse:
    """Return branch-search summaries for the dashboard comparison queue."""

    searches = _query_service(context).list_searches(
        session_id=session_id,
        limit=limit,
    )
    return BranchSearchListPageResponse(
        items=build_branch_search_summary_responses(searches)
    )


@router.get(
    "/{search_id}",
    response_model=BranchSearchDetailResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_branch_search_detail(
    search_id: UUID,
    context: RuntimeContextDep,
) -> BranchSearchDetailResponse:
    """Return one branch search with candidate comparison rows."""

    try:
        detail = _query_service(context).get_detail(search_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return BranchSearchDetailResponse(
        search=build_branch_search_summary_response(detail.search),
        candidates=build_branch_candidate_responses(detail.candidates),
        decision_support=build_branch_search_decision_support_response(
            derive_branch_search_decision_support(
                search=detail.search,
                candidates=detail.candidates,
                workspace_root=context.infrastructure.artifacts_root,
            )
        ),
    )


@router.post(
    "/{search_id}/candidates/{candidate_id}/select",
    response_model=BranchCandidateActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def select_branch_candidate(
    search_id: UUID,
    candidate_id: UUID,
    request: BranchCandidateActionRequest,
    context: RuntimeContextDep,
) -> BranchCandidateActionResponse:
    """Mark a branch-search candidate as selected metadata."""

    return _mark_candidate(
        search_id,
        candidate_id,
        request,
        context,
        action="selected",
    )


@router.post(
    "/{search_id}/candidates/{candidate_id}/reject",
    response_model=BranchCandidateActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def reject_branch_candidate(
    search_id: UUID,
    candidate_id: UUID,
    request: BranchCandidateActionRequest,
    context: RuntimeContextDep,
) -> BranchCandidateActionResponse:
    """Mark a branch-search candidate as rejected evidence."""

    return _mark_candidate(
        search_id,
        candidate_id,
        request,
        context,
        action="rejected",
    )


@router.post(
    "/{search_id}/candidates/{candidate_id}/needs-review",
    response_model=BranchCandidateActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def mark_branch_candidate_needs_review(
    search_id: UUID,
    candidate_id: UUID,
    request: BranchCandidateActionRequest,
    context: RuntimeContextDep,
) -> BranchCandidateActionResponse:
    """Mark a branch-search candidate as needing more operator review."""

    return _mark_candidate(
        search_id,
        candidate_id,
        request,
        context,
        action="needs_review",
    )


def _mark_candidate(
    search_id: UUID,
    candidate_id: UUID,
    request: BranchCandidateActionRequest,
    context: RuntimeContextDep,
    *,
    action: str,
) -> BranchCandidateActionResponse:
    service = _query_service(context)
    try:
        detail = service.get_detail(search_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    candidate = next(
        (item for item in detail.candidates if item.candidate_id == candidate_id),
        None,
    )
    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=f"unknown branch-search candidate: {candidate_id}",
        )
    context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=detail.search.session_id,
            sequence=0,
            payload=_mark_candidate_payload(
                search_id,
                candidate_id,
                request,
                action=action,
            ),
        )
    )
    refreshed = service.get_detail(search_id)
    updated = next(
        item for item in refreshed.candidates if item.candidate_id == candidate_id
    )
    return BranchCandidateActionResponse(
        status=action,
        candidate=build_branch_candidate_response(updated),
    )


def _mark_candidate_payload(
    search_id: UUID,
    candidate_id: UUID,
    request: BranchCandidateActionRequest,
    *,
    action: str,
):
    if action == "selected":
        return BranchCandidateSelected(
            search_id=search_id,
            candidate_id=candidate_id,
            selected_by=request.actor,
            reason=request.reason,
        )
    if action == "rejected":
        return BranchCandidateRejected(
            search_id=search_id,
            candidate_id=candidate_id,
            rejected_by=request.actor,
            reason=request.reason,
        )
    return BranchCandidateNeedsReview(
        search_id=search_id,
        candidate_id=candidate_id,
        marked_by=request.actor,
        reason=request.reason,
    )
