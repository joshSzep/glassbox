"""Compatibility facade for eval recommendation output helpers."""

from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_long_run_surfaces import (
    build_long_run_surface_recommendations,
)
from glassbox.runtime.eval_recommendation_plans import build_cheapest_next_command
from glassbox.runtime.eval_recommendation_plans import build_fallback_policy_commands
from glassbox.runtime.eval_recommendation_plans import build_suggested_commands
from glassbox.runtime.eval_recommendation_reason_groups import build_reason_groups
from glassbox.runtime.eval_recommendation_recipes import build_recipe_recommendations
from glassbox.runtime.eval_recommendation_release_surfaces import (
    build_release_surface_recommendations,
)
from glassbox.runtime.eval_recommendation_rows import build_case_recommendations
from glassbox.runtime.eval_recommendation_rows import build_profile_recommendations
from glassbox.runtime.eval_recommendation_test_targets import (
    build_test_target_recommendations,
)

__all__ = [
    "build_case_recommendations",
    "build_cheapest_next_command",
    "build_fallback_policy_commands",
    "build_long_run_surface_recommendations",
    "build_profile_recommendations",
    "build_reason_groups",
    "build_recipe_recommendations",
    "build_release_surface_recommendations",
    "build_suggested_commands",
    "build_test_target_recommendations",
    "dedupe_strings",
]
