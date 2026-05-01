"""Path and rule matching helpers for eval recommendations."""

from fnmatch import fnmatch
from pathlib import Path
from pathlib import PurePosixPath

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.runtime.eval_coverage import DEFAULT_EVAL_COVERAGE_PATH
from glassbox.runtime.eval_coverage import EvalCapabilityDefinition
from glassbox.runtime.eval_impact_rules import DEFAULT_EVAL_IMPACT_PATH
from glassbox.runtime.eval_impact_rules import EvalImpactRule
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalProfileDefinition


class _PathRuleMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: EvalImpactRule
    matched_path: str


type _RecommendationReasonMap = dict[str, list[EvalRecommendationReason]]
type _RuleTargetMatches = dict[str, list[_PathRuleMatch]]


def match_rules(
    normalized_paths: list[str],
    rules: list[EvalImpactRule],
) -> list[_PathRuleMatch]:
    matches: list[_PathRuleMatch] = []
    for normalized_path in normalized_paths:
        pure_path = PurePosixPath(normalized_path)
        for rule in rules:
            if any(
                pure_path.match(path_glob) or fnmatch(normalized_path, path_glob)
                for path_glob in rule.path_globs
            ):
                matches.append(_PathRuleMatch(rule=rule, matched_path=normalized_path))
    return matches


def add_direct_path_recommendations(
    *,
    normalized_paths: list[str],
    case_paths: dict[str, EvalCase],
    profiles: list[EvalProfileDefinition],
    case_reasons: _RecommendationReasonMap,
    profile_reasons: _RecommendationReasonMap,
) -> tuple[set[str], bool, list[str]]:
    matched_paths: set[str] = set()
    warnings: list[str] = []
    coverage_audit_recommended = False
    profiles_path = str(Path("evals") / "profiles.json")

    for touched_path in normalized_paths:
        if touched_path in case_paths:
            case = case_paths[touched_path]
            _add_reason(
                case_reasons,
                case.case_id,
                EvalRecommendationReason(
                    confidence="direct",
                    group="direct-path",
                    summary=f"touched eval case manifest {touched_path}",
                    matched_path=touched_path,
                ),
            )
            matched_paths.add(touched_path)

        if touched_path == str(DEFAULT_EVAL_COVERAGE_PATH):
            coverage_audit_recommended = True
            warnings.append(
                "Touched eval coverage manifest; run eval audit because "
                "capability-to-case expectations may have changed."
            )
            matched_paths.add(touched_path)

        if touched_path == str(DEFAULT_EVAL_IMPACT_PATH):
            warnings.append(
                "Touched eval impact manifest; review recommendations as "
                "metadata-driven guidance."
            )
            matched_paths.add(touched_path)

        if touched_path == profiles_path:
            for profile in profiles:
                _add_reason(
                    profile_reasons,
                    profile.profile_id,
                    EvalRecommendationReason(
                        confidence="direct",
                        group="direct-path",
                        summary=f"touched eval profile manifest {touched_path}",
                        matched_path=touched_path,
                    ),
                )
            matched_paths.add(touched_path)

    return matched_paths, coverage_audit_recommended, warnings


def add_rule_match_recommendations(
    *,
    rule_matches: list[_PathRuleMatch],
    cases_by_id: dict[str, EvalCase],
    profiles_by_id: dict[str, EvalProfileDefinition],
    case_reasons: _RecommendationReasonMap,
    profile_reasons: _RecommendationReasonMap,
) -> tuple[_RuleTargetMatches, _RuleTargetMatches]:
    matched_owners: _RuleTargetMatches = {}
    matched_capabilities: _RuleTargetMatches = {}

    for match in rule_matches:
        rule = match.rule
        for case_id in rule.case_ids:
            if case_id in cases_by_id:
                _add_reason(
                    case_reasons,
                    case_id,
                    EvalRecommendationReason(
                        confidence="direct",
                        group="direct-path",
                        summary=(
                            f"impact rule {rule.rule_id} matched "
                            f"{match.matched_path} and names case {case_id}"
                        ),
                        matched_path=match.matched_path,
                        rule_id=rule.rule_id,
                    ),
                )

        for profile_id in rule.profile_ids:
            if profile_id not in profiles_by_id:
                continue
            _add_reason(
                profile_reasons,
                profile_id,
                EvalRecommendationReason(
                    confidence="direct",
                    group="direct-path",
                    summary=(
                        f"impact rule {rule.rule_id} matched "
                        f"{match.matched_path} and names profile {profile_id}"
                    ),
                    matched_path=match.matched_path,
                    rule_id=rule.rule_id,
                ),
            )

        for owner in rule.owners:
            matched_owners.setdefault(owner, []).append(match)
        for capability_id in rule.capabilities:
            matched_capabilities.setdefault(capability_id, []).append(match)

    return matched_owners, matched_capabilities


