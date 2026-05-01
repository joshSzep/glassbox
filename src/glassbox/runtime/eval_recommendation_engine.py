"""Recommendation engine for replay/eval change-impact reports."""

from pathlib import Path

from glassbox.runtime.eval_coverage import DEFAULT_EVAL_COVERAGE_PATH
from glassbox.runtime.eval_coverage import EvalCapabilityDefinition
from glassbox.runtime.eval_coverage import load_eval_coverage_manifest
from glassbox.runtime.eval_impact_rules import maybe_load_eval_impact_manifest
from glassbox.runtime.eval_recommendation_case_expansion import (
    add_capability_derived_case_recommendations,
)
from glassbox.runtime.eval_recommendation_case_expansion import (
    add_owner_derived_case_recommendations,
)
from glassbox.runtime.eval_recommendation_case_expansion import build_impacted_stages
from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_long_run_surfaces import (
    build_long_run_surface_recommendations,
)
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_recommendation_path_matching import (
    add_direct_path_recommendations,
)
from glassbox.runtime.eval_recommendation_path_matching import (
    add_rule_match_recommendations,
)
from glassbox.runtime.eval_recommendation_path_matching import match_rules
from glassbox.runtime.eval_recommendation_plans import build_cheapest_next_command
from glassbox.runtime.eval_recommendation_plans import build_fallback_policy_commands
from glassbox.runtime.eval_recommendation_plans import build_suggested_commands
from glassbox.runtime.eval_recommendation_profile_expansion import (
    add_fallback_profile_recommendations,
)
from glassbox.runtime.eval_recommendation_profile_expansion import (
    add_stage_derived_profile_recommendations,
)
from glassbox.runtime.eval_recommendation_reason_groups import build_reason_groups
from glassbox.runtime.eval_recommendation_recipes import build_recipe_recommendations
from glassbox.runtime.eval_recommendation_release_surfaces import (
    build_release_surface_recommendations,
)
from glassbox.runtime.eval_recommendation_rows import build_case_recommendations
from glassbox.runtime.eval_recommendation_rows import build_profile_recommendations
from glassbox.runtime.eval_verification_recipes import (
    maybe_load_eval_verification_recipe_manifest,
)
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import _ensure_path_within_root
from glassbox.runtime.evals import discover_eval_case_files
from glassbox.runtime.evals import load_eval_case
from glassbox.runtime.evals import load_eval_profiles


