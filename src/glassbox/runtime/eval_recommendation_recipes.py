"""Recipe and release-gate command helpers for eval recommendations."""

from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_models import (
    EvalVerificationRecipeRecommendation,
)
from glassbox.runtime.eval_verification_recipes import EvalVerificationRecipe
from glassbox.runtime.eval_verification_recipes import recipe_matched_paths
from glassbox.runtime.evals import EvalVerificationStage


def build_recipe_recommendations(
    *,
    normalized_paths: list[str],
    recipes: list[EvalVerificationRecipe],
) -> list[EvalVerificationRecipeRecommendation]:
    recommendations: list[EvalVerificationRecipeRecommendation] = []
    for recipe in recipes:
        matched_paths = recipe_matched_paths(
            normalized_paths=normalized_paths,
            recipe=recipe,
        )
        if not matched_paths:
            continue
        recommendations.append(
            EvalVerificationRecipeRecommendation(
                recipe_id=recipe.recipe_id,
                title=recipe.title,
                matched_paths=matched_paths,
                commands=list(recipe.commands),
                profile_ids=list(recipe.profile_ids),
                case_ids=list(recipe.case_ids),
                notes=recipe.notes,
            )
        )
    recommendations.sort(key=lambda recommendation: recommendation.recipe_id)
    return recommendations


def release_gate_commands(
    stage: EvalVerificationStage,
    touched_paths: list[str],
) -> list[str]:
    if stage != "release-candidate":
        return []
    commands: list[str] = []
    for major in _release_gate_majors(touched_paths):
        script = f"scripts/validate_v{major}_release_gate.py"
        commands.append(f"uv run python {script}")
    if _touches_package_content_gate(touched_paths):
        commands.append("uv run python scripts/validate_package_contents.py")
    return dedupe_strings(commands)


def release_gate_notes(
    stage: EvalVerificationStage,
    touched_paths: list[str],
) -> list[str]:
    if stage != "release-candidate":
        return []
    notes: list[str] = []
    if _release_gate_majors(touched_paths):
        notes.append(
            "Full release gate scripts are sign-off checks; eval profiles are "
            "deterministic replay proof and do not replace the gate."
        )
    if _touches_package_content_gate(touched_paths):
        notes.append(
            "Package-content validation is a packaging gate; run it in addition "
            "to any recommended eval profile."
        )
    return dedupe_strings(notes)


def _release_gate_majors(touched_paths: list[str]) -> list[int]:
    majors: list[int] = []
    for path in touched_paths:
        for major in (11, 10, 9, 8, 7, 6, 5):
            if _touches_major_release_gate(path, major):
                if major not in majors:
                    majors.append(major)
    return majors


def _touches_major_release_gate(path: str, major: int) -> bool:
    return path in {
        f"scripts/validate_v{major}_release_gate.py",
        f"docs/v{major}-release-gate.md",
        f"docs/v{major}-release-candidate.md",
    }


def _touches_package_content_gate(touched_paths: list[str]) -> bool:
    return any(
        path
        in {
            "docs/release-packaging.md",
            "scripts/validate_package_contents.py",
            "tests/unit/test_packaging_metadata.py",
        }
        for path in touched_paths
    )
