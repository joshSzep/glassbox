"""Deterministic verification readiness model for reviewable changesets."""

from collections.abc import Iterable
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetVerificationState
from glassbox.core import TaskVerificationId
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import TaskVerificationStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanSource
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.workspace_profile import WorkspaceProfile


class ChangesetVerificationRequirement(BaseModel):
    """One check or evidence gap that contributes to changeset readiness."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1, max_length=200)
    state: ChangesetVerificationState
    check_name: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    source: VerificationPlanSource | None = None
    kind: VerificationCheckKind | None = None
    command: list[str] = Field(default_factory=list, max_length=64)
    changed_paths: list[str] = Field(default_factory=list, max_length=100)
    verification_id: TaskVerificationId | None = None
    blocking: bool = True
    evidence_summary: str | None = Field(default=None, max_length=2000)
    safe_next_actions: list[str] = Field(default_factory=list, max_length=10)


class ChangesetVerificationReadiness(BaseModel):
    """Aggregate readiness posture for one local changeset."""

    model_config = ConfigDict(extra="forbid")

    state: ChangesetVerificationState
    summary: str = Field(min_length=1, max_length=4000)
    requirements: list[ChangesetVerificationRequirement] = Field(default_factory=list)
    stale_count: int = Field(default=0, ge=0)
    missing_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    accepted_risk_count: int = Field(default=0, ge=0)
    safe_next_actions: list[str] = Field(default_factory=list, max_length=20)
    non_claims: list[str] = Field(default_factory=list, max_length=20)


def derive_changeset_verification_readiness(
    *,
    inventory: ChangeInventoryArtifact | None,
    inventory_freshness: ChangesetInventoryFreshness,
    inventory_sequence: int | None = None,
    task_ledger: Sequence[TaskVerificationLedgerRecord] = (),
    eval_recommendation: EvalRecommendationReport | None = None,
    workspace_profile: WorkspaceProfile | None = None,
    command_evidence: Sequence[str] = (),
) -> ChangesetVerificationReadiness:
    """Derive review-time verification posture from retained local evidence."""

    requirements: list[ChangesetVerificationRequirement] = []
    safe_next_actions: list[str] = []
    if inventory is None:
        requirements.append(
            ChangesetVerificationRequirement(
                requirement_id="inventory-required",
                state=ChangesetVerificationState.MISSING,
                check_name="Change inventory",
                reason="verification readiness requires a current change inventory",
                source=VerificationPlanSource.CHANGED_PATHS,
                safe_next_actions=["glassbox changeset refresh CHANGESET --cwd ."],
            )
        )
    elif inventory.summary.changed_path_count == 0:
        requirements.append(
            ChangesetVerificationRequirement(
                requirement_id="no-changed-paths",
                state=ChangesetVerificationState.NOT_APPLICABLE,
                check_name="Changed-path verification",
                reason="no changed paths are present in the latest inventory",
                source=VerificationPlanSource.CHANGED_PATHS,
                blocking=False,
            )
        )
    else:
        safe_next_actions.append(_eval_recommend_command(inventory))
        if inventory_freshness in {
            ChangesetInventoryFreshness.STALE,
            ChangesetInventoryFreshness.SUPERSEDED,
        }:
            requirements.append(
                ChangesetVerificationRequirement(
                    requirement_id="inventory-stale",
                    state=ChangesetVerificationState.STALE,
                    check_name="Inventory freshness",
                    reason=(
                        "changed-path inventory is stale; verification cannot be "
                        "treated as fresh until inventory is refreshed"
                    ),
                    source=VerificationPlanSource.CHANGED_PATHS,
                    changed_paths=_inventory_paths(inventory),
                    safe_next_actions=["glassbox changeset refresh CHANGESET --cwd ."],
                )
            )
        elif inventory_freshness == ChangesetInventoryFreshness.UNKNOWN:
            requirements.append(
                ChangesetVerificationRequirement(
                    requirement_id="inventory-freshness-unknown",
                    state=ChangesetVerificationState.MISSING,
                    check_name="Inventory freshness",
                    reason=(
                        "changed-path inventory freshness is unknown; refresh before "
                        "trusting verification posture"
                    ),
                    source=VerificationPlanSource.CHANGED_PATHS,
                    changed_paths=_inventory_paths(inventory),
                    safe_next_actions=["glassbox changeset refresh CHANGESET --cwd ."],
                )
            )
        requirements.extend(
            _requirements_from_eval_recommendation(
                eval_recommendation,
                task_ledger=task_ledger,
                command_evidence=command_evidence,
                inventory_sequence=inventory_sequence,
            )
        )
        if (
            workspace_profile is not None
            and workspace_profile.verification.eval_profile
        ):
            requirements.append(
                _workspace_profile_requirement(
                    workspace_profile.verification.eval_profile,
                    task_ledger=task_ledger,
                    inventory_sequence=inventory_sequence,
                )
            )
        if not _has_non_inventory_requirement(requirements):
            requirements.append(
                _changed_path_requirement(
                    inventory,
                    task_ledger=task_ledger,
                    command_evidence=command_evidence,
                    inventory_sequence=inventory_sequence,
                )
            )

    readiness_state = _aggregate_state(requirements)
    safe_next_actions.extend(
        action
        for requirement in requirements
        for action in requirement.safe_next_actions
    )
    return ChangesetVerificationReadiness(
        state=readiness_state,
        summary=_summary(readiness_state, requirements),
        requirements=requirements,
        stale_count=_count(requirements, ChangesetVerificationState.STALE),
        missing_count=_count(requirements, ChangesetVerificationState.MISSING),
        failed_count=_count(requirements, ChangesetVerificationState.FAILED),
        accepted_risk_count=sum(
            1
            for requirement in requirements
            if requirement.state == ChangesetVerificationState.ACCEPTED_WITH_RISK
        ),
        safe_next_actions=list(dict.fromkeys(safe_next_actions)),
        non_claims=[
            "verification readiness is advisory review posture, not proof",
            "old passing checks are not fresh when inventory is stale",
            "recommended commands are previews; this model does not run them",
        ],
    )


def _requirements_from_eval_recommendation(
    recommendation: EvalRecommendationReport | None,
    *,
    task_ledger: Sequence[TaskVerificationLedgerRecord],
    command_evidence: Sequence[str],
    inventory_sequence: int | None,
) -> list[ChangesetVerificationRequirement]:
    if recommendation is None:
        return []
    requirements: list[ChangesetVerificationRequirement] = []
    for command in recommendation.suggested_commands:
        command_parts = _command_parts(command)
        requirements.append(
            _requirement_for_command(
                requirement_id=f"eval-command:{command}",
                check_name="Eval recommendation",
                command=command_parts,
                source=VerificationPlanSource.EVAL_RECOMMENDATION,
                kind=VerificationCheckKind.EVAL,
                reason="eval recommendation selected this command for changed paths",
                task_ledger=task_ledger,
                command_evidence=command_evidence,
                changed_paths=recommendation.touched_paths,
                inventory_sequence=inventory_sequence,
            )
        )
    for recipe in recommendation.recipes:
        for command in recipe.commands:
            command_parts = _command_parts(command)
            requirements.append(
                _requirement_for_command(
                    requirement_id=f"recipe:{recipe.recipe_id}:{command}",
                    check_name=recipe.title,
                    command=command_parts,
                    source=VerificationPlanSource.EVAL_RECOMMENDATION,
                    kind=VerificationCheckKind.COMMAND,
                    reason=(
                        "verification recipe matched "
                        f"{len(recipe.matched_paths)} changed path(s)"
                    ),
                    changed_paths=recipe.matched_paths,
                    task_ledger=task_ledger,
                    command_evidence=command_evidence,
                    inventory_sequence=inventory_sequence,
                )
            )
    for profile in recommendation.profiles:
        requirements.append(
            _requirement_for_eval_profile(
                profile.profile_id,
                check_name=f"Eval profile {profile.profile_id}",
                source=VerificationPlanSource.EVAL_RECOMMENDATION,
                reason="eval recommendation selected this profile",
                task_ledger=task_ledger,
                inventory_sequence=inventory_sequence,
            )
        )
    return requirements


def _workspace_profile_requirement(
    profile_id: str,
    *,
    task_ledger: Sequence[TaskVerificationLedgerRecord],
    inventory_sequence: int | None,
) -> ChangesetVerificationRequirement:
    return _requirement_for_eval_profile(
        profile_id,
        check_name=f"Workspace profile eval {profile_id}",
        source=VerificationPlanSource.WORKSPACE_PROFILE,
        reason="workspace profile declares a default eval profile",
        task_ledger=task_ledger,
        inventory_sequence=inventory_sequence,
    )


def _changed_path_requirement(
    inventory: ChangeInventoryArtifact,
    *,
    task_ledger: Sequence[TaskVerificationLedgerRecord],
    command_evidence: Sequence[str],
    inventory_sequence: int | None,
) -> ChangesetVerificationRequirement:
    paths = _inventory_paths(inventory)
    matching = _latest_path_ledger_entry(task_ledger, paths)
    if matching is not None:
        return _requirement_from_ledger(
            matching,
            requirement_id="changed-path-ledger",
            reason="task verification ledger targets changed inventory paths",
            inventory_sequence=inventory_sequence,
            current_changed_paths=paths,
        )
    command = _eval_recommend_command(inventory)
    state = (
        ChangesetVerificationState.PLANNED
        if command in set(command_evidence)
        else ChangesetVerificationState.MISSING
    )
    risk = inventory.summary.risk_level
    reason = (
        f"{risk} risk changed paths need verification evidence"
        if risk in {"high", "medium"}
        else "changed paths have no retained verification evidence"
    )
    return ChangesetVerificationRequirement(
        requirement_id="changed-path-coverage",
        state=state,
        check_name="Changed-path verification coverage",
        reason=reason,
        source=VerificationPlanSource.CHANGED_PATHS,
        kind=VerificationCheckKind.CUSTOM,
        command=_command_parts(command),
        changed_paths=paths,
        safe_next_actions=[command],
    )


def _requirement_for_command(
    *,
    requirement_id: str,
    check_name: str,
    command: list[str],
    source: VerificationPlanSource,
    kind: VerificationCheckKind,
    reason: str,
    task_ledger: Sequence[TaskVerificationLedgerRecord],
    command_evidence: Sequence[str],
    changed_paths: Sequence[str] = (),
    inventory_sequence: int | None,
) -> ChangesetVerificationRequirement:
    matching = _latest_command_ledger_entry(task_ledger, command)
    if matching is not None:
        return _requirement_from_ledger(
            matching,
            requirement_id=requirement_id,
            reason=reason,
            inventory_sequence=inventory_sequence,
            current_changed_paths=changed_paths,
        )
    command_text = " ".join(command)
    state = (
        ChangesetVerificationState.PLANNED
        if command_text in set(command_evidence)
        else ChangesetVerificationState.MISSING
    )
    return ChangesetVerificationRequirement(
        requirement_id=requirement_id,
        state=state,
        check_name=check_name,
        reason=reason,
        source=source,
        kind=kind,
        command=command,
        changed_paths=list(changed_paths),
        safe_next_actions=[command_text],
    )


def _requirement_for_eval_profile(
    profile_id: str,
    *,
    check_name: str,
    source: VerificationPlanSource,
    reason: str,
    task_ledger: Sequence[TaskVerificationLedgerRecord],
    inventory_sequence: int | None,
) -> ChangesetVerificationRequirement:
    matching = _latest_profile_ledger_entry(task_ledger, profile_id)
    if matching is not None:
        return _requirement_from_ledger(
            matching,
            requirement_id=f"eval-profile:{profile_id}",
            reason=reason,
            inventory_sequence=inventory_sequence,
            current_changed_paths=[],
        )
    command = ["uv", "run", "glassbox", "eval", "run", profile_id, "--cwd", "."]
    return ChangesetVerificationRequirement(
        requirement_id=f"eval-profile:{profile_id}",
        state=ChangesetVerificationState.MISSING,
        check_name=check_name,
        reason=reason,
        source=source,
        kind=VerificationCheckKind.EVAL,
        command=command,
        safe_next_actions=[" ".join(command)],
    )


def _requirement_from_ledger(
    entry: TaskVerificationLedgerRecord,
    *,
    requirement_id: str,
    reason: str,
    inventory_sequence: int | None,
    current_changed_paths: Sequence[str],
) -> ChangesetVerificationRequirement:
    state = _state_for_ledger_status(entry.status)
    stale_reason = _stale_reason(
        entry,
        inventory_sequence=inventory_sequence,
        current_changed_paths=current_changed_paths,
    )
    if state == ChangesetVerificationState.PASSED and stale_reason is not None:
        state = ChangesetVerificationState.STALE
        reason = stale_reason
    return ChangesetVerificationRequirement(
        requirement_id=requirement_id,
        state=state,
        check_name=entry.check_name,
        reason=reason,
        source=entry.source,
        kind=entry.kind,
        command=[str(part) for part in entry.command],
        changed_paths=[_path_to_string(path) for path in entry.changed_paths],
        verification_id=entry.verification_id,
        blocking=entry.blocking,
        evidence_summary=entry.summary or entry.latest_failed_summary,
        safe_next_actions=[]
        if state == ChangesetVerificationState.PASSED
        else ["inspect retained verification output before retrying"],
    )


def _stale_reason(
    entry: TaskVerificationLedgerRecord,
    *,
    inventory_sequence: int | None,
    current_changed_paths: Sequence[str],
) -> str | None:
    if inventory_sequence is None or not current_changed_paths:
        return None
    evidence_sequence = entry.last_success_sequence or entry.last_sequence
    if evidence_sequence >= inventory_sequence:
        return None
    changed_path_set = set(current_changed_paths)
    ledger_paths = {_path_to_string(path) for path in entry.changed_paths}
    if not changed_path_set.intersection(ledger_paths):
        return None
    return (
        "passed verification predates the latest inventory refresh for overlapping "
        "changed paths"
    )


def _state_for_ledger_status(
    status: TaskVerificationStatus,
) -> ChangesetVerificationState:
    if status == TaskVerificationStatus.PLANNED:
        return ChangesetVerificationState.PLANNED
    if status == TaskVerificationStatus.RUNNING:
        return ChangesetVerificationState.RUNNING
    if status == TaskVerificationStatus.PASSED:
        return ChangesetVerificationState.PASSED
    if status in {TaskVerificationStatus.FAILED, TaskVerificationStatus.CANCELLED}:
        return ChangesetVerificationState.FAILED
    if status == TaskVerificationStatus.SKIPPED:
        return ChangesetVerificationState.SKIPPED
    if status == TaskVerificationStatus.ACCEPTED_WITH_RISK:
        return ChangesetVerificationState.ACCEPTED_WITH_RISK
    return ChangesetVerificationState.MISSING


def _aggregate_state(
    requirements: Sequence[ChangesetVerificationRequirement],
) -> ChangesetVerificationState:
    if not requirements:
        return ChangesetVerificationState.NOT_APPLICABLE
    precedence = (
        ChangesetVerificationState.FAILED,
        ChangesetVerificationState.STALE,
        ChangesetVerificationState.RUNNING,
        ChangesetVerificationState.MISSING,
        ChangesetVerificationState.PLANNED,
        ChangesetVerificationState.ACCEPTED_WITH_RISK,
        ChangesetVerificationState.SKIPPED,
    )
    states = {requirement.state for requirement in requirements if requirement.blocking}
    for state in precedence:
        if state in states:
            return state
    if all(
        requirement.state == ChangesetVerificationState.NOT_APPLICABLE
        for requirement in requirements
    ):
        return ChangesetVerificationState.NOT_APPLICABLE
    return ChangesetVerificationState.PASSED


def _summary(
    state: ChangesetVerificationState,
    requirements: Sequence[ChangesetVerificationRequirement],
) -> str:
    if state == ChangesetVerificationState.PASSED:
        return "fresh retained verification evidence covers current requirements"
    if state == ChangesetVerificationState.NOT_APPLICABLE:
        return "no verification command is applicable to the current inventory"
    counts = {
        item.value: _count(requirements, item)
        for item in ChangesetVerificationState
        if _count(requirements, item) > 0
    }
    detail = ", ".join(f"{value} {key}" for key, value in sorted(counts.items()))
    return f"verification readiness is {state.value}: {detail}"


def _latest_command_ledger_entry(
    ledger: Sequence[TaskVerificationLedgerRecord],
    command: Sequence[str],
) -> TaskVerificationLedgerRecord | None:
    normalized = tuple(command)
    return _latest(
        entry
        for entry in ledger
        if tuple(str(part) for part in entry.command) == normalized
    )


def _latest_profile_ledger_entry(
    ledger: Sequence[TaskVerificationLedgerRecord],
    profile_id: str,
) -> TaskVerificationLedgerRecord | None:
    return _latest(entry for entry in ledger if entry.eval_profile_id == profile_id)


def _latest_path_ledger_entry(
    ledger: Sequence[TaskVerificationLedgerRecord],
    paths: Sequence[str],
) -> TaskVerificationLedgerRecord | None:
    path_set = set(paths)
    return _latest(
        entry
        for entry in ledger
        if path_set.intersection(
            {_path_to_string(path) for path in entry.changed_paths}
        )
    )


def _latest(
    entries: Iterable[TaskVerificationLedgerRecord],
) -> TaskVerificationLedgerRecord | None:
    return max(entries, key=lambda entry: entry.last_sequence, default=None)


def _count(
    requirements: Sequence[ChangesetVerificationRequirement],
    state: ChangesetVerificationState,
) -> int:
    return sum(1 for requirement in requirements if requirement.state == state)


def _inventory_paths(inventory: ChangeInventoryArtifact) -> list[str]:
    return [entry.path for entry in inventory.paths[:100]]


def _has_non_inventory_requirement(
    requirements: Sequence[ChangesetVerificationRequirement],
) -> bool:
    return any(
        not requirement.requirement_id.startswith("inventory-")
        for requirement in requirements
    )


def _eval_recommend_command(inventory: ChangeInventoryArtifact) -> str:
    paths = _inventory_paths(inventory)
    if not paths:
        return "glassbox eval recommend --cwd ."
    return "glassbox eval recommend " + " ".join(paths[:20]) + " --cwd ."


def _command_parts(command: str) -> list[str]:
    return [part for part in command.split() if part]


def _path_to_string(path: Path) -> str:
    return path.as_posix()


__all__ = [
    "ChangesetVerificationReadiness",
    "ChangesetVerificationRequirement",
    "derive_changeset_verification_readiness",
]