def recommend_eval_change_impact(
    workspace_root: Path,
    *,
    touched_paths: list[str],
    impact_path: Path | None = None,
    coverage_path: Path | None = None,
    recipes_path: Path | None = None,
) -> EvalRecommendationReport:
    """Recommend replay/eval cases and profiles for one changed path set."""

    resolved_workspace_root = workspace_root.resolve()
    normalized_paths = [
        _normalize_touched_path(resolved_workspace_root, touched_path)
        for touched_path in touched_paths
    ]

    cases = _load_all_eval_cases(resolved_workspace_root)
    cases_by_id = {case.case_id: case for case in cases}
    case_paths = {
        str(case.case_path.relative_to(resolved_workspace_root)).replace("\\", "/"): (
            case
        )
        for case in cases
    }
    profiles = load_eval_profiles(resolved_workspace_root)
    profiles_by_id = {profile.profile_id: profile for profile in profiles}
    capabilities = _load_capabilities(
        resolved_workspace_root,
        coverage_path=coverage_path,
    )
    capabilities_by_id = {
        capability.capability_id: capability for capability in capabilities
    }
    impact_manifest = maybe_load_eval_impact_manifest(
        resolved_workspace_root,
        impact_path=impact_path,
    )
    rules = [] if impact_manifest is None else impact_manifest.rules
    recipe_manifest = maybe_load_eval_verification_recipe_manifest(
        resolved_workspace_root,
        recipes_path=recipes_path,
    )
    recipes = [] if recipe_manifest is None else recipe_manifest.recipes

    case_reasons: dict[str, list[EvalRecommendationReason]] = {}
    profile_reasons: dict[str, list[EvalRecommendationReason]] = {}
    matched_paths, coverage_audit_recommended, warnings = (
        add_direct_path_recommendations(
            normalized_paths=normalized_paths,
            case_paths=case_paths,
            profiles=profiles,
            case_reasons=case_reasons,
            profile_reasons=profile_reasons,
        )
    )

    rule_matches = match_rules(normalized_paths, rules)
    matched_rule_ids = {match.rule.rule_id for match in rule_matches}
    matched_paths.update(match.matched_path for match in rule_matches)
    matched_owners, matched_capabilities = add_rule_match_recommendations(
        rule_matches=rule_matches,
        cases_by_id=cases_by_id,
        profiles_by_id=profiles_by_id,
        case_reasons=case_reasons,
        profile_reasons=profile_reasons,
    )
    add_owner_derived_case_recommendations(
        cases=cases,
        matched_owners=matched_owners,
        case_reasons=case_reasons,
    )
    add_capability_derived_case_recommendations(
        cases=cases,
        cases_by_id=cases_by_id,
        capabilities_by_id=capabilities_by_id,
        matched_capabilities=matched_capabilities,
        case_reasons=case_reasons,
    )

    impacted_stages = build_impacted_stages(
        cases_by_id=cases_by_id,
        capabilities_by_id=capabilities_by_id,
        case_reasons=case_reasons,
        matched_capabilities=matched_capabilities,
    )
    add_stage_derived_profile_recommendations(
        profiles=profiles,
        impacted_stages=impacted_stages,
        case_reasons=case_reasons,
        profile_reasons=profile_reasons,
    )
    add_fallback_profile_recommendations(
        normalized_paths=normalized_paths,
        profiles=profiles,
        case_reasons=case_reasons,
        profile_reasons=profile_reasons,
        warnings=warnings,
    )

    case_recommendations = build_case_recommendations(cases_by_id, case_reasons)
    profile_recommendations = build_profile_recommendations(
        profiles_by_id,
        profile_reasons,
    )
    unmatched_paths = [path for path in normalized_paths if path not in matched_paths]
    suggested_commands = build_suggested_commands(
        case_recommendations,
        profile_recommendations,
        coverage_audit_recommended=coverage_audit_recommended,
    )
    release_surfaces = build_release_surface_recommendations(
        touched_paths=normalized_paths,
        case_recommendations=case_recommendations,
        profile_recommendations=profile_recommendations,
        profiles_by_id=profiles_by_id,
    )
    long_run_surfaces = build_long_run_surface_recommendations(
        touched_paths=normalized_paths,
        case_recommendations=case_recommendations,
        profile_recommendations=profile_recommendations,
    )
    reason_groups = build_reason_groups(
        case_recommendations=case_recommendations,
        profile_recommendations=profile_recommendations,
        release_surfaces=release_surfaces,
    )
    recipe_recommendations = build_recipe_recommendations(
        normalized_paths=normalized_paths,
        recipes=recipes,
    )

    return EvalRecommendationReport(
        workspace_root=resolved_workspace_root,
        touched_paths=normalized_paths,
        matched_rule_ids=sorted(matched_rule_ids),
        unmatched_paths=unmatched_paths,
        coverage_audit_recommended=coverage_audit_recommended,
        warnings=dedupe_strings(warnings),
        release_surfaces=release_surfaces,
        long_run_surfaces=long_run_surfaces,
        cases=case_recommendations,
        profiles=profile_recommendations,
        recipes=recipe_recommendations,
        suggested_commands=suggested_commands,
        cheapest_next_command=build_cheapest_next_command(
            case_recommendations,
            profile_recommendations,
            coverage_audit_recommended=coverage_audit_recommended,
        ),
        fallback_policy_commands=build_fallback_policy_commands(
            case_recommendations,
            profile_recommendations,
        ),
        reason_groups=reason_groups,
    )


def _normalize_touched_path(workspace_root: Path, touched_path: str) -> str:
    raw_path = Path(touched_path)
    resolved_path = (
        raw_path.resolve()
        if raw_path.is_absolute()
        else (workspace_root / raw_path).resolve()
    )
    _ensure_path_within_root(resolved_path, workspace_root, kind="touched path")
    return str(resolved_path.relative_to(workspace_root)).replace("\\", "/")


def _load_all_eval_cases(workspace_root: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for case_path in discover_eval_case_files(workspace_root):
        cases.append(load_eval_case(case_path, workspace_root=workspace_root))
    cases.sort(key=lambda case: case.case_id)
    return cases


def _load_capabilities(
    workspace_root: Path,
    *,
    coverage_path: Path | None,
) -> list[EvalCapabilityDefinition]:
    try:
        return load_eval_coverage_manifest(
            workspace_root,
            coverage_path=coverage_path,
        ).capabilities
    except ValueError as exc:
        resolved_path = _resolve_optional_manifest_path(
            workspace_root,
            coverage_path,
            DEFAULT_EVAL_COVERAGE_PATH,
        )
        if "missing eval coverage manifest" in str(exc) and not resolved_path.exists():
            return []
        raise


def _resolve_optional_manifest_path(
    workspace_root: Path,
    path: Path | None,
    default_path: Path,
) -> Path:
    if path is None:
        return (workspace_root.resolve() / default_path).resolve()
    if path.is_absolute():
        return path.resolve()
    return (workspace_root.resolve() / path).resolve()
