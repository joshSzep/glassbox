"""Owner and capability expansion helpers for eval recommendations."""

from glassbox.runtime.eval_coverage import EvalCapabilityDefinition
from glassbox.runtime.eval_recommendation_matching_common import RecommendationReasonMap
from glassbox.runtime.eval_recommendation_matching_common import RuleTargetMatches
from glassbox.runtime.eval_recommendation_matching_common import add_reason
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason
from glassbox.runtime.evals import EvalCase


def add_owner_derived_case_recommendations(
    *,
    cases: list[EvalCase],
    matched_owners: RuleTargetMatches,
    case_reasons: RecommendationReasonMap,
) -> None:
    for owner, owner_matches in matched_owners.items():
        owner_cases = [case for case in cases if case.release_contract.owner == owner]
        for case in owner_cases:
            for match in owner_matches:
                add_reason(
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
    matched_capabilities: RuleTargetMatches,
    case_reasons: RecommendationReasonMap,
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
                add_reason(
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
    case_reasons: RecommendationReasonMap,
    matched_capabilities: RuleTargetMatches,
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
