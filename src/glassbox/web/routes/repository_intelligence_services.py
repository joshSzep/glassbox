"""Route-local service helpers for repository intelligence APIs."""

from typing import cast
from uuid import UUID

from fastapi import HTTPException

from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
from glassbox.runtime.workspace_memory_capture import MemoryExtractionPolicy
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureRepository
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureService
from glassbox.web.app import RuntimeContextDep
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceMemoryCandidateListPageResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceVerificationRecommendationResponse,
)
from glassbox.web.repository_intelligence_api import (
    build_memory_candidate_list_page_response,
)
from glassbox.web.repository_intelligence_api import (
    build_verification_recommendation_response,
)


def build_verification_recommendation_route_response(
    context: RuntimeContextDep,
    *,
    paths: list[str],
) -> RepositoryIntelligenceVerificationRecommendationResponse:
    try:
        report = recommend_eval_change_impact(
            context.infrastructure.artifacts_root,
            touched_paths=paths,
        )
    except ValueError as exc:
        return build_verification_recommendation_response(
            status="unavailable",
            paths=paths,
            detail=str(exc),
            next_actions=[
                "inspect repository intelligence with `glassbox repo status --cwd .`",
                "run `glassbox eval audit --cwd .` after eval metadata exists",
            ],
        )
    return build_verification_recommendation_response(
        status="ok",
        paths=paths,
        report=report,
        next_actions=report.suggested_commands,
    )


def build_memory_candidate_route_response(
    context: RuntimeContextDep,
    *,
    session_id: UUID,
    cursor: int,
    limit: int,
) -> RepositoryIntelligenceMemoryCandidateListPageResponse:
    try:
        rows = WorkspaceMemoryCaptureService(
            cast(WorkspaceMemoryCaptureRepository, context.repositories.sessions)
        ).list_candidates(
            session_id,
            policy=MemoryExtractionPolicy(max_candidates=cursor + limit + 1),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return build_memory_candidate_list_page_response(
        session_id=str(session_id),
        cursor=cursor,
        limit=limit,
        candidates=rows,
    )
