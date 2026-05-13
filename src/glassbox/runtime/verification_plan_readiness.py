"""Verification-plan entries derived from changeset readiness requirements."""

from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanLifecycleState
from glassbox.core import VerificationPlanSource
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.verification_plan_entries import build_verification_entry


def build_readiness_verification_entries(
    readiness: ChangesetVerificationReadiness,
    *,
    changed_paths: list[str],
) -> list[VerificationPlanEntry]:
    """Build command-backed entries from advisory changeset readiness posture."""

    entries: list[VerificationPlanEntry] = []
    for requirement in readiness.requirements:
        if not requirement.command:
            continue
        entries.append(
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
    return entries


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


__all__ = ["build_readiness_verification_entries"]
