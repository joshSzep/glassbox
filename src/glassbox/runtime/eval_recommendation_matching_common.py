"""Shared types for eval recommendation matching helpers."""

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.runtime.eval_impact_rules import EvalImpactRule
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReason


class PathRuleMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: EvalImpactRule
    matched_path: str


type RecommendationReasonMap = dict[str, list[EvalRecommendationReason]]
type RuleTargetMatches = dict[str, list[PathRuleMatch]]


def add_reason(
    destination: dict[str, list[EvalRecommendationReason]],
    key: str,
    reason: EvalRecommendationReason,
) -> None:
    reasons = destination.setdefault(key, [])
    if any(existing.summary == reason.summary for existing in reasons):
        return
    reasons.append(reason)
