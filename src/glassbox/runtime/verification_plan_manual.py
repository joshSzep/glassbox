"""Manual-only verification-plan entries for advisory evidence posture."""

from pathlib import Path

from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanLifecycleState
from glassbox.core import VerificationPlanSource
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.verification_plan_identity import stable_verification_id


def build_manual_evidence_entries(
    changed_paths: list[str],
) -> list[VerificationPlanEntry]:
    """Build manual-only evidence rows that remain advisory, not passing claims."""

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


def build_manual_only_profile_entry(
    profile: EvalProfileRecommendation,
    *,
    changed_paths: list[str],
) -> VerificationPlanEntry:
    """Build an advisory profile row that requires explicit operator selection."""

    return VerificationPlanEntry(
        verification_id=stable_verification_id(f"manual-profile:{profile.profile_id}"),
        check_name=f"Advisory profile {profile.profile_id}",
        kind=VerificationCheckKind.CUSTOM,
        lifecycle_state=VerificationPlanLifecycleState.MANUAL_ONLY,
        target=NextActionTarget(
            kind=NextActionTargetKind.VERIFICATION,
            target_id=profile.profile_id,
            label=profile.title,
        ),
        source=VerificationPlanSource.MANUAL_EVIDENCE,
        rationale=(
            f"{profile.track} evidence is advisory and requires explicit operator "
            "selection before it can shape verification posture."
        ),
        selection_rationale="advisory evidence stays separate from command checks",
        blocking=False,
        changed_paths=[Path(path) for path in profile.matched_paths or changed_paths],
        manual_evidence_required=True,
        execution_requires_approval=True,
    )


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


def _has_ui_path(paths: list[str]) -> bool:
    return any(
        path.startswith(("frontend/", "src/glassbox/web/"))
        or path.endswith((".tsx", ".jsx", ".css"))
        for path in paths
    )


__all__ = [
    "build_manual_evidence_entries",
    "build_manual_only_profile_entry",
]
