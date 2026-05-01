"""Shared helpers for eval recommendation output construction."""

from glassbox.runtime.eval_recommendation_models import _CONFIDENCE_PRIORITY
from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import EvalRecommendationConfidence
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason


def dedupe_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def sort_reasons(
    reasons: list[EvalRecommendationReason],
) -> list[EvalRecommendationReason]:
    return sorted(
        reasons,
        key=lambda reason: (
            -_CONFIDENCE_PRIORITY[reason.confidence],
            reason.summary,
        ),
    )


def strongest_confidence(
    reasons: list[EvalRecommendationReason],
) -> EvalRecommendationConfidence:
    strongest = max(reasons, key=lambda reason: _CONFIDENCE_PRIORITY[reason.confidence])
    return strongest.confidence


def commands_for_recommendations(
    cases: list[EvalCaseRecommendation],
    profiles: list[EvalProfileRecommendation],
) -> list[str]:
    commands: list[str] = []
    if cases:
        case_ids = " ".join(case.case_id for case in cases)
        commands.append(f"uv run glassbox eval run {case_ids} --cwd .")
    for profile in profiles:
        if profile.track != "deterministic":
            continue
        commands.append(
            f"uv run glassbox eval run --profile {profile.profile_id} --cwd ."
        )
    return dedupe_strings(commands)
