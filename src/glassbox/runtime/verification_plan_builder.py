"""Build v16 verification plan entries from local recommendation inputs."""

from glassbox.core import VerificationPlanEntry
from glassbox.runtime.changeset_models import ChangesetVerificationSkippedCheckPreview
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.verification_plan_evals import build_eval_verification_entries
from glassbox.runtime.verification_plan_identity import VerificationPlanEntryCoalescer
from glassbox.runtime.verification_plan_manual import build_manual_evidence_entries
from glassbox.runtime.verification_plan_readiness import (
    build_readiness_verification_entries,
)
from glassbox.runtime.verification_plan_recipes import build_recipe_verification_entries
from glassbox.runtime.verification_plan_recommendations import (
    build_test_target_verification_entries,
)
from glassbox.runtime.verification_plan_skips import (
    MAX_VERIFICATION_PLAN_SKIPPED_CHECKS,
)
from glassbox.runtime.verification_plan_skips import VerificationPlanSkippedCollector
from glassbox.runtime.verification_plan_skips import plan_entry_limit_row

MAX_VERIFICATION_PLAN_ENTRIES = 50


def build_verification_plan_entries(
    *,
    changed_paths: list[str],
    readiness: ChangesetVerificationReadiness | None = None,
    recommendation: EvalRecommendationReport | None = None,
) -> tuple[list[VerificationPlanEntry], list[ChangesetVerificationSkippedCheckPreview]]:
    """Build reviewable plan entries without running or approving commands."""

    entries: list[VerificationPlanEntry] = []
    skipped: list[ChangesetVerificationSkippedCheckPreview] = []
    coalescer = VerificationPlanEntryCoalescer(entries)
    skipped_collector = VerificationPlanSkippedCollector(
        skipped,
        changed_paths=changed_paths,
    )
    entry_limit_recorded = False

    def add(entry: VerificationPlanEntry) -> None:
        nonlocal entry_limit_recorded
        if (
            coalescer.requires_new_entry(entry)
            and len(entries) >= MAX_VERIFICATION_PLAN_ENTRIES
        ):
            if not entry_limit_recorded:
                add_skipped(
                    plan_entry_limit_row(
                        changed_paths,
                        limit=MAX_VERIFICATION_PLAN_ENTRIES,
                    )
                )
                entry_limit_recorded = True
            return
        coalescer.add(entry)

    def add_skipped(item: ChangesetVerificationSkippedCheckPreview) -> None:
        skipped_collector.add(item)

    if recommendation is not None:
        for entry in build_test_target_verification_entries(
            recommendation,
            changed_paths=changed_paths,
        ):
            add(entry)
        recipe_entries, recipe_skipped = build_recipe_verification_entries(
            recommendation,
            changed_paths=changed_paths,
        )
        for skipped_item in recipe_skipped:
            add_skipped(skipped_item)
        for entry in recipe_entries:
            add(entry)
        eval_entries, eval_skipped = build_eval_verification_entries(
            recommendation,
            changed_paths=changed_paths,
        )
        for skipped_item in eval_skipped:
            add_skipped(skipped_item)
        for entry in eval_entries:
            add(entry)

    if readiness is not None:
        for entry in build_readiness_verification_entries(
            readiness,
            changed_paths=changed_paths,
        ):
            add(entry)

    for entry in build_manual_evidence_entries(changed_paths):
        add(entry)

    return entries, skipped


__all__ = [
    "MAX_VERIFICATION_PLAN_ENTRIES",
    "MAX_VERIFICATION_PLAN_SKIPPED_CHECKS",
    "build_verification_plan_entries",
]
