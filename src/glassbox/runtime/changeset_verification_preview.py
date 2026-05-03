"""Changeset verification preview helper functions."""

from collections.abc import Sequence
from pathlib import Path

from glassbox.core import ArtifactId
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetVerificationState
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.changeset_models import ChangesetVerificationRecipePreview
from glassbox.runtime.changeset_models import ChangesetVerificationReviewLoopSummary
from glassbox.runtime.changeset_topology import ChangesetTopologyImpact
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
from glassbox.runtime.review_responses import ChangesetReviewResponseSummary


def inventory_paths_for_preview(
    inventory: ChangeInventoryArtifact | None,
) -> list[str]:
    if inventory is None:
        return []
    return [entry.path for entry in inventory.paths[:100]]


def safe_eval_recommendation(
    recommendation: EvalRecommendationReport | None,
) -> EvalRecommendationReport | None:
    if recommendation is None:
        return None
    recipes = [
        recipe.model_copy(
            update={
                "commands": [
                    command
                    for command in recipe.commands
                    if is_safe_verification_command(command)
                ]
            }
        )
        for recipe in recommendation.recipes
    ]
    return recommendation.model_copy(
        update={
            "suggested_commands": [
                command
                for command in recommendation.suggested_commands
                if is_safe_verification_command(command)
            ],
            "fallback_policy_commands": [
                command
                for command in recommendation.fallback_policy_commands
                if is_safe_verification_command(command)
            ],
            "recipes": recipes,
        }
    )


def recommendation_for_preview(
    workspace_root: Path,
    changed_paths: list[str],
) -> tuple[EvalRecommendationReport | None, list[str]]:
    if not changed_paths:
        return None, []
    try:
        return (
            safe_eval_recommendation(
                recommend_eval_change_impact(
                    workspace_root,
                    touched_paths=changed_paths,
                )
            ),
            [],
        )
    except ValueError as exc:
        return None, [f"eval recommendation unavailable: {exc}"]


def preview_commands(
    readiness: ChangesetVerificationReadiness,
    recommendation: EvalRecommendationReport | None,
) -> list[str]:
    commands = (
        list(recommendation.suggested_commands) if recommendation is not None else []
    )
    for requirement in readiness.requirements:
        if requirement.command:
            commands.append(" ".join(requirement.command))
    return [
        command
        for command in dict.fromkeys(commands)
        if is_safe_verification_command(command)
    ]


def is_safe_verification_command(command: str) -> bool:
    tokens = {part.lower() for part in command.replace(";", " ").split()}
    blocked = {
        "deploy",
        "publish",
        "push",
        "rm",
        "upload",
        "release",
        "release:publish",
    }
    return not tokens.intersection(blocked)


