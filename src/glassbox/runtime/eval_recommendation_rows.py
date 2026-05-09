"""Case and profile row construction for eval recommendation reports."""

from glassbox.runtime.eval_recommendation_common import sort_reasons
from glassbox.runtime.eval_recommendation_common import strongest_confidence
from glassbox.runtime.eval_recommendation_models import _CONFIDENCE_PRIORITY
from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationSourceMetadata
from glassbox.runtime.eval_recommendation_profile_rows import (
    profile_budget_implications,
)
from glassbox.runtime.eval_recommendation_profile_rows import profile_safe_next_commands
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalProfileDefinition


def build_case_recommendations(
    cases_by_id: dict[str, EvalCase],
    case_reasons: dict[str, list[EvalRecommendationReason]],
    *,
    source_metadata_by_case_id: dict[str, list[EvalRecommendationSourceMetadata]]
    | None = None,
    safe_next_commands_by_case_id: dict[str, list[str]] | None = None,
) -> list[EvalCaseRecommendation]:
    source_metadata_by_case_id = source_metadata_by_case_id or {}
    safe_next_commands_by_case_id = safe_next_commands_by_case_id or {}
    recommendations: list[EvalCaseRecommendation] = []
    for case_id, reasons in case_reasons.items():
        case = cases_by_id.get(case_id)
        if case is None:
            continue
        sorted_reasons = sort_reasons(reasons)
        recommendations.append(
            EvalCaseRecommendation(
                case_id=case.case_id,
                title=case.title,
                confidence=strongest_confidence(sorted_reasons),
                owner=case.release_contract.owner,
                capabilities=list(case.release_contract.capabilities),
                verification_stages=list(case.release_contract.verification_stages),
                matched_paths=_reason_matched_paths(sorted_reasons),
                source_metadata=source_metadata_by_case_id.get(case.case_id, []),
                safe_next_commands=safe_next_commands_by_case_id.get(
                    case.case_id,
                    [],
                ),
                reasons=sorted_reasons,
            )
        )
    recommendations.sort(
        key=lambda recommendation: (
            -_CONFIDENCE_PRIORITY[recommendation.confidence],
            recommendation.case_id,
        )
    )
    return recommendations


def build_profile_recommendations(
    profiles_by_id: dict[str, EvalProfileDefinition],
    profile_reasons: dict[str, list[EvalRecommendationReason]],
    *,
    source_metadata_by_profile_id: dict[str, list[EvalRecommendationSourceMetadata]]
    | None = None,
    safe_next_commands_by_profile_id: dict[str, list[str]] | None = None,
) -> list[EvalProfileRecommendation]:
    source_metadata_by_profile_id = source_metadata_by_profile_id or {}
    safe_next_commands_by_profile_id = safe_next_commands_by_profile_id or {}
    recommendations: list[EvalProfileRecommendation] = []
    for profile_id, reasons in profile_reasons.items():
        profile = profiles_by_id.get(profile_id)
        if profile is None:
            continue
        sorted_reasons = sort_reasons(reasons)
        recommendations.append(
            EvalProfileRecommendation(
                profile_id=profile.profile_id,
                title=profile.title,
                confidence=strongest_confidence(sorted_reasons),
                verification_stage=profile.verification_stage,
                track=profile.track,
                blocking=profile.blocking,
                matched_paths=_reason_matched_paths(sorted_reasons),
                source_metadata=source_metadata_by_profile_id.get(
                    profile.profile_id,
                    [],
                ),
                budget_implications=profile_budget_implications(profile),
                safe_next_commands=safe_next_commands_by_profile_id.get(
                    profile.profile_id,
                    profile_safe_next_commands(profile),
                ),
                reasons=sorted_reasons,
            )
        )
    recommendations.sort(
        key=lambda recommendation: (
            -_CONFIDENCE_PRIORITY[recommendation.confidence],
            recommendation.profile_id,
        )
    )
    return recommendations


def _reason_matched_paths(reasons: list[EvalRecommendationReason]) -> list[str]:
    return list(
        dict.fromkeys(reason.matched_path for reason in reasons if reason.matched_path)
    )
