"""Command-plan construction for eval recommendation reports."""

from glassbox.runtime.eval_recommendation_common import commands_for_recommendations
from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation


def build_suggested_commands(
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
    *,
    coverage_audit_recommended: bool,
) -> list[str]:
    commands: list[str] = []
    if case_recommendations:
        case_ids = " ".join(
            recommendation.case_id for recommendation in case_recommendations
        )
        commands.append(f"uv run glassbox eval run {case_ids} --cwd .")
    for recommendation in profile_recommendations:
        if recommendation.track != "deterministic":
            continue
        commands.append(
            f"uv run glassbox eval run --profile {recommendation.profile_id} --cwd ."
        )
    if coverage_audit_recommended:
        commands.append("uv run glassbox eval audit --cwd .")
    return dedupe_strings(commands)


def build_cheapest_next_command(
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
    *,
    coverage_audit_recommended: bool,
) -> str | None:
    """Return the narrowest visible command before broader release checks."""

    if case_recommendations:
        case_ids = " ".join(
            recommendation.case_id for recommendation in case_recommendations
        )
        return f"uv run glassbox eval run {case_ids} --cwd ."

    stage_order: dict[str, int] = {
        "commit-time": 0,
        "push-time": 1,
        "advisory": 2,
        "release-candidate": 3,
    }
    deterministic_profiles = sorted(
        (
            recommendation
            for recommendation in profile_recommendations
            if recommendation.track == "deterministic"
        ),
        key=lambda recommendation: (
            stage_order.get(recommendation.verification_stage, 99),
            recommendation.profile_id,
        ),
    )
    if deterministic_profiles:
        profile = deterministic_profiles[0]
        return f"uv run glassbox eval run --profile {profile.profile_id} --cwd ."

    if coverage_audit_recommended:
        return "uv run glassbox eval audit --cwd ."
    return None


def build_fallback_policy_commands(
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
) -> list[str]:
    fallback_cases = [
        recommendation
        for recommendation in case_recommendations
        if recommendation.confidence == "fallback"
    ]
    fallback_profiles = [
        recommendation
        for recommendation in profile_recommendations
        if recommendation.confidence == "fallback"
    ]
    return commands_for_recommendations(fallback_cases, fallback_profiles)
