"""Output assembly helpers for eval recommendation reports."""

from glassbox.runtime.eval_recommendation_models import _CONFIDENCE_PRIORITY
from glassbox.runtime.eval_recommendation_models import _DAILY_RELEASE_STAGES
from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import EvalRecommendationConfidence
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.eval_recommendation_models import EvalReleaseSurfaceRecommendation
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.evals import EvalVerificationStage


def build_case_recommendations(
    cases_by_id: dict[str, EvalCase],
    case_reasons: dict[str, list[EvalRecommendationReason]],
) -> list[EvalCaseRecommendation]:
    recommendations: list[EvalCaseRecommendation] = []
    for case_id, reasons in case_reasons.items():
        case = cases_by_id.get(case_id)
        if case is None:
            continue
        sorted_reasons = _sort_reasons(reasons)
        recommendations.append(
            EvalCaseRecommendation(
                case_id=case.case_id,
                title=case.title,
                confidence=_strongest_confidence(sorted_reasons),
                owner=case.release_contract.owner,
                capabilities=list(case.release_contract.capabilities),
                verification_stages=list(case.release_contract.verification_stages),
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
) -> list[EvalProfileRecommendation]:
    recommendations: list[EvalProfileRecommendation] = []
    for profile_id, reasons in profile_reasons.items():
        profile = profiles_by_id.get(profile_id)
        if profile is None:
            continue
        sorted_reasons = _sort_reasons(reasons)
        recommendations.append(
            EvalProfileRecommendation(
                profile_id=profile.profile_id,
                title=profile.title,
                confidence=_strongest_confidence(sorted_reasons),
                verification_stage=profile.verification_stage,
                track=profile.track,
                blocking=profile.blocking,
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


def build_release_surface_recommendations(
    *,
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
    profiles_by_id: dict[str, EvalProfileDefinition],
) -> list[EvalReleaseSurfaceRecommendation]:
    return [
        _build_release_surface_recommendation(
            stage,
            case_recommendations=case_recommendations,
            profile_recommendations=profile_recommendations,
            profiles_by_id=profiles_by_id,
        )
        for stage in _DAILY_RELEASE_STAGES
    ]


def dedupe_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _sort_reasons(
    reasons: list[EvalRecommendationReason],
) -> list[EvalRecommendationReason]:
    return sorted(
        reasons,
        key=lambda reason: (
            -_CONFIDENCE_PRIORITY[reason.confidence],
            reason.summary,
        ),
    )


def _strongest_confidence(
    reasons: list[EvalRecommendationReason],
) -> EvalRecommendationConfidence:
    strongest = max(reasons, key=lambda reason: _CONFIDENCE_PRIORITY[reason.confidence])
    return strongest.confidence


def _build_release_surface_recommendation(
    stage: EvalVerificationStage,
    *,
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
    profiles_by_id: dict[str, EvalProfileDefinition],
) -> EvalReleaseSurfaceRecommendation:
    stage_cases = [
        recommendation
        for recommendation in case_recommendations
        if stage in recommendation.verification_stages
    ]
    stage_profiles = [
        recommendation
        for recommendation in profile_recommendations
        if recommendation.verification_stage == stage
    ]
    return EvalReleaseSurfaceRecommendation(
        verification_stage=stage,
        impacted=bool(stage_cases or stage_profiles),
        recommended_case_ids=[case.case_id for case in stage_cases],
        recommended_profile_ids=[profile.profile_id for profile in stage_profiles],
        blocking_profile_ids=[
            profile.profile_id for profile in stage_profiles if profile.blocking
        ],
        impacted_capability_ids=_stage_capability_ids(stage_cases),
        owner_ids=_stage_owner_ids(stage_cases),
        profile_budget_notes=_stage_profile_budget_notes(
            stage_profiles,
            profiles_by_id=profiles_by_id,
        ),
    )


def _stage_capability_ids(
    stage_cases: list[EvalCaseRecommendation],
) -> list[str]:
    capability_ids: list[str] = []
    for case in stage_cases:
        for capability_id in case.capabilities:
            if capability_id not in capability_ids:
                capability_ids.append(capability_id)
    return capability_ids


def _stage_owner_ids(stage_cases: list[EvalCaseRecommendation]) -> list[str]:
    owner_ids: list[str] = []
    for case in stage_cases:
        if case.owner is None or case.owner in owner_ids:
            continue
        owner_ids.append(case.owner)
    return owner_ids


def _stage_profile_budget_notes(
    stage_profiles: list[EvalProfileRecommendation],
    *,
    profiles_by_id: dict[str, EvalProfileDefinition],
) -> list[str]:
    notes: list[str] = []
    for profile_recommendation in stage_profiles:
        profile = profiles_by_id.get(profile_recommendation.profile_id)
        if profile is None or profile.budget is None:
            continue
        budget = profile.budget
        fragments: list[str] = []
        if budget.max_selected_case_count is not None:
            fragments.append(f"case limit {budget.max_selected_case_count}")
        if budget.max_selected_invariant_case_count is not None:
            fragments.append(
                f"selected-invariant limit {budget.max_selected_invariant_case_count}"
            )
        if budget.max_recorded_model_call_count is not None:
            fragments.append(f"model-call limit {budget.max_recorded_model_call_count}")
        if budget.allow_advisory_cases is False:
            fragments.append("advisory cases disallowed")
        if fragments:
            notes.append(f"{profile.profile_id}: " + "; ".join(fragments))
    return notes
