"""Repository intelligence v2 API routes."""

from pathlib import Path
from typing import Annotated
from typing import cast
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
from glassbox.runtime.repository_index import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.repository_intelligence_freshness import (
    repository_index_freshness_cues,
)
from glassbox.runtime.repository_intelligence_freshness import (
    workspace_topology_freshness_cues,
)
from glassbox.runtime.repository_intelligence_queries import (
    inspect_repository_intelligence_path,
)
from glassbox.runtime.repository_intelligence_queries import (
    search_repository_intelligence_entries,
)
from glassbox.runtime.repository_intelligence_queries import (
    workspace_relative_repository_path,
)
from glassbox.runtime.workspace_memory_capture import MemoryExtractionPolicy
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureRepository
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureService
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import load_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path
from glassbox.web.app import RuntimeContextDep
from glassbox.web.memory_api import build_workspace_memory_candidate_responses
from glassbox.web.repository_index_api import RepositoryIndexStatusResponse
from glassbox.web.repository_index_api import WorkspaceTopologyStatusResponse
from glassbox.web.repository_index_api import build_repository_index_status_response
from glassbox.web.repository_index_api import build_workspace_topology_status_response
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
from glassbox.web.repository_intelligence_api import build_command_recipe_responses
from glassbox.web.repository_intelligence_api import build_entry_search_page_response
from glassbox.web.repository_intelligence_api import build_ownership_hint_responses
from glassbox.web.repository_intelligence_api import build_path_inspection_response
from glassbox.web.repository_intelligence_api import build_release_surface_responses
from glassbox.web.repository_intelligence_api import (
    build_repository_intelligence_overview_response,
)
from glassbox.web.repository_intelligence_api import build_subsystem_responses
from glassbox.web.session_api import PageInfoResponse

router = APIRouter(prefix="/repo/intelligence", tags=["repo"])

PageCursorParam = Annotated[int, Query(ge=0)]
PageLimitParam = Annotated[int, Query(ge=1, le=200)]


@router.get("", response_model=RepositoryIntelligenceOverviewResponse)
def get_repository_intelligence_overview(
    context: RuntimeContextDep,
) -> RepositoryIntelligenceOverviewResponse:
    """Return repository intelligence map data for dashboard inspection."""

    workspace_root = context.infrastructure.artifacts_root
    snapshot = _load_index_or_404(workspace_root)
    return build_repository_intelligence_overview_response(
        index=build_repository_index_status_response(
            snapshot,
            path=str(repository_index_path(workspace_root)),
        ),
        topology=_load_topology_status(workspace_root),
        source_manifests=snapshot.source_manifests,
        source_roots=snapshot.source_roots,
        test_roots=snapshot.test_roots,
        doc_roots=snapshot.doc_roots,
        generated_paths=snapshot.generated_paths,
        policy_sensitive_paths=snapshot.policy_sensitive_paths,
        package_boundaries=snapshot.package_boundaries,
        subsystems=snapshot.subsystems,
        release_surfaces=snapshot.release_sensitive_surfaces,
        memory_references=snapshot.memory_references,
        limitations=snapshot.limitations,
    )


@router.get("/freshness", response_model=RepositoryIntelligenceFreshnessResponse)
def get_repository_intelligence_freshness(
    context: RuntimeContextDep,
) -> RepositoryIntelligenceFreshnessResponse:
    """Return shared freshness, drift, and rebuild guidance."""

    workspace_root = context.infrastructure.artifacts_root
    index_path = repository_index_path(workspace_root)
    try:
        snapshot = load_repository_index(workspace_root)
        index = build_repository_index_status_response(snapshot, path=str(index_path))
    except RepositoryIndexNotFoundError:
        snapshot = None
        index = RepositoryIndexStatusResponse(
            status="missing",
            path=str(index_path),
            entry_count=0,
            detail="repository index has not been built",
            freshness_cues=repository_index_freshness_cues(workspace_root, None),
        )
    topology = _load_topology_status(workspace_root)
    cues = list(index.freshness_cues)
    if topology is not None:
        cues.extend(topology.freshness_cues)
    next_actions = [
        f"glassbox repo refresh --cwd {workspace_root.resolve()}",
    ]
    if snapshot is None or index.status != "fresh":
        next_actions.insert(
            0, f"glassbox repo index build --cwd {workspace_root.resolve()}"
        )
    if topology is None or topology.freshness != "fresh":
        next_actions.append(
            f"glassbox repo topology build --cwd {workspace_root.resolve()}"
        )
    return RepositoryIntelligenceFreshnessResponse(
        index=index,
        topology=topology,
        cues=cues,
        next_actions=list(dict.fromkeys(next_actions)),
    )


