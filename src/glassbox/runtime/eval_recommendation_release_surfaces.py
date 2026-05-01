"""Daily-development release-surface derivation for eval recommendations."""

from glassbox.runtime.eval_recommendation_models import _DAILY_RELEASE_STAGES
from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import EvalReleaseSurfaceRecommendation
from glassbox.runtime.eval_recommendation_recipes import release_gate_commands
from glassbox.runtime.eval_recommendation_recipes import release_gate_notes
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.evals import EvalVerificationStage


def build_release_surface_recommendations(
    *,
    touched_paths: list[str],
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
    profiles_by_id: dict[str, EvalProfileDefinition],
) -> list[EvalReleaseSurfaceRecommendation]:
    return [
        _build_release_surface_recommendation(
            stage,
            touched_paths=touched_paths,
            case_recommendations=case_recommendations,
            profile_recommendations=profile_recommendations,
            profiles_by_id=profiles_by_id,
        )
        for stage in _DAILY_RELEASE_STAGES
    ]


def _build_release_surface_recommendation(
    stage: EvalVerificationStage,
    *,
    touched_paths: list[str],
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
        release_gate_commands=release_gate_commands(stage, touched_paths),
        release_gate_notes=release_gate_notes(stage, touched_paths),
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
