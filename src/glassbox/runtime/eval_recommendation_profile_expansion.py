"""Profile-stage and fallback guidance helpers for eval recommendations."""

from glassbox.runtime.eval_recommendation_matching_common import RecommendationReasonMap
from glassbox.runtime.eval_recommendation_matching_common import add_reason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.evals import EvalProfileDefinition


def add_stage_derived_profile_recommendations(
    *,
    profiles: list[EvalProfileDefinition],
    impacted_stages: set[str],
    case_reasons: RecommendationReasonMap,
    profile_reasons: RecommendationReasonMap,
) -> None:
    recommended_case_ids = set(case_reasons)
    for profile in profiles:
        if profile.verification_stage not in impacted_stages:
            continue
        if profile.track != "deterministic":
            continue
        if profile.case_ids and not recommended_case_ids.intersection(
            set(profile.case_ids)
        ):
            continue
        if profile.verification_stage == "advisory" and not profile.case_ids:
            continue
        add_reason(
            profile_reasons,
            profile.profile_id,
            EvalRecommendationReason(
                confidence="stage-derived",
                group="stage-derived-profile",
                summary=(
                    f"verification stage {profile.verification_stage} is "
                    "impacted by the matched cases or capabilities"
                ),
                verification_stage=profile.verification_stage,
            ),
        )


def add_fallback_profile_recommendations(
    *,
    normalized_paths: list[str],
    profiles: list[EvalProfileDefinition],
    case_reasons: RecommendationReasonMap,
    profile_reasons: RecommendationReasonMap,
    warnings: list[str],
) -> None:
    if case_reasons or profile_reasons:
        return

    fallback_profiles = [
        profile
        for profile in profiles
        if profile.verification_stage == "commit-time" and profile.blocking
    ]
    runtime_like_change = any(path.startswith("src/") for path in normalized_paths)
    if runtime_like_change and fallback_profiles:
        for profile in fallback_profiles:
            add_reason(
                profile_reasons,
                profile.profile_id,
                EvalRecommendationReason(
                    confidence="fallback",
                    group="fallback-policy",
                    summary=(
                        "no confident replay/eval mapping was found; use "
                        "the smallest deterministic commit-time profile "
                        "as manual policy guidance"
                    ),
                ),
            )
        warnings.append(
            "No confident replay or eval recommendation was found; fallback "
            "commands are manual policy guidance, not inferred evidence."
        )
        return

    if not warnings:
        warnings.append(
            "No confident replay or eval recommendation was found for "
            "the touched paths."
        )
