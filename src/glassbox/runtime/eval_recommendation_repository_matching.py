"""Repository-intelligence matching helpers for eval recommendations."""

from pathlib import Path

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.core.types import RepositoryIntelligenceCommandRisk
from glassbox.core.types import RepositoryIntelligenceReleaseSurfaceKind
from glassbox.runtime.eval_recommendation_common import dedupe_strings


def matched_subsystems(
    snapshot: RepositoryIndexSnapshot,
    normalized_paths: list[str],
) -> list[tuple[RepositoryIntelligenceSubsystem, list[str]]]:
    return [
        (subsystem, paths)
        for subsystem in snapshot.subsystems
        if (
            paths := [
                path
                for path in normalized_paths
                if _path_in_roots(Path(path), subsystem.scope_paths)
            ]
        )
    ]


def matched_owners(
    snapshot: RepositoryIndexSnapshot,
    normalized_paths: list[str],
) -> list[tuple[RepositoryIntelligenceOwnershipHint, list[str]]]:
    return [
        (owner, paths)
        for owner in snapshot.ownership_hints
        if (
            paths := [
                path
                for path in normalized_paths
                if _path_in_roots(Path(path), owner.scope_paths)
            ]
        )
    ]


def matched_release_surfaces(
    snapshot: RepositoryIndexSnapshot,
    normalized_paths: list[str],
) -> list[tuple[RepositoryIntelligenceReleaseSurface, list[str]]]:
    return [
        (surface, paths)
        for surface in snapshot.release_sensitive_surfaces
        if (
            paths := [
                path
                for path in normalized_paths
                if _path_in_roots(Path(path), surface.scope_paths)
            ]
        )
    ]


def matched_command_recipes(
    snapshot: RepositoryIndexSnapshot,
    normalized_paths: list[str],
) -> list[tuple[RepositoryIntelligenceCommandRecipe, list[str]]]:
    matches: list[tuple[RepositoryIntelligenceCommandRecipe, list[str]]] = []
    for recipe in snapshot.command_recipes:
        if not _safe_recipe_for_eval_recommendation(recipe):
            continue
        matched_paths = [
            path
            for path in normalized_paths
            if _path_in_roots(Path(path), recipe.scope_paths)
        ]
        if matched_paths:
            matches.append((recipe, dedupe_strings(matched_paths)))
    matches.sort(key=lambda item: (item[0].risk.value, item[0].recipe_id))
    return matches


def surface_stage(kind: RepositoryIntelligenceReleaseSurfaceKind) -> str | None:
    if kind == RepositoryIntelligenceReleaseSurfaceKind.COMMIT_TIME:
        return "commit-time"
    if kind == RepositoryIntelligenceReleaseSurfaceKind.PUSH_TIME:
        return "push-time"
    if kind == RepositoryIntelligenceReleaseSurfaceKind.RELEASE_CANDIDATE:
        return "release-candidate"
    if kind == RepositoryIntelligenceReleaseSurfaceKind.ADVISORY:
        return "advisory"
    return None


def _safe_recipe_for_eval_recommendation(
    recipe: RepositoryIntelligenceCommandRecipe,
) -> bool:
    return recipe.risk in {
        RepositoryIntelligenceCommandRisk.READ_ONLY,
        RepositoryIntelligenceCommandRisk.RELEASE,
        RepositoryIntelligenceCommandRisk.UNKNOWN,
    }


def _path_in_roots(path: Path, roots: list[Path]) -> bool:
    return any(_path_contains(root, path) for root in roots)


def _path_contains(root: Path, path: Path) -> bool:
    if root == Path("."):
        return True
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


__all__ = [
    "matched_command_recipes",
    "matched_owners",
    "matched_release_surfaces",
    "matched_subsystems",
    "surface_stage",
]
