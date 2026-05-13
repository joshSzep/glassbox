"""Shared verification-plan entry construction helpers."""

from collections.abc import Iterable
from pathlib import Path

from glassbox.core import NextActionCommandRecipe
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import TaskVerificationId
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanLifecycleState
from glassbox.core import VerificationPlanSource
from glassbox.runtime.eval_recommendation_models import PathVerificationFreshness
from glassbox.runtime.verification_plan_identity import stable_verification_id


def build_verification_entry(
    *,
    seed: str,
    check_name: str,
    kind: VerificationCheckKind,
    source: VerificationPlanSource,
    target_id: str,
    target_label: str,
    rationale: str,
    command: list[str] | None = None,
    selection_rationale: str | None = None,
    blocking: bool = True,
    changed_paths: list[str] | None = None,
    eval_case_id: str | None = None,
    eval_profile_id: str | None = None,
    release_surfaces: list[str] | None = None,
    stale_reasons: list[str] | None = None,
    lifecycle_state: VerificationPlanLifecycleState = (
        VerificationPlanLifecycleState.PROPOSED
    ),
    evidence_references: list[NextActionEvidenceRef] | None = None,
    verification_id: TaskVerificationId | None = None,
) -> VerificationPlanEntry:
    """Build one executable verification entry from deterministic local inputs."""

    command_parts = command or []
    command_recipe = (
        NextActionCommandRecipe(
            command=command_parts,
            display=" ".join(command_parts),
            purpose=rationale,
            requires_approval=True,
        )
        if command_parts
        else None
    )
    return VerificationPlanEntry(
        verification_id=verification_id or stable_verification_id(seed),
        check_name=check_name,
        kind=kind,
        lifecycle_state=lifecycle_state,
        target=NextActionTarget(
            kind=NextActionTargetKind.VERIFICATION,
            target_id=target_id,
            label=target_label,
        ),
        command=command_parts,
        command_recipe=command_recipe,
        source=source,
        rationale=rationale,
        selection_rationale=selection_rationale,
        blocking=blocking,
        changed_paths=[Path(path) for path in changed_paths or []],
        eval_case_id=eval_case_id,
        eval_profile_id=eval_profile_id,
        release_surfaces=release_surfaces or [],
        evidence_references=evidence_references or [],
        stale_reasons=stale_reasons or [],
        execution_requires_approval=True,
        manual_evidence_required=False,
    )


def command_parts(command: str) -> list[str]:
    """Split display commands into stored command parts."""

    return command.split()


def lifecycle_for_freshness(
    freshness: PathVerificationFreshness,
) -> VerificationPlanLifecycleState:
    """Map recommendation freshness to preview lifecycle posture."""

    if freshness in {"stale", "degraded"}:
        return VerificationPlanLifecycleState.STALE
    return VerificationPlanLifecycleState.PROPOSED


def stale_reasons(freshness: str) -> list[str]:
    """Return stale/degraded/missing copy for source evidence posture."""

    if freshness == "stale":
        return ["source evidence is stale"]
    if freshness == "degraded":
        return ["source evidence is degraded"]
    if freshness == "missing":
        return ["source evidence is missing"]
    return []


def join_reasons(reasons: Iterable[str], *, fallback: str) -> str:
    """Join recommendation reason copy while keeping model bounds stable."""

    compact = [reason.strip() for reason in reasons if reason.strip()]
    if not compact:
        return fallback
    return "; ".join(compact)[:2000]


__all__ = [
    "build_verification_entry",
    "command_parts",
    "join_reasons",
    "lifecycle_for_freshness",
    "stale_reasons",
]
