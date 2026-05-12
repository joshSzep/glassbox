"""Build v16 verification plan entries from local recommendation inputs."""

from collections.abc import Iterable
from pathlib import Path
from uuid import NAMESPACE_URL
from uuid import uuid5

from glassbox.core import NextActionCommandRecipe
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import TaskVerificationId
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanLifecycleState
from glassbox.core import VerificationPlanSource
from glassbox.runtime.changeset_models import ChangesetVerificationSkippedCheckPreview
from glassbox.runtime.changeset_verification_preview import is_safe_verification_command
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.eval_recommendation_models import EvalProfileRecommendation
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_recommendation_models import (
    EvalVerificationRecipeRecommendation,
)
from glassbox.runtime.eval_recommendation_models import PathVerificationFreshness

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
    seen: set[str] = set()
    entry_limit_recorded = False
    skipped_limit_recorded = False

    def add(entry: VerificationPlanEntry) -> None:
        nonlocal entry_limit_recorded
        key = _entry_key(entry)
        if key in seen:
            return
        if len(entries) >= MAX_VERIFICATION_PLAN_ENTRIES:
            if not entry_limit_recorded:
                add_skipped(
                    _plan_entry_limit_skipped(
                        changed_paths,
                        limit=MAX_VERIFICATION_PLAN_ENTRIES,
                    )
                )
                entry_limit_recorded = True
            return
        seen.add(key)
        entries.append(entry)

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
        for target in recommendation.test_targets:
            if not target.command:
                continue
            add(
                _entry(
                    seed=f"test-target:{target.target_id}:{target.command}",
                    check_name=target.title,
                    kind=VerificationCheckKind.TEST,
                    command=_command_parts(target.command),
                    source=_source_for_test_target(target.source),
                    target_id=target.target_id,
                    target_label=target.title,
                    rationale=_join_reasons(
                        target.reasons,
                        fallback="Repository intelligence mapped this test target.",
                    ),
                    selection_rationale=(
                        f"{target.confidence} confidence from {target.source}"
                    ),
                    changed_paths=target.matched_paths or changed_paths,
                    stale_reasons=_stale_reasons(target.freshness),
                    lifecycle_state=_lifecycle_for_freshness(target.freshness),
                )
            )
        for recipe in recommendation.recipes:
            for command in recipe.commands:
                if not is_safe_verification_command(command):
                    add_skipped(
                        _skipped(
                            target_id=recipe.recipe_id,
                            target_kind="command-recipe",
                            reason="unsafe-command",
                            explanation=(
                                "verification planning filters publication, upload, "
                                "push, deploy, release, and destructive commands"
                            ),
                            matched_paths=recipe.matched_paths,
                        )
                    )
                    continue
                add(
                    _entry_for_recipe(
                        recipe,
                        command,
                        changed_paths=changed_paths,
                    )
                )
        for profile in recommendation.profiles:
            if profile.track != "deterministic":
                add_skipped(
                    _skipped(
                        target_id=profile.profile_id,
                        target_kind="eval-profile",
                        reason="operator-selection-required",
                        explanation=(
                            f"{profile.track} profiles remain advisory until the "
                            "operator explicitly selects them"
                        ),
                        matched_paths=profile.matched_paths,
                        safe_next_actions=profile.safe_next_commands,
                    )
                )
                add(
                    _manual_only_entry_for_profile(profile, changed_paths=changed_paths)
                )
                continue
            command = (
                profile.safe_next_commands[0]
                if profile.safe_next_commands
                else f"uv run glassbox eval run --profile {profile.profile_id} --cwd ."
            )
            add(
                _entry(
                    seed=f"eval-profile:{profile.profile_id}:{command}",
                    check_name=f"Eval profile {profile.profile_id}",
                    kind=VerificationCheckKind.EVAL,
                    command=_command_parts(command),
                    source=VerificationPlanSource.EVAL_RECOMMENDATION,
                    target_id=profile.profile_id,
                    target_label=profile.title,
                    rationale=_join_reasons(
                        [reason.summary for reason in profile.reasons],
                        fallback="Eval recommendation selected this profile.",
                    ),
                    selection_rationale=(
                        f"{profile.confidence} confidence for "
                        f"{profile.verification_stage} verification"
                    ),
                    blocking=profile.blocking,
                    changed_paths=profile.matched_paths or changed_paths,
                    eval_profile_id=profile.profile_id,
                    release_surfaces=[profile.verification_stage],
                )
            )
        for case in recommendation.cases:
            command = f"uv run glassbox eval run {case.case_id} --cwd ."
            add(
                _entry(
                    seed=f"eval-case:{case.case_id}:{command}",
                    check_name=f"Eval case {case.case_id}",
                    kind=VerificationCheckKind.EVAL,
                    command=_command_parts(command),
                    source=VerificationPlanSource.EVAL_RECOMMENDATION,
                    target_id=case.case_id,
                    target_label=case.title,
                    rationale=_join_reasons(
                        [reason.summary for reason in case.reasons],
                        fallback="Eval recommendation selected this case.",
                    ),
                    selection_rationale=f"{case.confidence} confidence eval case",
                    changed_paths=case.matched_paths or changed_paths,
                    eval_case_id=case.case_id,
                )
            )
        for surface in recommendation.release_surfaces:
            if not surface.impacted:
                continue
            for command in surface.release_gate_commands:
                if not is_safe_verification_command(command):
                    continue
                add(
                    _entry(
                        seed=f"release:{surface.verification_stage}:{command}",
                        check_name=f"{surface.verification_stage} release gate",
                        kind=VerificationCheckKind.PACKAGE,
                        command=_command_parts(command),
                        source=VerificationPlanSource.RELEASE_GATE,
                        target_id=f"release:{surface.verification_stage}",
                        target_label=f"{surface.verification_stage} release surface",
                        rationale=(
                            "Changed paths affect this release verification surface."
                        ),
                        selection_rationale="release surface impact",
                        changed_paths=changed_paths,
                        release_surfaces=[surface.verification_stage],
                    )
                )

    if readiness is not None:
        for requirement in readiness.requirements:
            if not requirement.command:
                continue
            add(
                _entry(
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


def _entry(
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
        verification_id=verification_id or _stable_verification_id(seed),
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


def _entry_for_recipe(
    recipe: EvalVerificationRecipeRecommendation,
    command: str,
    *,
    changed_paths: list[str],
) -> VerificationPlanEntry:
    return _entry(
        seed=f"recipe:{recipe.recipe_id}:{command}",
        check_name=recipe.title,
        kind=VerificationCheckKind.COMMAND,
        command=_command_parts(command),
        source=(
            VerificationPlanSource.REPOSITORY_INTELLIGENCE
            if recipe.source == "repository-intelligence"
            else VerificationPlanSource.COMMAND_RECIPE
        ),
        target_id=recipe.recipe_id,
        target_label=recipe.title,
        rationale=recipe.notes
        or f"Verification recipe matched {len(recipe.matched_paths)} changed path(s).",
        selection_rationale=(
            f"{recipe.confidence} confidence recipe from {recipe.source}"
        ),
        changed_paths=recipe.matched_paths or changed_paths,
        stale_reasons=_stale_reasons(recipe.freshness),
        lifecycle_state=_lifecycle_for_freshness(recipe.freshness),
        evidence_references=[
            NextActionEvidenceRef(
                kind=NextActionEvidenceKind.REPOSITORY_INTELLIGENCE,
                ref_id=recipe.recipe_id,
                summary=f"Verification recipe {recipe.recipe_id} matched paths.",
                freshness=recipe.freshness,
            )
        ],
    )


def _manual_only_entry_for_profile(
    profile: EvalProfileRecommendation,
    *,
    changed_paths: list[str],
) -> VerificationPlanEntry:
    return VerificationPlanEntry(
        verification_id=_stable_verification_id(f"manual-profile:{profile.profile_id}"),
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
        verification_id=_stable_verification_id(seed + ":" + "|".join(changed_paths)),
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


def _source_for_test_target(source: str) -> VerificationPlanSource:
    if source in {"repository-intelligence", "topology", "recipe"}:
        return VerificationPlanSource.REPOSITORY_INTELLIGENCE
    return VerificationPlanSource.CHANGED_PATHS


def _readiness_kind(kind: VerificationCheckKind | None) -> VerificationCheckKind:
    if kind is None or kind == VerificationCheckKind.EVAL:
        return VerificationCheckKind.COMMAND
    return kind


def _lifecycle_for_freshness(
    freshness: PathVerificationFreshness,
) -> VerificationPlanLifecycleState:
    if freshness in {"stale", "degraded"}:
        return VerificationPlanLifecycleState.STALE
    return VerificationPlanLifecycleState.PROPOSED


def _stale_reasons(freshness: str) -> list[str]:
    if freshness == "stale":
        return ["source evidence is stale"]
    if freshness == "degraded":
        return ["source evidence is degraded"]
    if freshness == "missing":
        return ["source evidence is missing"]
    return []


def _join_reasons(reasons: Iterable[str], *, fallback: str) -> str:
    compact = [reason.strip() for reason in reasons if reason.strip()]
    if not compact:
        return fallback
    return "; ".join(compact)[:2000]


def _command_parts(command: str) -> list[str]:
    return command.split()


def _stable_verification_id(seed: str) -> TaskVerificationId:
    return uuid5(NAMESPACE_URL, f"glassbox:v16-verification-plan:{seed}")


def _entry_key(entry: VerificationPlanEntry) -> str:
    command = " ".join(entry.command)
    target_id = entry.target.target_id if entry.target is not None else ""
    return f"{entry.kind.value}:{target_id}:{command}:{entry.check_name}"


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