def review_loop_verification_summary(
    *,
    changeset: ChangesetRecord,
    response_summary: ChangesetReviewResponseSummary,
    manual_evidence: Sequence[ManualEvidenceRecord],
    readiness: ChangesetVerificationReadiness,
    topology_impacts: Sequence[ChangesetTopologyImpact],
) -> ChangesetVerificationReviewLoopSummary:
    response_state_counts: dict[str, int] = {}
    for item in response_summary.items:
        key = item.response_state.value
        response_state_counts[key] = response_state_counts.get(key, 0) + 1

    manual_evidence_kind_counts: dict[str, int] = {}
    for item in manual_evidence:
        key = item.evidence_kind.value
        manual_evidence_kind_counts[key] = manual_evidence_kind_counts.get(key, 0) + 1

    missing_response_verification_count = sum(
        1
        for item in response_summary.items
        if item.verification_state == ChangesetVerificationState.MISSING
    )
    failed_response_verification_count = sum(
        1
        for item in response_summary.items
        if item.verification_state == ChangesetVerificationState.FAILED
    )
    accepted_risk_response_count = sum(
        1
        for item in response_summary.items
        if item.verification_state == ChangesetVerificationState.ACCEPTED_WITH_RISK
    )
    browser_evidence_count = sum(
        1
        for item in manual_evidence
        if item.evidence_kind
        in {
            ManualEvidenceKind.BROWSER_OBSERVATION,
            ManualEvidenceKind.SCREENSHOT,
        }
    )
    accessibility_evidence_count = sum(
        1
        for item in manual_evidence
        if item.evidence_kind == ManualEvidenceKind.ACCESSIBILITY_NOTE
    )
    safe_next_actions = [
        *response_summary.safe_next_actions,
        (
            "glassbox changeset evidence list --changeset "
            f"{changeset.changeset_id} --cwd ."
        ),
        f"glassbox changeset verification-plan {changeset.changeset_id} --cwd .",
    ]
    limitations: list[str] = []
    if manual_evidence:
        limitations.append(
            "manual evidence can inform verification choice but is not retained "
            "verification proof"
        )
    if missing_response_verification_count:
        limitations.append(
            "one or more review responses lack retained verification mapped to "
            "their fixup paths"
        )
    return ChangesetVerificationReviewLoopSummary(
        feedback_count=response_summary.total_feedback_count,
        open_feedback_count=response_summary.open_count,
        response_state_counts=response_state_counts,
        stale_response_count=response_summary.stale_response_count,
        missing_response_verification_count=missing_response_verification_count,
        failed_response_verification_count=failed_response_verification_count,
        accepted_risk_response_count=accepted_risk_response_count,
        manual_evidence_count=len(manual_evidence),
        manual_evidence_kind_counts=manual_evidence_kind_counts,
        browser_evidence_count=browser_evidence_count,
        accessibility_evidence_count=accessibility_evidence_count,
        stale_check_count=readiness.stale_count,
        topology_impact_count=len(topology_impacts),
        retained_verification_state=readiness.state,
        safe_next_actions=list(dict.fromkeys(safe_next_actions)),
        limitations=limitations,
        non_claims=[
            (
                "manual evidence suggests context only; retained verification "
                "decides check state"
            ),
            "browser and accessibility evidence remain advisory review-loop context",
            "verification plan output is preview-only and does not run commands",
        ],
    )


def eval_profile_ids_for_preview(
    recommendation: EvalRecommendationReport | None,
) -> list[str]:
    if recommendation is None:
        return []
    profile_ids = [profile.profile_id for profile in recommendation.profiles]
    for recipe in recommendation.recipes:
        profile_ids.extend(recipe.profile_ids)
    return list(dict.fromkeys(profile_ids))


def recipe_previews(
    recommendation: EvalRecommendationReport | None,
) -> list[ChangesetVerificationRecipePreview]:
    if recommendation is None:
        return []
    return [
        ChangesetVerificationRecipePreview(
            recipe_id=recipe.recipe_id,
            title=recipe.title,
            confidence=recipe.confidence,
            source=recipe.source,
            matched_paths=recipe.matched_paths,
            component_ids=recipe.component_ids,
            commands=recipe.commands,
            profile_ids=recipe.profile_ids,
            case_ids=recipe.case_ids,
            notes=recipe.notes,
            limitations=recipe.limitations,
        )
        for recipe in recommendation.recipes
    ]


def artifact_ids_from_readiness(
    readiness: ChangesetVerificationReadiness,
) -> list[ArtifactId]:
    artifact_ids = [
        requirement.artifact_id
        for requirement in readiness.requirements
        if requirement.artifact_id is not None
    ]
    return list(dict.fromkeys(artifact_ids))


__all__ = [
    "artifact_ids_from_readiness",
    "eval_profile_ids_for_preview",
    "inventory_paths_for_preview",
    "is_safe_verification_command",
    "preview_commands",
    "recipe_previews",
    "recommendation_for_preview",
    "review_loop_verification_summary",
    "safe_eval_recommendation",
]