def add_owner_derived_case_recommendations(
    *,
    cases: list[EvalCase],
    matched_owners: _RuleTargetMatches,
    case_reasons: _RecommendationReasonMap,
) -> None:
    for owner, owner_matches in matched_owners.items():
        owner_cases = [case for case in cases if case.release_contract.owner == owner]
        for case in owner_cases:
            for match in owner_matches:
                _add_reason(
                    case_reasons,
                    case.case_id,
                    EvalRecommendationReason(
                        confidence="owner-derived",
                        group="owner-derived-rule",
                        summary=(
                            f"impact rule {match.rule.rule_id} matched "
                            f"{match.matched_path} and maps to owner {owner}"
                        ),
                        matched_path=match.matched_path,
                        rule_id=match.rule.rule_id,
                        owner=owner,
                    ),
                )


def add_capability_derived_case_recommendations(
    *,
    cases: list[EvalCase],
    cases_by_id: dict[str, EvalCase],
    capabilities_by_id: dict[str, EvalCapabilityDefinition],
    matched_capabilities: _RuleTargetMatches,
    case_reasons: _RecommendationReasonMap,
) -> None:
    for capability_id, capability_matches in matched_capabilities.items():
        capability = capabilities_by_id.get(capability_id)
        capability_case_ids = _collect_capability_case_ids(
            capability_id=capability_id,
            capability=capability,
            cases=cases,
        )
        for case_id in sorted(capability_case_ids):
            if case_id not in cases_by_id:
                continue
            for match in capability_matches:
                _add_reason(
                    case_reasons,
                    case_id,
                    EvalRecommendationReason(
                        confidence="capability-derived",
                        group="capability-derived-rule",
                        summary=(
                            f"impact rule {match.rule.rule_id} matched "
                            f"{match.matched_path} and maps to capability "
                            f"{capability_id}"
                        ),
                        matched_path=match.matched_path,
                        rule_id=match.rule.rule_id,
                        capability_id=capability_id,
                    ),
                )


def build_impacted_stages(
    *,
    cases_by_id: dict[str, EvalCase],
    capabilities_by_id: dict[str, EvalCapabilityDefinition],
    case_reasons: _RecommendationReasonMap,
    matched_capabilities: _RuleTargetMatches,
) -> set[str]:
    impacted_stages: set[str] = set()
    for case_id in case_reasons:
        impacted_stages.update(
            cases_by_id[case_id].release_contract.verification_stages
        )
    for capability_id in matched_capabilities:
        capability = capabilities_by_id.get(capability_id)
        if capability is not None:
            impacted_stages.update(capability.verification_stages)
    return impacted_stages


def add_stage_derived_profile_recommendations(
    *,
    profiles: list[EvalProfileDefinition],
    impacted_stages: set[str],
    case_reasons: _RecommendationReasonMap,
    profile_reasons: _RecommendationReasonMap,
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
        _add_reason(
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
    case_reasons: _RecommendationReasonMap,
    profile_reasons: _RecommendationReasonMap,
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
            _add_reason(
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


def _collect_capability_case_ids(
    *,
    capability_id: str,
    capability: EvalCapabilityDefinition | None,
    cases: list[EvalCase],
) -> set[str]:
    capability_case_ids: set[str] = set()
    if capability is not None:
        capability_case_ids.update(capability.expected_case_ids)
    capability_case_ids.update(
        case.case_id
        for case in cases
        if capability_id in case.release_contract.capabilities
    )
    return capability_case_ids


def _add_reason(
    destination: dict[str, list[EvalRecommendationReason]],
    key: str,
    reason: EvalRecommendationReason,
) -> None:
    reasons = destination.setdefault(key, [])
    if any(existing.summary == reason.summary for existing in reasons):
        return
    reasons.append(reason)
