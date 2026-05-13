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

MAX_VERIFICATION_PLAN_ENTRIES = 50
MAX_VERIFICATION_PLAN_SKIPPED_CHECKS = 50


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
    entry_limit_recorded = False
    skipped_limit_recorded = False

    def add(entry: VerificationPlanEntry) -> None:
        nonlocal entry_limit_recorded
        if (
            coalescer.requires_new_entry(entry)
            and len(entries) >= MAX_VERIFICATION_PLAN_ENTRIES
        ):
            if not entry_limit_recorded:
                add_skipped(
                    _plan_entry_limit_skipped(
                        changed_paths,
                        limit=MAX_VERIFICATION_PLAN_ENTRIES,
                    )
                )
                entry_limit_recorded = True
            return
        coalescer.add(entry)

    def add_skipped(item: ChangesetVerificationSkippedCheckPreview) -> None:
        nonlocal skipped_limit_recorded
        if len(skipped) >= MAX_VERIFICATION_PLAN_SKIPPED_CHECKS:
            if not skipped_limit_recorded and skipped:
                skipped[-1] = _skipped_limit_skipped(
                    changed_paths,
                    limit=MAX_VERIFICATION_PLAN_SKIPPED_CHECKS,
                )
                skipped_limit_recorded = True
            return
        skipped.append(item)

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


def _skipped(
    *,
    target_id: str,
    target_kind: str,
    reason: str,
    explanation: str,
    matched_paths: list[str],
    safe_next_actions: list[str] | None = None,
) -> ChangesetVerificationSkippedCheckPreview:
    return ChangesetVerificationSkippedCheckPreview(
        target_id=target_id,
        target_kind=target_kind,
        reason=reason,
        explanation=explanation,
        matched_paths=matched_paths,
        safe_next_actions=safe_next_actions or [],
    )


def _plan_entry_limit_skipped(
    matched_paths: list[str],
    *,
    limit: int,
) -> ChangesetVerificationSkippedCheckPreview:
    return _skipped(
        target_id="verification-plan-entry-limit",
        target_kind="plan-limit",
        reason="plan-entry-limit",
        explanation=(
            f"Verification plan preview is capped at {limit} entry summaries; "
            "inspect repository recommendations for additional candidate checks."
        ),
        matched_paths=matched_paths[:100],
    )


def _skipped_limit_skipped(
    matched_paths: list[str],
    *,
    limit: int,
) -> ChangesetVerificationSkippedCheckPreview:
    return _skipped(
        target_id="verification-skipped-check-limit",
        target_kind="plan-limit",
        reason="skipped-check-limit",
        explanation=(
            f"Skipped-check preview is capped at {limit} rows; inspect repository "
            "recommendations for additional skipped advisory checks."
        ),
        matched_paths=matched_paths[:100],
    )


__all__ = [
    "MAX_VERIFICATION_PLAN_ENTRIES",
    "MAX_VERIFICATION_PLAN_SKIPPED_CHECKS",
    "build_verification_plan_entries",
]
