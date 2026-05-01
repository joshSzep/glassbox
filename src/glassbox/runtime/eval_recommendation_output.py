"""Output assembly helpers for eval recommendation reports."""

from glassbox.runtime.eval_recommendation_models import _CONFIDENCE_PRIORITY
from glassbox.runtime.eval_recommendation_models import _DAILY_RELEASE_STAGES
from glassbox.runtime.eval_recommendation_models import _LONG_RUN_SURFACES
from glassbox.runtime.eval_recommendation_models import EvalCaseRecommendation
from glassbox.runtime.eval_recommendation_models import EvalLongRunSurfaceRecommendation
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import EvalRecommendationConfidence
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReasonGroup
from glassbox.runtime.eval_recommendation_models import (
    EvalRecommendationReasonGroupKind,
)
from glassbox.runtime.eval_recommendation_models import EvalReleaseSurfaceRecommendation
from glassbox.runtime.eval_recommendation_models import LongRunVerificationSurface
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
    return _commands_for_recommendations(fallback_cases, fallback_profiles)


def build_reason_groups(
    *,
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
    release_surfaces: list[EvalReleaseSurfaceRecommendation],
) -> list[EvalRecommendationReasonGroup]:
    groups: dict[EvalRecommendationReasonGroupKind, EvalRecommendationReasonGroup] = {}
    for case in case_recommendations:
        for reason in case.reasons:
            group = _ensure_reason_group(groups, reason.group)
            _append_unique(group.summaries, reason.summary)
            _append_optional_unique(group.matched_paths, reason.matched_path)
            _append_optional_unique(group.rule_ids, reason.rule_id)
            _append_unique(group.recommended_case_ids, case.case_id)

    for profile in profile_recommendations:
        for reason in profile.reasons:
            group = _ensure_reason_group(groups, reason.group)
            _append_unique(group.summaries, reason.summary)
            _append_optional_unique(group.matched_paths, reason.matched_path)
            _append_optional_unique(group.rule_ids, reason.rule_id)
            _append_unique(group.recommended_profile_ids, profile.profile_id)

    release_gate_commands: list[str] = []
    release_gate_summaries: list[str] = []
    for surface in release_surfaces:
        for command in surface.release_gate_commands:
            _append_unique(release_gate_commands, command)
        for note in surface.release_gate_notes:
            _append_unique(release_gate_summaries, note)
    if release_gate_commands:
        group = _ensure_reason_group(groups, "release-gate-recommendation")
        for command in release_gate_commands:
            _append_unique(group.release_gate_commands, command)
        for summary in release_gate_summaries:
            _append_unique(group.summaries, summary)

    return [
        groups[group]
        for group in (
            "direct-path",
            "owner-derived-rule",
            "capability-derived-rule",
            "stage-derived-profile",
            "release-gate-recommendation",
            "fallback-policy",
        )
        if group in groups
    ]


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
        release_gate_commands=_release_gate_commands(stage, touched_paths),
        release_gate_notes=_release_gate_notes(stage, touched_paths),
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


def _release_gate_commands(
    stage: EvalVerificationStage,
    touched_paths: list[str],
) -> list[str]:
    if stage != "release-candidate":
        return []
    commands: list[str] = []
    for major in _release_gate_majors(touched_paths):
        script = f"scripts/validate_v{major}_release_gate.py"
        commands.append(f"uv run python {script} --cwd .")
    if _touches_package_content_gate(touched_paths):
        commands.append("uv run python scripts/validate_package_contents.py")
    return dedupe_strings(commands)


def _release_gate_notes(
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
        for major in (10, 9, 8, 7, 6, 5):
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
        suggested_commands=_commands_for_recommendations(cases, profiles),
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


def _commands_for_recommendations(
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


def _ensure_reason_group(
    groups: dict[EvalRecommendationReasonGroupKind, EvalRecommendationReasonGroup],
    group: EvalRecommendationReasonGroupKind,
) -> EvalRecommendationReasonGroup:
    existing = groups.get(group)
    if existing is not None:
        return existing
    created = EvalRecommendationReasonGroup(
        group=group,
        title=_reason_group_title(group),
    )
    groups[group] = created
    return created


def _reason_group_title(group: EvalRecommendationReasonGroupKind) -> str:
    if group == "direct-path":
        return "Direct path matches"
    if group == "owner-derived-rule":
        return "Owner-derived rule matches"
    if group == "capability-derived-rule":
        return "Capability-derived rule matches"
    if group == "stage-derived-profile":
        return "Stage-derived profile matches"
    if group == "release-gate-recommendation":
        return "Release gate recommendations"
    return "Fallback policy guidance"


def _append_optional_unique(values: list[str], value: str | None) -> None:
    if value is not None:
        _append_unique(values, value)


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


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
