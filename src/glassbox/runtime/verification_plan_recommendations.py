"""Verification-plan entries derived from path test-target recommendations."""

from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.verification_plan_entries import build_verification_entry
from glassbox.runtime.verification_plan_entries import command_parts
from glassbox.runtime.verification_plan_entries import join_reasons
from glassbox.runtime.verification_plan_entries import lifecycle_for_freshness
from glassbox.runtime.verification_plan_entries import stale_reasons


def build_test_target_verification_entries(
    recommendation: EvalRecommendationReport,
    *,
    changed_paths: list[str],
) -> list[VerificationPlanEntry]:
    """Build command-backed entries for recommended test targets."""

    entries: list[VerificationPlanEntry] = []
    for target in recommendation.test_targets:
        if not target.command:
            continue
        entries.append(
            build_verification_entry(
                seed=f"test-target:{target.target_id}:{target.command}",
                check_name=target.title,
                kind=VerificationCheckKind.TEST,
                command=command_parts(target.command),
                source=_source_for_test_target(target.source),
                target_id=target.target_id,
                target_label=target.title,
                rationale=join_reasons(
                    target.reasons,
                    fallback="Repository intelligence mapped this test target.",
                ),
                selection_rationale=(
                    f"{target.confidence} confidence from {target.source}"
                ),
                changed_paths=target.matched_paths or changed_paths,
                stale_reasons=stale_reasons(target.freshness),
                lifecycle_state=lifecycle_for_freshness(target.freshness),
            )
        )
    return entries


def _source_for_test_target(source: str) -> VerificationPlanSource:
    if source in {"repository-intelligence", "topology", "recipe"}:
        return VerificationPlanSource.REPOSITORY_INTELLIGENCE
    return VerificationPlanSource.CHANGED_PATHS


__all__ = ["build_test_target_verification_entries"]
