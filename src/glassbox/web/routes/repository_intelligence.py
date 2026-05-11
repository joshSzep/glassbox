"""Repository intelligence v2 API route declarations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Query

from glassbox.web.app import RuntimeContextDep
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceCommandRecipeDetailResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceCommandRecipeListPageResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceFreshnessResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceMemoryCandidateListPageResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceOverviewResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligencePathInspectionResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceSearchPageResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceSubsystemDetailResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceSubsystemListPageResponse,
)
from glassbox.web.repository_intelligence_api import (
    RepositoryIntelligenceVerificationRecommendationResponse,
)
from glassbox.web.routes.repository_intelligence_queries import (
    build_command_recipe_detail_route_response,
)
from glassbox.web.routes.repository_intelligence_queries import (
    build_command_recipe_list_route_response,
)
from glassbox.web.routes.repository_intelligence_queries import (
    build_path_inspection_route_response,
)
from glassbox.web.routes.repository_intelligence_queries import (
    build_repository_intelligence_freshness_route_response,
)
from glassbox.web.routes.repository_intelligence_queries import (
    build_repository_intelligence_overview_route_response,
)
from glassbox.web.routes.repository_intelligence_queries import (
    build_search_route_response,
)
from glassbox.web.routes.repository_intelligence_queries import (
    build_subsystem_detail_route_response,
)
from glassbox.web.routes.repository_intelligence_queries import (
    build_subsystem_list_route_response,
)
from glassbox.web.routes.repository_intelligence_services import (
    build_memory_candidate_route_response,
)
from glassbox.web.routes.repository_intelligence_services import (
    build_verification_recommendation_route_response,
)

router = APIRouter(prefix="/repo/intelligence", tags=["repo"])

PageCursorParam = Annotated[int, Query(ge=0)]
PageLimitParam = Annotated[int, Query(ge=1, le=200)]


@router.get("", response_model=RepositoryIntelligenceOverviewResponse)
def get_repository_intelligence_overview(
    context: RuntimeContextDep,
) -> RepositoryIntelligenceOverviewResponse:
    """Return repository intelligence map data for dashboard inspection."""

    return build_repository_intelligence_overview_route_response(
        context.infrastructure.artifacts_root
    )


@router.get("/freshness", response_model=RepositoryIntelligenceFreshnessResponse)
def get_repository_intelligence_freshness(
    context: RuntimeContextDep,
) -> RepositoryIntelligenceFreshnessResponse:
    """Return shared freshness, drift, and rebuild guidance."""

    return build_repository_intelligence_freshness_route_response(
        context.infrastructure.artifacts_root
    )


@router.get(
    "/paths/{path:path}", response_model=RepositoryIntelligencePathInspectionResponse
)
def inspect_repository_intelligence_path_route(
    path: str,
    context: RuntimeContextDep,
) -> RepositoryIntelligencePathInspectionResponse:
    """Return packages, subsystems, recipes, owners, and release hints for a path."""

    return build_path_inspection_route_response(
        context.infrastructure.artifacts_root,
        path,
    )


@router.get(
    "/command-recipes",
    response_model=RepositoryIntelligenceCommandRecipeListPageResponse,
)
def list_repository_intelligence_command_recipes(
    context: RuntimeContextDep,
    query: str | None = None,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> RepositoryIntelligenceCommandRecipeListPageResponse:
    """Return advisory command recipes with provenance and risk labels."""

    return build_command_recipe_list_route_response(
        context.infrastructure.artifacts_root,
        query=query,
        cursor=cursor,
        limit=limit,
    )


@router.get(
    "/command-recipes/{recipe_id}",
    response_model=RepositoryIntelligenceCommandRecipeDetailResponse,
)
def get_repository_intelligence_command_recipe(
    recipe_id: str,
    context: RuntimeContextDep,
) -> RepositoryIntelligenceCommandRecipeDetailResponse:
    """Return one advisory command recipe."""

    return build_command_recipe_detail_route_response(
        context.infrastructure.artifacts_root,
        recipe_id,
    )


@router.get(
    "/subsystems", response_model=RepositoryIntelligenceSubsystemListPageResponse
)
def list_repository_intelligence_subsystems(
    context: RuntimeContextDep,
    query: str | None = None,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> RepositoryIntelligenceSubsystemListPageResponse:
    """Return repository subsystem hints."""

    return build_subsystem_list_route_response(
        context.infrastructure.artifacts_root,
        query=query,
        cursor=cursor,
        limit=limit,
    )


@router.get(
    "/subsystems/{subsystem_id}",
    response_model=RepositoryIntelligenceSubsystemDetailResponse,
)
def get_repository_intelligence_subsystem(
    subsystem_id: str,
    context: RuntimeContextDep,
) -> RepositoryIntelligenceSubsystemDetailResponse:
    """Return one subsystem with linked owner, release, and command hints."""

    return build_subsystem_detail_route_response(
        context.infrastructure.artifacts_root,
        subsystem_id,
    )


@router.get(
    "/verification",
    response_model=RepositoryIntelligenceVerificationRecommendationResponse,
)
def recommend_repository_intelligence_verification(
    context: RuntimeContextDep,
    paths: Annotated[list[str], Query(min_length=1)],
) -> RepositoryIntelligenceVerificationRecommendationResponse:
    """Return path-to-verification recommendations for changed paths."""

    return build_verification_recommendation_route_response(
        context,
        paths=paths,
    )


@router.get(
    "/memory-candidates",
    response_model=RepositoryIntelligenceMemoryCandidateListPageResponse,
)
async def list_repository_intelligence_memory_candidates(
    context: RuntimeContextDep,
    session_id: UUID,
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 100,
) -> RepositoryIntelligenceMemoryCandidateListPageResponse:
    """Return review-only memory candidates relevant to repository intelligence."""

    return build_memory_candidate_route_response(
        context,
        session_id=session_id,
        cursor=cursor,
        limit=limit,
    )


@router.get("/search", response_model=RepositoryIntelligenceSearchPageResponse)
def search_repository_intelligence(
    context: RuntimeContextDep,
    query: str = Query(min_length=1),
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 50,
) -> RepositoryIntelligenceSearchPageResponse:
    """Search repository intelligence entries with cursor pagination."""

    return build_search_route_response(
        context.infrastructure.artifacts_root,
        query=query,
        cursor=cursor,
        limit=limit,
    )
