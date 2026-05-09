"""Repository-intelligence enrichment for eval recommendations."""

from dataclasses import dataclass
from pathlib import Path

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceCommandRisk
from glassbox.core.types import RepositoryIntelligenceReleaseSurfaceKind
from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_matching_common import RecommendationReasonMap
from glassbox.runtime.eval_recommendation_matching_common import add_reason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationSourceMetadata
from glassbox.runtime.eval_recommendation_models import (
    EvalVerificationRecipeRecommendation,
)
from glassbox.runtime.eval_recommendation_models import PathVerificationFreshness
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.repository_index_persistence import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index_persistence import load_repository_index


@dataclass(frozen=True)
class EvalRepositoryIntelligenceEnrichment:
    """Repository-intelligence additions for one eval recommendation report."""

    recipe_recommendations: list[EvalVerificationRecipeRecommendation]
    warnings: list[str]
    matched_paths: set[str]
    case_source_metadata: dict[str, list[EvalRecommendationSourceMetadata]]
    profile_source_metadata: dict[str, list[EvalRecommendationSourceMetadata]]
    case_safe_next_commands: dict[str, list[str]]
    profile_safe_next_commands: dict[str, list[str]]


def apply_repository_intelligence_recommendations(
    *,
    workspace_root: Path,
    normalized_paths: list[str],
    cases: list[EvalCase],
    profiles: list[EvalProfileDefinition],
    case_reasons: RecommendationReasonMap,
    profile_reasons: RecommendationReasonMap,
) -> EvalRepositoryIntelligenceEnrichment:
    """Use repository intelligence as advisory eval recommendation context."""

    try:
        snapshot = load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError:
        return _empty_enrichment()
    except ValueError as exc:
        return _empty_enrichment(
            warnings=[f"Repository intelligence snapshot could not be read: {exc}"]
        )

    if snapshot.status == RepositoryIndexFreshness.FAILED:
        reason = snapshot.failure_reason or "unknown failure"
        return _empty_enrichment(
            warnings=[f"Repository intelligence snapshot is failed; reason: {reason}."]
        )

    freshness = _freshness(snapshot)
    warnings: list[str] = []
    if freshness == "stale":
        warnings.append(
            "Repository intelligence snapshot is stale; eval recommendation "
            "source metadata and command recipes are degraded until "
            "`glassbox repo index build --cwd .` is rerun."
        )

    matched_subsystems = _matched_subsystems(snapshot, normalized_paths)
    matched_owners = _matched_owners(snapshot, normalized_paths)
    matched_surfaces = _matched_release_surfaces(snapshot, normalized_paths)
    matched_recipes = _matched_command_recipes(snapshot, normalized_paths)
    matched_paths = set()

    profile_metadata: dict[str, list[EvalRecommendationSourceMetadata]] = {}
    for profile in profiles:
        for surface, paths in matched_surfaces:
            stage = _surface_stage(surface.kind)
            if stage is None or profile.verification_stage != stage:
                continue
            if profile.track == "live-provider-canary":
                continue
            for path in paths:
                matched_paths.add(path)
                add_reason(
                    profile_reasons,
                    profile.profile_id,
                    EvalRecommendationReason(
                        confidence="stage-derived",
                        group="repository-intelligence",
                        summary=(
                            f"repository intelligence release surface "
                            f"{surface.surface_id} matched {path} and maps to "
                            f"profile {profile.profile_id}"
                        ),
                        matched_path=path,
                        verification_stage=profile.verification_stage,
                        source="repository-intelligence-snapshot",
                        source_id=surface.surface_id,
                        freshness=freshness,
                    ),
                )
            _append_metadata(
                profile_metadata,
                profile.profile_id,
                _surface_metadata(surface, paths, freshness=freshness),
            )

    case_metadata = _case_metadata(
        cases=cases,
        case_reasons=case_reasons,
        matched_subsystems=matched_subsystems,
        matched_owners=matched_owners,
        matched_surfaces=matched_surfaces,
        freshness=freshness,
    )
    recipe_recommendations = _recipe_recommendations(
        recipes=matched_recipes,
        freshness=freshness,
    )
    return EvalRepositoryIntelligenceEnrichment(
        recipe_recommendations=recipe_recommendations,
        warnings=dedupe_strings(warnings),
        matched_paths=matched_paths,
        case_source_metadata=case_metadata,
        profile_source_metadata=profile_metadata,
        case_safe_next_commands={},
        profile_safe_next_commands={},
    )


