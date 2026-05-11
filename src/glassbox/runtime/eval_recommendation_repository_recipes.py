"""Repository-intelligence recipe recommendation helpers."""

from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_models import (
    EvalVerificationRecipeRecommendation,
)
from glassbox.runtime.eval_recommendation_models import PathVerificationFreshness


def repository_intelligence_recipe_recommendations(
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


def _slug(value: str) -> str:
    return (
        value.replace(":", "-")
        .replace("/", "-")
        .replace("\\", "-")
        .replace("_", "-")
        .strip("-")
        or "recipe"
    )


__all__ = ["repository_intelligence_recipe_recommendations"]
