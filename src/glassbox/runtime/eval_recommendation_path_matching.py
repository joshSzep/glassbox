"""Path and impact-rule matching helpers for eval recommendations."""

from fnmatch import fnmatch
from pathlib import Path
from pathlib import PurePosixPath

from glassbox.runtime.eval_coverage import DEFAULT_EVAL_COVERAGE_PATH
from glassbox.runtime.eval_impact_rules import DEFAULT_EVAL_IMPACT_PATH
from glassbox.runtime.eval_impact_rules import EvalImpactRule
from glassbox.runtime.eval_recommendation_matching_common import PathRuleMatch
from glassbox.runtime.eval_recommendation_matching_common import RecommendationReasonMap
from glassbox.runtime.eval_recommendation_matching_common import RuleTargetMatches
from glassbox.runtime.eval_recommendation_matching_common import add_reason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalProfileDefinition


def match_rules(
    normalized_paths: list[str],
    rules: list[EvalImpactRule],
) -> list[PathRuleMatch]:
    matches: list[PathRuleMatch] = []
    for normalized_path in normalized_paths:
        pure_path = PurePosixPath(normalized_path)
        for rule in rules:
            if any(
                pure_path.match(path_glob) or fnmatch(normalized_path, path_glob)
                for path_glob in rule.path_globs
            ):
                matches.append(PathRuleMatch(rule=rule, matched_path=normalized_path))
    return matches


def add_direct_path_recommendations(
    *,
    normalized_paths: list[str],
    case_paths: dict[str, EvalCase],
    profiles: list[EvalProfileDefinition],
    case_reasons: RecommendationReasonMap,
    profile_reasons: RecommendationReasonMap,
) -> tuple[set[str], bool, list[str]]:
    matched_paths: set[str] = set()
    warnings: list[str] = []
    coverage_audit_recommended = False
    profiles_path = str(Path("evals") / "profiles.json")

    for touched_path in normalized_paths:
        if touched_path in case_paths:
            case = case_paths[touched_path]
            add_reason(
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
                add_reason(
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
    rule_matches: list[PathRuleMatch],
    cases_by_id: dict[str, EvalCase],
    profiles_by_id: dict[str, EvalProfileDefinition],
    case_reasons: RecommendationReasonMap,
    profile_reasons: RecommendationReasonMap,
) -> tuple[RuleTargetMatches, RuleTargetMatches]:
    matched_owners: RuleTargetMatches = {}
    matched_capabilities: RuleTargetMatches = {}

    for match in rule_matches:
        rule = match.rule
        for case_id in rule.case_ids:
            if case_id in cases_by_id:
                add_reason(
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
            add_reason(
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