def _case_metadata(
    *,
    cases: list[EvalCase],
    case_reasons: RecommendationReasonMap,
    matched_subsystems: list[tuple[RepositoryIntelligenceSubsystem, list[str]]],
    matched_owners: list[tuple[RepositoryIntelligenceOwnershipHint, list[str]]],
    matched_surfaces: list[tuple[RepositoryIntelligenceReleaseSurface, list[str]]],
    freshness: PathVerificationFreshness,
) -> dict[str, list[EvalRecommendationSourceMetadata]]:
    metadata: dict[str, list[EvalRecommendationSourceMetadata]] = {}
    cases_by_id = {case.case_id: case for case in cases}
    for case_id in case_reasons:
        case = cases_by_id.get(case_id)
        if case is None:
            continue
        for subsystem, paths in matched_subsystems:
            if _case_mentions_subsystem(case, subsystem):
                _append_metadata(
                    metadata,
                    case_id,
                    _subsystem_metadata(subsystem, paths, freshness=freshness),
                )
        for owner, paths in matched_owners:
            _append_metadata(
                metadata,
                case_id,
                _owner_metadata(owner, paths, freshness=freshness),
            )
        for surface, paths in matched_surfaces:
            if _case_mentions_surface(case, surface):
                _append_metadata(
                    metadata,
                    case_id,
                    _surface_metadata(surface, paths, freshness=freshness),
                )
    return metadata


def _recipe_recommendations(
    *,
    recipes: list[tuple[RepositoryIntelligenceCommandRecipe, list[str]]],
    freshness: PathVerificationFreshness,
) -> list[EvalVerificationRecipeRecommendation]:
    recommendations: list[EvalVerificationRecipeRecommendation] = []
    for recipe, matched_paths in recipes[:12]:
        confidence = "degraded" if freshness == "stale" else "direct"
        limitations = list(recipe.limitations)
        if freshness == "stale":
            limitations.append(
                "Repository intelligence changed after this snapshot was built."
            )
        recommendations.append(
            EvalVerificationRecipeRecommendation(
                recipe_id=f"repo-intelligence-{_slug(recipe.recipe_id)}",
                title=recipe.name,
                confidence=confidence,
                source="repository-intelligence",
                freshness=freshness,
                matched_paths=matched_paths,
                commands=[recipe.command],
                notes=(
                    f"Derived from repository intelligence command recipe "
                    f"`{recipe.recipe_id}`."
                ),
                limitations=dedupe_strings(limitations),
                safe_next_commands=[recipe.command],
            )
        )
    recommendations.sort(key=lambda item: item.recipe_id)
    return recommendations


