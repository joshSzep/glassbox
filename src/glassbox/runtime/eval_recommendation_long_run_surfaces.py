"""Long-running verification-surface derivation for eval recommendations."""

from glassbox.runtime.eval_recommendation_common import commands_for_recommendations
from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_models import _LONG_RUN_SURFACES
from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalLongRunSurfaceRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import LongRunVerificationSurface


def build_long_run_surface_recommendations(
    *,
    touched_paths: list[str],
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
) -> list[EvalLongRunSurfaceRecommendation]:
    risk_tags = _long_run_risk_tags(touched_paths)
    return [
        _build_long_run_surface_recommendation(
            surface,
            risk_tags=risk_tags,
            case_recommendations=case_recommendations,
            profile_recommendations=profile_recommendations,
        )
        for surface in _LONG_RUN_SURFACES
    ]


def _build_long_run_surface_recommendation(
    surface: LongRunVerificationSurface,
    *,
    risk_tags: list[str],
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
) -> EvalLongRunSurfaceRecommendation:
    cases = _long_run_surface_cases(surface, case_recommendations, risk_tags)
    profiles = _long_run_surface_profiles(surface, profile_recommendations, risk_tags)
    reasons = _long_run_surface_reasons(surface, risk_tags, cases, profiles)
    return EvalLongRunSurfaceRecommendation(
        surface=surface,
        impacted=bool(cases or profiles or reasons),
        recommended_case_ids=[case.case_id for case in cases],
        recommended_profile_ids=[profile.profile_id for profile in profiles],
        suggested_commands=commands_for_recommendations(cases, profiles),
        reasons=reasons,
    )


def _long_run_surface_cases(
    surface: LongRunVerificationSurface,
    case_recommendations: list[EvalCaseRecommendation],
    risk_tags: list[str],
) -> list[EvalCaseRecommendation]:
    if surface == "release-candidate":
        selected = [
            case
            for case in case_recommendations
            if "release-candidate" in case.verification_stages
        ]
        return selected or (case_recommendations if risk_tags else [])
    if surface in {"immediate", "pre-merge"}:
        return case_recommendations
    if surface in {"checkpoint", "pre-resume"} and risk_tags:
        return case_recommendations
    return []


def _long_run_surface_profiles(
    surface: LongRunVerificationSurface,
    profile_recommendations: list[EvalProfileRecommendation],
    risk_tags: list[str],
) -> list[EvalProfileRecommendation]:
    deterministic = [
        profile
        for profile in profile_recommendations
        if profile.track == "deterministic"
    ]
    if surface == "immediate":
        return [
            profile
            for profile in deterministic
            if profile.verification_stage == "commit-time"
        ]
    if surface == "checkpoint":
        if not risk_tags:
            return []
        return [
            profile
            for profile in deterministic
            if profile.verification_stage in {"commit-time", "advisory"}
        ]
    if surface == "pre-resume":
        return deterministic if risk_tags else []
    if surface == "pre-merge":
        return [
            profile
            for profile in deterministic
            if profile.verification_stage in {"commit-time", "push-time", "advisory"}
        ]
    if surface == "release-candidate":
        selected = [
            profile
            for profile in deterministic
            if profile.verification_stage == "release-candidate"
        ]
        return selected or (deterministic if risk_tags else [])
    return []


def _long_run_surface_reasons(
    surface: LongRunVerificationSurface,
    risk_tags: list[str],
    cases: list[EvalCaseRecommendation],
    profiles: list[EvalProfileRecommendation],
) -> list[str]:
    reasons: list[str] = []
    if cases or profiles:
        reasons.append(_surface_default_reason(surface))
    if risk_tags:
        reasons.append("long-run risk tags: " + ", ".join(risk_tags))
    return dedupe_strings(reasons)


def _surface_default_reason(surface: LongRunVerificationSurface) -> str:
    if surface == "immediate":
        return "run focused deterministic proof before continuing local work"
    if surface == "checkpoint":
        return "refresh proof before recording or trusting a checkpoint"
    if surface == "pre-resume":
        return "verify recovery-sensitive state before resuming a long task"
    if surface == "pre-merge":
        return "run merge-bound deterministic proof before handing off changes"
    return "include release-candidate proof for long-run infrastructure changes"


def _long_run_risk_tags(touched_paths: list[str]) -> list[str]:
    tags: list[str] = []
    for path in touched_paths:
        normalized = path.replace("\\", "/")
        _add_long_run_tag(tags, normalized, "checkpoint", ["checkpoint"])
        _add_long_run_tag(tags, normalized, "compaction", ["compaction"])
        _add_long_run_tag(
            tags,
            normalized,
            "tool-attempt",
            ["tool_attempt", "tool-attempt"],
        )
        _add_long_run_tag(tags, normalized, "provider-recovery", ["provider"])
        _add_long_run_tag(
            tags,
            normalized,
            "verification-drift",
            ["verification", "task_queries.py"],
        )
        _add_long_run_tag(
            tags,
            normalized,
            "long-run-cockpit",
            [
                "long-run-cockpit",
                "task-autonomy",
                "workspace-overview",
                "frontend/components/console",
                "dashboard-cockpit",
            ],
        )
    return tags


def _add_long_run_tag(
    tags: list[str],
    path: str,
    tag: str,
    needles: list[str],
) -> None:
    if tag in tags:
        return
    if any(needle in path for needle in needles):
        tags.append(tag)
