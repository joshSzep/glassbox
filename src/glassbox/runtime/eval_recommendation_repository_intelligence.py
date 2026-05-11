"""Repository-intelligence enrichment for eval recommendations."""

from dataclasses import dataclass
from pathlib import Path

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_matching_common import RecommendationReasonMap
from glassbox.runtime.eval_recommendation_matching_common import add_reason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationSourceMetadata
from glassbox.runtime.eval_recommendation_models import (
    EvalVerificationRecipeRecommendation,
)
from glassbox.runtime.eval_recommendation_models import PathVerificationFreshness
from glassbox.runtime.eval_recommendation_repository_matching import (
    matched_command_recipes,
)
from glassbox.runtime.eval_recommendation_repository_matching import matched_owners
from glassbox.runtime.eval_recommendation_repository_matching import (
    matched_release_surfaces,
)
from glassbox.runtime.eval_recommendation_repository_matching import matched_subsystems
from glassbox.runtime.eval_recommendation_repository_matching import surface_stage
from glassbox.runtime.eval_recommendation_repository_metadata import (
    append_repository_intelligence_metadata,
)
from glassbox.runtime.eval_recommendation_repository_metadata import (
    case_repository_intelligence_metadata,
)
from glassbox.runtime.eval_recommendation_repository_metadata import (
    surface_repository_intelligence_metadata,
)
from glassbox.runtime.eval_recommendation_repository_recipes import (
    repository_intelligence_recipe_recommendations,
)
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

    repository_subsystems = matched_subsystems(snapshot, normalized_paths)
    repository_owners = matched_owners(snapshot, normalized_paths)
    repository_surfaces = matched_release_surfaces(snapshot, normalized_paths)
    repository_recipes = matched_command_recipes(snapshot, normalized_paths)
    matched_paths = set()

    profile_metadata: dict[str, list[EvalRecommendationSourceMetadata]] = {}
    for profile in profiles:
        for surface, paths in repository_surfaces:
            stage = surface_stage(surface.kind)
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
            append_repository_intelligence_metadata(
                profile_metadata,
                profile.profile_id,
                surface_repository_intelligence_metadata(
                    surface,
                    paths,
                    freshness=freshness,
                ),
            )

    case_metadata = case_repository_intelligence_metadata(
        cases=cases,
        case_reasons=case_reasons,
        matched_subsystems=repository_subsystems,
        matched_owners=repository_owners,
        matched_surfaces=repository_surfaces,
        freshness=freshness,
    )
    recipe_recommendations = repository_intelligence_recipe_recommendations(
        recipes=repository_recipes,
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


def _freshness(snapshot: RepositoryIndexSnapshot) -> PathVerificationFreshness:
    if snapshot.status == RepositoryIndexFreshness.FRESH:
        return "fresh"
    if snapshot.status == RepositoryIndexFreshness.STALE:
        return "stale"
    return "degraded"


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
