"""Stable verification-plan entry identity and coalescing helpers."""

from pathlib import Path
from uuid import NAMESPACE_URL
from uuid import uuid5

from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import TaskVerificationId
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanLifecycleState
from glassbox.core import VerificationPlanSource

_LIFECYCLE_PRIORITY: dict[VerificationPlanLifecycleState, int] = {
    VerificationPlanLifecycleState.FAILED: 90,
    VerificationPlanLifecycleState.BLOCKED: 85,
    VerificationPlanLifecycleState.RUNNING: 80,
    VerificationPlanLifecycleState.STALE: 70,
    VerificationPlanLifecycleState.PASSED: 60,
    VerificationPlanLifecycleState.SELECTED: 50,
    VerificationPlanLifecycleState.ACCEPTED_RISK: 45,
    VerificationPlanLifecycleState.SKIPPED: 40,
    VerificationPlanLifecycleState.PROPOSED: 30,
    VerificationPlanLifecycleState.MANUAL_ONLY: 20,
    VerificationPlanLifecycleState.SUPERSEDED: 10,
}
_SOURCE_PRIORITY: dict[VerificationPlanSource, int] = {
    VerificationPlanSource.OPERATOR: 90,
    VerificationPlanSource.CHANGED_PATHS: 80,
    VerificationPlanSource.CHANGESET_INVENTORY: 75,
    VerificationPlanSource.WORKSPACE_PROFILE: 70,
    VerificationPlanSource.RELEASE_GATE: 65,
    VerificationPlanSource.REPOSITORY_INTELLIGENCE: 60,
    VerificationPlanSource.EVAL_RECOMMENDATION: 55,
    VerificationPlanSource.COMMAND_RECIPE: 50,
    VerificationPlanSource.TASK_TYPE: 45,
    VerificationPlanSource.POLICY_BUDGET: 40,
    VerificationPlanSource.MANUAL_EVIDENCE: 30,
}


def stable_verification_id(seed: str) -> TaskVerificationId:
    """Return the stable v16 preview ID for a derived verification entry."""

    return uuid5(NAMESPACE_URL, f"glassbox:v16-verification-plan:{seed}")


def verification_entry_key(entry: VerificationPlanEntry) -> str:
    """Return the exact-entry dedupe key used by verification previews."""

    command = " ".join(entry.command)
    target_id = entry.target.target_id if entry.target is not None else ""
    return f"{entry.kind.value}:{target_id}:{command}:{entry.check_name}"


def verification_command_key(entry: VerificationPlanEntry) -> tuple[str, ...] | None:
    """Return a cross-source command identity for executable preview entries."""

    if not entry.command:
        return None
    return tuple(str(part) for part in entry.command)


class VerificationPlanEntryCoalescer:
    """Add entries while preserving exact dedupe and same-command coalescing."""

    def __init__(self, entries: list[VerificationPlanEntry]) -> None:
        self._entries = entries
        self._exact_keys: set[str] = set()
        self._command_indexes: dict[tuple[str, ...], int] = {}
        for index, entry in enumerate(entries):
            self._index_entry(index, entry)

    def requires_new_entry(self, entry: VerificationPlanEntry) -> bool:
        """Return true when adding this entry would append to the plan."""

        if verification_entry_key(entry) in self._exact_keys:
            return False
        command_key = verification_command_key(entry)
        return command_key is None or command_key not in self._command_indexes

    def add(self, entry: VerificationPlanEntry) -> None:
        """Add or merge an entry into the mutable backing list."""

        exact_key = verification_entry_key(entry)
        if exact_key in self._exact_keys:
            return
        command_key = verification_command_key(entry)
        if command_key is not None and command_key in self._command_indexes:
            index = self._command_indexes[command_key]
            merged = coalesce_verification_plan_entries(self._entries[index], entry)
            self._entries[index] = merged
            self._exact_keys.add(exact_key)
            self._index_entry(index, merged)
            return
        self._entries.append(entry)
        self._index_entry(len(self._entries) - 1, entry)

    def _index_entry(self, index: int, entry: VerificationPlanEntry) -> None:
        self._exact_keys.add(verification_entry_key(entry))
        command_key = verification_command_key(entry)
        if command_key is not None:
            self._command_indexes[command_key] = index


def coalesce_verification_plan_entries(
    existing: VerificationPlanEntry,
    incoming: VerificationPlanEntry,
) -> VerificationPlanEntry:
    """Merge two entries that point at the same executable command."""

    primary, secondary = (
        (incoming, existing)
        if _entry_authority_score(incoming) > _entry_authority_score(existing)
        else (existing, incoming)
    )
    return primary.model_copy(
        update={
            "blocking": existing.blocking or incoming.blocking,
            "changed_paths": _merge_paths(
                existing.changed_paths, incoming.changed_paths
            ),
            "evidence_references": _merge_evidence_refs(
                existing.evidence_references,
                incoming.evidence_references,
            ),
            "release_surfaces": _merge_strings(
                existing.release_surfaces,
                incoming.release_surfaces,
                limit=20,
            ),
            "stale_reasons": _merge_strings(
                existing.stale_reasons,
                incoming.stale_reasons,
                limit=20,
            ),
            "rationale": _merge_text(primary.rationale, secondary.rationale),
            "selection_rationale": _merge_optional_text(
                primary.selection_rationale,
                secondary.selection_rationale,
            ),
            "command_recipe": primary.command_recipe or secondary.command_recipe,
            "target": primary.target or secondary.target,
            "eval_case_id": primary.eval_case_id or secondary.eval_case_id,
            "eval_profile_id": primary.eval_profile_id or secondary.eval_profile_id,
        }
    )


def _entry_authority_score(entry: VerificationPlanEntry) -> tuple[int, int, int, int]:
    retained_evidence = any(
        ref.kind
        in {NextActionEvidenceKind.VERIFICATION, NextActionEvidenceKind.ARTIFACT}
        for ref in entry.evidence_references
    )
    return (
        100 if retained_evidence else 0,
        _LIFECYCLE_PRIORITY.get(entry.lifecycle_state, 0),
        _SOURCE_PRIORITY.get(entry.source, 0),
        len(entry.evidence_references),
    )


def _merge_paths(left: list[Path], right: list[Path]) -> list[Path]:
    return list(dict.fromkeys([*left, *right]))[:100]


def _merge_evidence_refs(
    left: list[NextActionEvidenceRef],
    right: list[NextActionEvidenceRef],
) -> list[NextActionEvidenceRef]:
    by_key: dict[tuple[str, str, str], NextActionEvidenceRef] = {}
    for ref in [*left, *right]:
        by_key[(ref.kind.value, ref.ref_id, ref.summary)] = ref
    return list(by_key.values())[:20]


def _merge_strings(left: list[str], right: list[str], *, limit: int) -> list[str]:
    return list(dict.fromkeys([*left, *right]))[:limit]


def _merge_optional_text(left: str | None, right: str | None) -> str | None:
    if left is None:
        return right
    if right is None:
        return left
    return _merge_text(left, right)


def _merge_text(left: str, right: str) -> str:
    if left == right or right in left:
        return left
    if left in right:
        return right
    return f"{left}; {right}"[:2000]


__all__ = [
    "VerificationPlanEntryCoalescer",
    "coalesce_verification_plan_entries",
    "stable_verification_id",
    "verification_command_key",
    "verification_entry_key",
]
