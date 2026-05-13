"""Build v16 verification plan entries from local recommendation inputs."""

from pathlib import Path

from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanLifecycleState
from glassbox.core import VerificationPlanSource
from glassbox.runtime.changeset_models import ChangesetVerificationSkippedCheckPreview
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.verification_plan_entries import build_verification_entry
from glassbox.runtime.verification_plan_evals import build_eval_verification_entries
from glassbox.runtime.verification_plan_identity import VerificationPlanEntryCoalescer
from glassbox.runtime.verification_plan_identity import stable_verification_id
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
        for requirement in readiness.requirements:
            if not requirement.command:
                continue
            add(
                build_verification_entry(
                    seed=f"readiness:{requirement.requirement_id}",
                    check_name=requirement.check_name,
                    kind=_readiness_kind(requirement.kind),
                    command=requirement.command,
                    source=requirement.source or VerificationPlanSource.CHANGED_PATHS,
                    target_id=requirement.requirement_id,
                    target_label=requirement.check_name,
                    rationale=requirement.reason,
                    selection_rationale="changeset readiness requirement",
                    blocking=requirement.blocking,
                    changed_paths=requirement.changed_paths or changed_paths,
                    stale_reasons=(
                        [requirement.reason]
                        if requirement.state.value in {"stale", "missing"}
                        else []
                    ),
                    lifecycle_state=(
                        VerificationPlanLifecycleState.STALE
                        if requirement.state.value == "stale"
                        else VerificationPlanLifecycleState.PROPOSED
                    ),
                    evidence_references=_requirement_evidence_refs(requirement),
                    verification_id=requirement.verification_id,
                )
            )

    for entry in _manual_evidence_entries(changed_paths):
        add(entry)

    return entries, skipped


def _manual_evidence_entries(changed_paths: list[str]) -> list[VerificationPlanEntry]:
    if not changed_paths:
        return []
    entries = [
        _manual_entry(
            seed="manual-evidence",
            check_name="Manual evidence note",
            rationale=(
                "Operators may attach bounded manual evidence for context; it is "
                "not a substitute for retained command verification."
            ),
            changed_paths=changed_paths,
        )
    ]
    if _has_ui_path(changed_paths):
        entries.extend(
            [
                _manual_entry(
                    seed="browser-evidence",
                    check_name="Advisory browser evidence",
                    rationale=(
                        "User-facing paths may need retained browser observation; "
                        "planning does not run a browser check."
                    ),
                    changed_paths=changed_paths,
                ),
                _manual_entry(
                    seed="accessibility-evidence",
                    check_name="Advisory accessibility evidence",
                    rationale=(
                        "User-facing paths may need keyboard or screen-reader "
                        "notes; planning does not claim accessibility passed."
                    ),
                    changed_paths=changed_paths,
                ),
            ]
        )
    return entries


def _manual_entry(
    *,
    seed: str,
    check_name: str,
    rationale: str,
    changed_paths: list[str],
) -> VerificationPlanEntry:
    return VerificationPlanEntry(
        verification_id=stable_verification_id(seed + ":" + "|".join(changed_paths)),
        check_name=check_name,
        kind=VerificationCheckKind.CUSTOM,
        lifecycle_state=VerificationPlanLifecycleState.MANUAL_ONLY,
        target=NextActionTarget(
            kind=NextActionTargetKind.VERIFICATION,
            target_id=seed,
            label=check_name,
        ),
        source=VerificationPlanSource.MANUAL_EVIDENCE,
        rationale=rationale,
        selection_rationale="advisory manual evidence remains separate from passes",
        blocking=False,
        changed_paths=[Path(path) for path in changed_paths],
        manual_evidence_required=True,
        execution_requires_approval=True,
    )


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


def _readiness_kind(kind: VerificationCheckKind | None) -> VerificationCheckKind:
    if kind is None or kind == VerificationCheckKind.EVAL:
        return VerificationCheckKind.COMMAND
    return kind


def _requirement_evidence_refs(requirement) -> list[NextActionEvidenceRef]:
    refs: list[NextActionEvidenceRef] = []
    if requirement.verification_id is not None:
        refs.append(
            NextActionEvidenceRef(
                kind=NextActionEvidenceKind.VERIFICATION,
                ref_id=str(requirement.verification_id),
                summary=requirement.evidence_summary or requirement.reason,
            )
        )
    if requirement.artifact_id is not None:
        refs.append(
            NextActionEvidenceRef(
                kind=NextActionEvidenceKind.ARTIFACT,
                ref_id=str(requirement.artifact_id),
                summary=requirement.evidence_summary or requirement.reason,
            )
        )
    return refs


def _has_ui_path(paths: list[str]) -> bool:
    return any(
        path.startswith(("frontend/", "src/glassbox/web/"))
        or path.endswith((".tsx", ".jsx", ".css"))
        for path in paths
    )


__all__ = [
    "MAX_VERIFICATION_PLAN_ENTRIES",
    "MAX_VERIFICATION_PLAN_SKIPPED_CHECKS",
    "build_verification_plan_entries",
]