def _matched_subsystems(
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


def _matched_owners(
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


def _matched_release_surfaces(
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


def _matched_command_recipes(
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


def _safe_recipe_for_eval_recommendation(
    recipe: RepositoryIntelligenceCommandRecipe,
) -> bool:
    return recipe.risk in {
        RepositoryIntelligenceCommandRisk.READ_ONLY,
        RepositoryIntelligenceCommandRisk.RELEASE,
        RepositoryIntelligenceCommandRisk.UNKNOWN,
    }


def _surface_stage(kind: RepositoryIntelligenceReleaseSurfaceKind) -> str | None:
    if kind == RepositoryIntelligenceReleaseSurfaceKind.COMMIT_TIME:
        return "commit-time"
    if kind == RepositoryIntelligenceReleaseSurfaceKind.PUSH_TIME:
        return "push-time"
    if kind == RepositoryIntelligenceReleaseSurfaceKind.RELEASE_CANDIDATE:
        return "release-candidate"
    if kind == RepositoryIntelligenceReleaseSurfaceKind.ADVISORY:
        return "advisory"
    return None


def _case_mentions_subsystem(
    case: EvalCase,
    subsystem: RepositoryIntelligenceSubsystem,
) -> bool:
    tokens = {
        subsystem.subsystem_id.removeprefix("subsystem:"),
        *(tag.lower() for tag in subsystem.tags),
    }
    owner = (case.release_contract.owner or "").lower()
    capabilities = [
        capability.lower() for capability in case.release_contract.capabilities
    ]
    return any(
        token and (token in owner or any(token in cap for cap in capabilities))
        for token in tokens
    )


def _case_mentions_surface(
    case: EvalCase,
    surface: RepositoryIntelligenceReleaseSurface,
) -> bool:
    stage = _surface_stage(surface.kind)
    return stage is not None and stage in case.release_contract.verification_stages


def _subsystem_metadata(
    subsystem: RepositoryIntelligenceSubsystem,
    matched_paths: list[str],
    *,
    freshness: PathVerificationFreshness,
) -> EvalRecommendationSourceMetadata:
    return EvalRecommendationSourceMetadata(
        source="repository-intelligence-snapshot",
        source_id=subsystem.subsystem_id,
        source_path=_provenance_path(subsystem.provenance),
        freshness=freshness,
        matched_paths=dedupe_strings(matched_paths),
        explanation=(
            f"Repository intelligence matched subsystem `{subsystem.name}` "
            "for the changed paths."
        ),
        limitations=list(subsystem.limitations),
    )


def _owner_metadata(
    owner: RepositoryIntelligenceOwnershipHint,
    matched_paths: list[str],
    *,
    freshness: PathVerificationFreshness,
) -> EvalRecommendationSourceMetadata:
    return EvalRecommendationSourceMetadata(
        source="repository-intelligence-snapshot",
        source_id=owner.hint_id,
        source_path=_provenance_path(owner.provenance),
        freshness=freshness,
        matched_paths=dedupe_strings(matched_paths),
        explanation=(
            f"Repository intelligence matched owner hint `{owner.owner_label}`."
        ),
        limitations=list(owner.limitations),
    )


def _surface_metadata(
    surface: RepositoryIntelligenceReleaseSurface,
    matched_paths: list[str],
    *,
    freshness: PathVerificationFreshness,
) -> EvalRecommendationSourceMetadata:
    return EvalRecommendationSourceMetadata(
        source="repository-intelligence-snapshot",
        source_id=surface.surface_id,
        source_path=_provenance_path(surface.provenance),
        freshness=freshness,
        matched_paths=dedupe_strings(matched_paths),
        explanation=(
            f"Repository intelligence matched release surface `{surface.name}`."
        ),
        limitations=list(surface.limitations),
    )


def _append_metadata(
    mapping: dict[str, list[EvalRecommendationSourceMetadata]],
    key: str,
    metadata: EvalRecommendationSourceMetadata,
) -> None:
    rows = mapping.setdefault(key, [])
    dedupe_key = (
        metadata.source,
        metadata.source_id,
        tuple(metadata.matched_paths),
        metadata.freshness,
    )
    if dedupe_key not in {
        (row.source, row.source_id, tuple(row.matched_paths), row.freshness)
        for row in rows
    }:
        rows.append(metadata)


def _provenance_path(provenance: object) -> str | None:
    if not isinstance(provenance, list) or not provenance:
        return None
    first = provenance[0]
    source_type = getattr(first, "source_type", None)
    path = getattr(first, "path", None)
    if path is None:
        return None
    if source_type == RepositoryIndexSourceType.FILE_SYSTEM:
        return Path(path).as_posix()
    return Path(path).as_posix()


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


def _freshness(snapshot: RepositoryIndexSnapshot) -> PathVerificationFreshness:
    if snapshot.status == RepositoryIndexFreshness.FRESH:
        return "fresh"
    if snapshot.status == RepositoryIndexFreshness.STALE:
        return "stale"
    return "degraded"


def _slug(value: str) -> str:
    return (
        value.replace(":", "-")
        .replace("/", "-")
        .replace("\\", "-")
        .replace("_", "-")
        .strip("-")
        or "recipe"
    )


def _empty_enrichment(
    *,
    warnings: list[str] | None = None,
) -> EvalRepositoryIntelligenceEnrichment:
    return EvalRepositoryIntelligenceEnrichment(
        recipe_recommendations=[],
        warnings=warnings or [],
        matched_paths=set(),
        case_source_metadata={},
        profile_source_metadata={},
        case_safe_next_commands={},
        profile_safe_next_commands={},
    )


__all__ = [
    "EvalRepositoryIntelligenceEnrichment",
    "apply_repository_intelligence_recommendations",
]
