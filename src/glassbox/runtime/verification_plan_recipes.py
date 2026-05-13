"""Verification-plan entries derived from command recipe recommendations."""

from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.runtime.changeset_models import ChangesetVerificationSkippedCheckPreview
from glassbox.runtime.changeset_verification_preview import is_safe_verification_command
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_recommendation_models import (
    EvalVerificationRecipeRecommendation,
)
from glassbox.runtime.verification_plan_entries import build_verification_entry
from glassbox.runtime.verification_plan_entries import command_parts
from glassbox.runtime.verification_plan_entries import lifecycle_for_freshness
from glassbox.runtime.verification_plan_entries import stale_reasons
from glassbox.runtime.verification_plan_skips import unsafe_command_skipped_row


def build_recipe_verification_entries(
    recommendation: EvalRecommendationReport,
    *,
    changed_paths: list[str],
) -> tuple[list[VerificationPlanEntry], list[ChangesetVerificationSkippedCheckPreview]]:
    """Build safe command recipe entries and unsafe-command skipped rows."""

    entries: list[VerificationPlanEntry] = []
    skipped: list[ChangesetVerificationSkippedCheckPreview] = []
    for recipe in recommendation.recipes:
        for command in recipe.commands:
            if not is_safe_verification_command(command):
                skipped.append(
                    unsafe_command_skipped_row(
                        target_id=recipe.recipe_id,
                        matched_paths=recipe.matched_paths,
                    )
                )
                continue
            entries.append(
                _entry_for_recipe(
                    recipe,
                    command,
                    changed_paths=changed_paths,
                )
            )
    return entries, skipped


def _entry_for_recipe(
    recipe: EvalVerificationRecipeRecommendation,
    command: str,
    *,
    changed_paths: list[str],
) -> VerificationPlanEntry:
    return build_verification_entry(
        seed=f"recipe:{recipe.recipe_id}:{command}",
        check_name=recipe.title,
        kind=VerificationCheckKind.COMMAND,
        command=command_parts(command),
        source=(
            VerificationPlanSource.REPOSITORY_INTELLIGENCE
            if recipe.source == "repository-intelligence"
            else VerificationPlanSource.COMMAND_RECIPE
        ),
        target_id=recipe.recipe_id,
        target_label=recipe.title,
        rationale=recipe.notes
        or f"Verification recipe matched {len(recipe.matched_paths)} changed path(s).",
        selection_rationale=(
            f"{recipe.confidence} confidence recipe from {recipe.source}"
        ),
        changed_paths=recipe.matched_paths or changed_paths,
        stale_reasons=stale_reasons(recipe.freshness),
        lifecycle_state=lifecycle_for_freshness(recipe.freshness),
        evidence_references=[
            NextActionEvidenceRef(
                kind=NextActionEvidenceKind.REPOSITORY_INTELLIGENCE,
                ref_id=recipe.recipe_id,
                summary=f"Verification recipe {recipe.recipe_id} matched paths.",
                freshness=recipe.freshness,
            )
        ],
    )


__all__ = ["build_recipe_verification_entries"]
