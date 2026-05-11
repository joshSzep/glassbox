"""Recommendation and memory-candidate builders for repository intelligence APIs."""

from collections.abc import Sequence

from glassbox.runtime.eval_recommendations import EvalRecommendationReport
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCandidate
from glassbox.web.memory_api import build_workspace_memory_candidate_responses
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceMemoryCandidateListPageResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceVerificationRecommendationResponse,
)
from glassbox.web.session_api import PageInfoResponse


def build_verification_recommendation_response(
    *,
    status: str,
    paths: Sequence[str],
    report: EvalRecommendationReport | None = None,
    detail: str | None = None,
    next_actions: Sequence[str] = (),
) -> RepositoryIntelligenceVerificationRecommendationResponse:
    return RepositoryIntelligenceVerificationRecommendationResponse(
        status=status,
        paths=list(paths),
        report=report,
        detail=detail,
        next_actions=list(next_actions),
    )


def build_memory_candidate_list_page_response(
    *,
    session_id: str,
    cursor: int,
    limit: int,
    candidates: Sequence[WorkspaceMemoryCandidate],
) -> RepositoryIntelligenceMemoryCandidateListPageResponse:
    page_rows = list(candidates[cursor : cursor + limit + 1])
    items = page_rows[:limit]
    next_cursor = cursor + len(items) if len(page_rows) > limit else None
    return RepositoryIntelligenceMemoryCandidateListPageResponse(
        session_id=session_id,
        page=PageInfoResponse(
            cursor=cursor,
            limit=limit,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            returned_count=len(items),
        ),
        items=build_workspace_memory_candidate_responses(items),
    )