@router.get(
    "/paths/{path:path}", response_model=RepositoryIntelligencePathInspectionResponse
)
def inspect_repository_intelligence_path_route(
    path: str,
    context: RuntimeContextDep,
) -> RepositoryIntelligencePathInspectionResponse:
    """Return packages, subsystems, recipes, owners, and release hints for a path."""

    workspace_root = context.infrastructure.artifacts_root
    snapshot = _load_index_or_404(workspace_root)
    try:
        relative_path = workspace_relative_repository_path(workspace_root, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_path_inspection_response(
        inspect_repository_intelligence_path(snapshot, relative_path)
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

    snapshot = _load_index_or_404(context.infrastructure.artifacts_root)
    recipes = snapshot.command_recipes
    if query is not None and query.strip():
        needle = query.strip().lower()
        recipes = [
            recipe
            for recipe in recipes
            if needle
            in " ".join(
                [
                    recipe.recipe_id,
                    recipe.name,
                    recipe.command,
                    recipe.purpose.value,
                    recipe.review_relevance.value,
                    recipe.risk.value,
                    recipe.toolchain or "",
                    " ".join(path.as_posix() for path in recipe.scope_paths),
                ]
            ).lower()
        ]
    items = recipes[cursor : cursor + limit]
    next_cursor = cursor + len(items) if len(recipes) > cursor + limit else None
    return RepositoryIntelligenceCommandRecipeListPageResponse(
        page=PageInfoResponse(
            cursor=cursor,
            limit=limit,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            returned_count=len(items),
        ),
        items=build_command_recipe_responses(items),
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

    snapshot = _load_index_or_404(context.infrastructure.artifacts_root)
    recipe = next(
        (
            candidate
            for candidate in snapshot.command_recipes
            if candidate.recipe_id == recipe_id
        ),
        None,
    )
    if recipe is None:
        raise HTTPException(
            status_code=404, detail=f"unknown command recipe: {recipe_id}"
        )
    return RepositoryIntelligenceCommandRecipeDetailResponse(
        recipe=build_command_recipe_responses([recipe])[0],
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

    snapshot = _load_index_or_404(context.infrastructure.artifacts_root)
    subsystems = snapshot.subsystems
    if query is not None and query.strip():
        needle = query.strip().lower()
        subsystems = [
            subsystem
            for subsystem in subsystems
            if needle
            in " ".join(
                [
                    subsystem.subsystem_id,
                    subsystem.name,
                    " ".join(subsystem.tags),
                    " ".join(path.as_posix() for path in subsystem.scope_paths),
                ]
            ).lower()
        ]
    items = subsystems[cursor : cursor + limit]
    next_cursor = cursor + len(items) if len(subsystems) > cursor + limit else None
    return RepositoryIntelligenceSubsystemListPageResponse(
        page=PageInfoResponse(
            cursor=cursor,
            limit=limit,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            returned_count=len(items),
        ),
        items=build_subsystem_responses(items),
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

    snapshot = _load_index_or_404(context.infrastructure.artifacts_root)
    subsystem = next(
        (
            candidate
            for candidate in snapshot.subsystems
            if candidate.subsystem_id == subsystem_id
        ),
        None,
    )
    if subsystem is None:
        raise HTTPException(
            status_code=404, detail=f"unknown subsystem: {subsystem_id}"
        )
    owner_ids = set(subsystem.owner_hint_ids)
    release_ids = set(subsystem.release_surface_ids)
    command_ids = {
        recipe_id
        for surface in snapshot.release_sensitive_surfaces
        if surface.surface_id in release_ids
        for recipe_id in surface.command_recipe_ids
    }
    return RepositoryIntelligenceSubsystemDetailResponse(
        subsystem=build_subsystem_responses([subsystem])[0],
        ownership_hints=build_ownership_hint_responses(
            [hint for hint in snapshot.ownership_hints if hint.hint_id in owner_ids]
        ),
        release_surfaces=build_release_surface_responses(
            [
                surface
                for surface in snapshot.release_sensitive_surfaces
                if surface.surface_id in release_ids
            ]
        ),
        command_recipes=build_command_recipe_responses(
            [
                recipe
                for recipe in snapshot.command_recipes
                if recipe.recipe_id in command_ids
                or any(scope in subsystem.scope_paths for scope in recipe.scope_paths)
            ]
        ),
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

    try:
        report = recommend_eval_change_impact(
            context.infrastructure.artifacts_root,
            touched_paths=paths,
        )
    except ValueError as exc:
        return RepositoryIntelligenceVerificationRecommendationResponse(
            status="unavailable",
            paths=paths,
            detail=str(exc),
            next_actions=[
                "inspect repository intelligence with `glassbox repo status --cwd .`",
                "run `glassbox eval audit --cwd .` after eval metadata exists",
            ],
        )
    return RepositoryIntelligenceVerificationRecommendationResponse(
        status="ok",
        paths=paths,
        report=report,
        next_actions=report.suggested_commands,
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

    try:
        rows = WorkspaceMemoryCaptureService(
            cast(WorkspaceMemoryCaptureRepository, context.repositories.sessions)
        ).list_candidates(
            session_id,
            policy=MemoryExtractionPolicy(max_candidates=cursor + limit + 1),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    page_rows = rows[cursor : cursor + limit + 1]
    items = page_rows[:limit]
    next_cursor = cursor + len(items) if len(page_rows) > limit else None
    return RepositoryIntelligenceMemoryCandidateListPageResponse(
        session_id=str(session_id),
        page=PageInfoResponse(
            cursor=cursor,
            limit=limit,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            returned_count=len(items),
        ),
        items=build_workspace_memory_candidate_responses(items),
    )


@router.get("/search", response_model=RepositoryIntelligenceSearchPageResponse)
def search_repository_intelligence(
    context: RuntimeContextDep,
    query: str = Query(min_length=1),
    cursor: PageCursorParam = 0,
    limit: PageLimitParam = 50,
) -> RepositoryIntelligenceSearchPageResponse:
    """Search repository intelligence entries with cursor pagination."""

    snapshot = _load_index_or_404(context.infrastructure.artifacts_root)
    return build_entry_search_page_response(
        query=query,
        cursor=cursor,
        limit=limit,
        entries=search_repository_intelligence_entries(snapshot, query),
    )


def _load_index_or_404(workspace_root: Path) -> RepositoryIndexSnapshot:
    try:
        return load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _load_topology_status(
    workspace_root: Path,
) -> WorkspaceTopologyStatusResponse | None:
    try:
        topology = load_workspace_topology(workspace_root)
    except WorkspaceTopologyNotFoundError:
        return WorkspaceTopologyStatusResponse(
            freshness="missing",
            path=str(workspace_topology_path(workspace_root)),
            component_count=0,
            dependency_count=0,
            recommendation_posture="unavailable",
            limitations=[],
            freshness_cues=workspace_topology_freshness_cues(workspace_root, None),
            detail="workspace topology has not been built",
            next_actions=[
                f"glassbox repo topology build --cwd {workspace_root.resolve()}",
            ],
        )
    return build_workspace_topology_status_response(
        topology,
        path=str(workspace_topology_path(workspace_root)),
        next_actions=(
            [f"glassbox repo topology build --cwd {workspace_root.resolve()}"]
            if topology.freshness != "fresh"
            else []
        ),
    )
