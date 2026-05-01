"""Compatibility facade for eval recommendation matching helpers."""

from glassbox.runtime.eval_recommendation_case_expansion import (
    add_capability_derived_case_recommendations,
)
from glassbox.runtime.eval_recommendation_case_expansion import (
    add_owner_derived_case_recommendations,
)
from glassbox.runtime.eval_recommendation_case_expansion import build_impacted_stages
from glassbox.runtime.eval_recommendation_matching_common import PathRuleMatch
from glassbox.runtime.eval_recommendation_matching_common import RecommendationReasonMap
from glassbox.runtime.eval_recommendation_matching_common import RuleTargetMatches
from glassbox.runtime.eval_recommendation_path_matching import (
    add_direct_path_recommendations,
)
from glassbox.runtime.eval_recommendation_path_matching import (
    add_rule_match_recommendations,
)
from glassbox.runtime.eval_recommendation_path_matching import match_rules
from glassbox.runtime.eval_recommendation_profile_expansion import (
    add_fallback_profile_recommendations,
)
from glassbox.runtime.eval_recommendation_profile_expansion import (
    add_stage_derived_profile_recommendations,
)

__all__ = [
    "PathRuleMatch",
    "RecommendationReasonMap",
    "RuleTargetMatches",
    "add_capability_derived_case_recommendations",
    "add_direct_path_recommendations",
    "add_fallback_profile_recommendations",
    "add_owner_derived_case_recommendations",
    "add_rule_match_recommendations",
    "add_stage_derived_profile_recommendations",
    "build_impacted_stages",
    "match_rules",
]
