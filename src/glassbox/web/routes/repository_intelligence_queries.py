"""Route-local query helpers for repository intelligence APIs."""

from collections.abc import Sequence
from pathlib import Path

from fastapi import HTTPException

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.runtime.repository_index import RepositoryIndexLoadError
from glassbox.runtime.repository_index import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index import (
    failed_repository_index_snapshot_from_error,
)
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
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import load_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path
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


def build_repository_intelligence_overview_route_response(
    workspace_root: Path,
) -> RepositoryIntelligenceOverviewResponse:
    snapshot = load_index_or_404(workspace_root)
    return build_repository_intelligence_overview_response(
        index=build_repository_index_status_response(
            snapshot,
            path=str(repository_index_path(workspace_root)),
        ),
        topology=load_topology_status(workspace_root),
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


def build_repository_intelligence_freshness_route_response(
    workspace_root: Path,
) -> RepositoryIntelligenceFreshnessResponse:
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
    except RepositoryIndexLoadError as error:
        snapshot = failed_repository_index_snapshot_from_error(workspace_root, error)
        index = build_repository_index_status_response(
            snapshot,
            path=str(index_path),
            detail=error.detail,
        )
    topology = load_topology_status(workspace_root)
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


def build_path_inspection_route_response(
    workspace_root: Path,
    path: str,
) -> RepositoryIntelligencePathInspectionResponse:
    snapshot = load_index_or_404(workspace_root)
    try:
        relative_path = workspace_relative_repository_path(workspace_root, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_path_inspection_response(
        inspect_repository_intelligence_path(snapshot, relative_path)
    )


def build_command_recipe_list_route_response(
    workspace_root: Path,
    *,
    query: str | None,
    cursor: int,
    limit: int,
) -> RepositoryIntelligenceCommandRecipeListPageResponse:
    snapshot = load_index_or_404(workspace_root)
    recipes = _filter_command_recipes(snapshot.command_recipes, query)
    items, page = _paginate(recipes, cursor=cursor, limit=limit)
    return RepositoryIntelligenceCommandRecipeListPageResponse(
        page=page,
        items=build_command_recipe_responses(items),
    )


def build_command_recipe_detail_route_response(
    workspace_root: Path,
    recipe_id: str,
) -> RepositoryIntelligenceCommandRecipeDetailResponse:
    snapshot = load_index_or_404(workspace_root)
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


def build_subsystem_list_route_response(
    workspace_root: Path,
    *,
    query: str | None,
    cursor: int,
    limit: int,
) -> RepositoryIntelligenceSubsystemListPageResponse:
    snapshot = load_index_or_404(workspace_root)
    subsystems = _filter_subsystems(snapshot.subsystems, query)
    items, page = _paginate(subsystems, cursor=cursor, limit=limit)
    return RepositoryIntelligenceSubsystemListPageResponse(
        page=page,
        items=build_subsystem_responses(items),
    )


def build_subsystem_detail_route_response(
    workspace_root: Path,
    subsystem_id: str,
) -> RepositoryIntelligenceSubsystemDetailResponse:
    snapshot = load_index_or_404(workspace_root)
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


def build_search_route_response(
    workspace_root: Path,
    *,
    query: str,
    cursor: int,
    limit: int,
) -> RepositoryIntelligenceSearchPageResponse:
    snapshot = load_index_or_404(workspace_root)
    return build_entry_search_page_response(
        query=query,
        cursor=cursor,
        limit=limit,
        entries=search_repository_intelligence_entries(snapshot, query),
    )


def load_index_or_404(workspace_root: Path) -> RepositoryIndexSnapshot:
    try:
        return load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RepositoryIndexLoadError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": error.reason,
                "message": error.detail,
                "path": str(error.path),
                "safe_next_actions": error.safe_next_actions,
            },
        ) from error


def load_topology_status(
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


def _filter_command_recipes(
    recipes: Sequence[RepositoryIntelligenceCommandRecipe],
    query: str | None,
) -> list[RepositoryIntelligenceCommandRecipe]:
    if query is None or not query.strip():
        return list(recipes)
    needle = query.strip().lower()
    return [
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


def _filter_subsystems(
    subsystems: Sequence[RepositoryIntelligenceSubsystem],
    query: str | None,
) -> list[RepositoryIntelligenceSubsystem]:
    if query is None or not query.strip():
        return list(subsystems)
    needle = query.strip().lower()
    return [
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


def _paginate[T](
    values: Sequence[T],
    *,
    cursor: int,
    limit: int,
) -> tuple[list[T], PageInfoResponse]:
    items = list(values[cursor : cursor + limit])
    next_cursor = cursor + len(items) if len(values) > cursor + limit else None
    return items, PageInfoResponse(
        cursor=cursor,
        limit=limit,
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
        returned_count=len(items),
    )
