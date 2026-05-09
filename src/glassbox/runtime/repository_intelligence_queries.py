"""Reusable query helpers for repository intelligence surfaces."""

from dataclasses import dataclass
from pathlib import Path

from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.runtime.repository_index_search import entry_search_text


@dataclass(frozen=True, slots=True)
class RepositoryIntelligencePathInspection:
    """Repository-intelligence matches for one workspace-relative path."""

    path: Path
    snapshot_status: str
    packages: list[RepositoryIntelligencePackageBoundary]
    path_hints: list[RepositoryIntelligencePathHint]
    subsystems: list[RepositoryIntelligenceSubsystem]
    command_recipes: list[RepositoryIntelligenceCommandRecipe]
    ownership_hints: list[RepositoryIntelligenceOwnershipHint]
    release_surfaces: list[RepositoryIntelligenceReleaseSurface]
    next_actions: list[str]


def workspace_relative_repository_path(workspace_root: Path, value: str) -> Path:
    """Normalize an operator path into a safe workspace-relative path."""

    raw_path = Path(value)
    if raw_path.is_absolute():
        return raw_path.resolve().relative_to(workspace_root.resolve())
    if ".." in raw_path.parts:
        raise ValueError("repository path must stay inside the workspace")
    return raw_path


def inspect_repository_intelligence_path(
    snapshot: RepositoryIndexSnapshot,
    path: Path,
) -> RepositoryIntelligencePathInspection:
    """Return repository-intelligence evidence relevant to one path."""

    packages = [
        package
        for package in snapshot.package_boundaries
        if _scope_contains(package.root, path)
        or any(_scope_contains(scope, path) for scope in package.source_roots)
        or any(_scope_contains(scope, path) for scope in package.test_roots)
        or any(_scope_contains(scope, path) for scope in package.doc_roots)
    ]
    path_hints = [
        hint for hint in _all_path_hints(snapshot) if _scope_contains(hint.path, path)
    ]
    subsystems = [
        subsystem
        for subsystem in snapshot.subsystems
        if any(_scope_contains(scope, path) for scope in subsystem.scope_paths)
    ]
    recipes = [
        recipe
        for recipe in snapshot.command_recipes
        if not recipe.scope_paths
        or any(_scope_contains(scope, path) for scope in recipe.scope_paths)
    ]
    owner_scope_ids = {
        owner.hint_id
        for owner in snapshot.ownership_hints
        if any(_scope_contains(scope, path) for scope in owner.scope_paths)
    }
    owner_scope_ids.update(
        owner_id for subsystem in subsystems for owner_id in subsystem.owner_hint_ids
    )
    owners = [
        owner for owner in snapshot.ownership_hints if owner.hint_id in owner_scope_ids
    ]
    release_surface_ids = {
        surface_id
        for subsystem in subsystems
        for surface_id in subsystem.release_surface_ids
    }
    release_surfaces = [
        surface
        for surface in snapshot.release_sensitive_surfaces
        if surface.surface_id in release_surface_ids
        or any(_scope_contains(scope, path) for scope in surface.scope_paths)
    ]
    return RepositoryIntelligencePathInspection(
        path=path,
        snapshot_status=snapshot.status.value,
        packages=packages,
        path_hints=path_hints,
        subsystems=subsystems,
        command_recipes=recipes,
        ownership_hints=owners,
        release_surfaces=release_surfaces,
        next_actions=[
            f"glassbox repo recommend {path.as_posix()}",
            f"glassbox eval recommend {path.as_posix()}",
        ],
    )


def search_repository_intelligence_entries(
    snapshot: RepositoryIndexSnapshot,
    query: str,
) -> list[RepositoryIndexEntry]:
    """Search already-loaded repository entries without re-reading artifacts."""

    normalized_query = query.strip().lower()
    if not normalized_query:
        return []
    return [
        entry
        for entry in snapshot.entries
        if normalized_query in entry_search_text(entry)
    ]


def _all_path_hints(
    snapshot: RepositoryIndexSnapshot,
) -> list[RepositoryIntelligencePathHint]:
    return [
        *snapshot.source_roots,
        *snapshot.test_roots,
        *snapshot.doc_roots,
        *snapshot.generated_paths,
        *snapshot.policy_sensitive_paths,
    ]


def _scope_contains(scope: Path, path: Path) -> bool:
    scope_value = Path(".") if scope.as_posix() in {"", "."} else scope
    path_value = Path(".") if path.as_posix() in {"", "."} else path
    return path_value == scope_value or path_value.is_relative_to(scope_value)


__all__ = [
    "RepositoryIntelligencePathInspection",
    "inspect_repository_intelligence_path",
    "search_repository_intelligence_entries",
    "workspace_relative_repository_path",
]
