"""Shared v17 readiness adapter for changeset handoff posture."""

from collections.abc import Sequence

from glassbox.core import ChangesetRecord
from glassbox.core import HandoffEvidenceFreshness
from glassbox.core import HandoffIntent
from glassbox.core import HandoffReadiness
from glassbox.core import HandoffReadinessReason
from glassbox.core import HandoffReadinessReasonKind
from glassbox.core import HandoffReadinessState as SharedHandoffReadinessState
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import RepositoryIntelligenceConfidence
from glassbox.runtime.handoff_readiness_signals import HandoffReadinessSignal
from glassbox.runtime.handoff_readiness_signals import HandoffReadinessState


def build_shared_changeset_handoff_readiness(
    *,
    changeset: ChangesetRecord,
    state: HandoffReadinessState,
    reason: str,
    blockers: Sequence[str],
    limitations: Sequence[str],
    safe_next_actions: Sequence[str],
    signals: Sequence[HandoffReadinessSignal],
    non_claims: Sequence[str],
) -> HandoffReadiness:
    """Map changeset-specific handoff posture into the shared v17 model."""

    shared_state = _shared_state(state)
    return HandoffReadiness(
        source=HandoffSourceRef(
            kind=HandoffSourceKind.CHANGESET,
            primary_id=str(changeset.changeset_id),
            identifiers=_shared_identifiers(changeset),
            label=changeset.summary or changeset.objective,
        ),
        intent=HandoffIntent.REVIEW_ONLY,
        state=shared_state,
        confidence=_shared_confidence(shared_state),
        freshness=_shared_freshness(shared_state),
        reasons=_shared_reasons(reason, blockers, signals),
        supporting_evidence=_shared_supporting_evidence(changeset, signals),
        missing_evidence=_shared_missing_evidence(signals),
        stale_evidence=_shared_stale_evidence(signals),
        local_only_evidence=_shared_local_only_evidence(signals),
        accepted_risks=_shared_accepted_risks(signals),
        limitations=list(dict.fromkeys(limitations))[:50],
        safe_first_commands=_shared_safe_commands(safe_next_actions),
        non_claims=list(non_claims),
    )


def _shared_identifiers(changeset: ChangesetRecord) -> dict[str, str]:
    identifiers = {"session_id": str(changeset.session_id)}
    if changeset.task_id is not None:
        identifiers["task_id"] = str(changeset.task_id)
    return identifiers


def _shared_state(state: HandoffReadinessState) -> SharedHandoffReadinessState:
    if state in {"handoff_ready", "commit_prep_ready"}:
        return SharedHandoffReadinessState.READY
    if state == "needs_verification":
        return SharedHandoffReadinessState.NEEDS_VERIFICATION
    if state == "needs_review_response":
        return SharedHandoffReadinessState.NEEDS_CONTEXT
    if state == "stale_inventory":
        return SharedHandoffReadinessState.STALE_EVIDENCE
    if state == "accepted_with_risk":
        return SharedHandoffReadinessState.ACCEPTED_WITH_RISK
    return SharedHandoffReadinessState.BLOCKED


def _shared_reasons(
    reason: str,
    blockers: Sequence[str],
    signals: Sequence[HandoffReadinessSignal],
) -> list[HandoffReadinessReason]:
    blocking_signals = [signal for signal in signals if signal.blocking]
    summaries = list(blockers) or [reason]
    reasons: list[HandoffReadinessReason] = []
    for index, summary in enumerate(summaries):
        signal = blocking_signals[index] if index < len(blocking_signals) else None
        reasons.append(
            HandoffReadinessReason(
                kind=_shared_reason_kind(signal)
                if signal is not None
                else HandoffReadinessReasonKind.SUPPORTING_EVIDENCE,
                summary=summary,
            )
        )
    return reasons[:50]


def _shared_reason_kind(
    signal: HandoffReadinessSignal,
) -> HandoffReadinessReasonKind:
    if signal.state == "stale_inventory":
        return HandoffReadinessReasonKind.STALE_EVIDENCE
    if signal.signal_id in {"local-only-evidence", "skipped-live-evidence"}:
        return HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE
    if signal.state in {"needs_review_response", "needs_verification"}:
        return HandoffReadinessReasonKind.MISSING_EVIDENCE
    if signal.state in {"accepted_with_risk", "unresolved_risk"}:
        return HandoffReadinessReasonKind.ACCEPTED_RISK
    return HandoffReadinessReasonKind.PACKAGE_LIMITATION


def _shared_supporting_evidence(
    changeset: ChangesetRecord,
    signals: Sequence[HandoffReadinessSignal],
) -> list[NextActionEvidenceRef]:
    evidence = [
        NextActionEvidenceRef(
            kind=NextActionEvidenceKind.EVENT,
            ref_id=str(changeset.changeset_id),
            summary=f"Changeset objective: {changeset.objective}",
        )
    ]
    evidence.extend(
        NextActionEvidenceRef(
            kind=NextActionEvidenceKind.CLI_OUTPUT,
            ref_id=signal.signal_id,
            summary=signal.summary,
        )
        for signal in signals
        if not signal.blocking
    )
    return evidence[:50]


def _shared_missing_evidence(
    signals: Sequence[HandoffReadinessSignal],
) -> list[NextActionEvidenceRef]:
    return [
        _signal_evidence(signal, freshness="missing")
        for signal in signals
        if signal.state in {"needs_review_response", "needs_verification", "not_ready"}
    ][:50]


def _shared_stale_evidence(
    signals: Sequence[HandoffReadinessSignal],
) -> list[NextActionEvidenceRef]:
    return [
        _signal_evidence(signal, freshness="stale")
        for signal in signals
        if signal.state == "stale_inventory"
    ][:50]


def _shared_local_only_evidence(
    signals: Sequence[HandoffReadinessSignal],
) -> list[HandoffReadinessReason]:
    return [
        HandoffReadinessReason(
            kind=HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE,
            summary=signal.summary,
            portable=False,
        )
        for signal in signals
        if signal.signal_id in {"local-only-evidence", "skipped-live-evidence"}
    ][:50]


def _shared_accepted_risks(
    signals: Sequence[HandoffReadinessSignal],
) -> list[HandoffReadinessReason]:
    return [
        HandoffReadinessReason(
            kind=HandoffReadinessReasonKind.ACCEPTED_RISK,
            summary=signal.summary,
        )
        for signal in signals
        if signal.state in {"accepted_with_risk", "unresolved_risk"}
    ][:50]


def _signal_evidence(
    signal: HandoffReadinessSignal,
    *,
    freshness: str,
) -> NextActionEvidenceRef:
    return NextActionEvidenceRef(
        kind=NextActionEvidenceKind.CLI_OUTPUT,
        ref_id=signal.signal_id,
        summary=signal.summary,
        freshness=freshness,
    )


def _shared_safe_commands(
    safe_next_actions: Sequence[str],
) -> list[HandoffSafeCommand]:
    return [
        HandoffSafeCommand(
            command=action.split(),
            display=action,
            purpose="Inspect changeset handoff posture before mutation.",
        )
        for action in safe_next_actions
        if _is_read_only_handoff_action(action)
    ][:20]


def _is_read_only_handoff_action(action: str) -> bool:
    return (
        action == "git status --short"
        or action.startswith("glassbox changeset show ")
        or action.startswith("glassbox changeset handoff-readiness ")
        or action.startswith("glassbox changeset evidence list ")
        or action.startswith("glassbox changeset feedback status ")
        or action.startswith("glassbox changeset verification-plan ")
        or action.startswith("glassbox changeset commit-prep ")
    )


def _shared_freshness(
    state: SharedHandoffReadinessState,
) -> HandoffEvidenceFreshness:
    if state == SharedHandoffReadinessState.STALE_EVIDENCE:
        return HandoffEvidenceFreshness.STALE
    if state in {
        SharedHandoffReadinessState.NEEDS_CONTEXT,
        SharedHandoffReadinessState.NEEDS_VERIFICATION,
    }:
        return HandoffEvidenceFreshness.MISSING
    if state == SharedHandoffReadinessState.BLOCKED:
        return HandoffEvidenceFreshness.DEGRADED
    return HandoffEvidenceFreshness.FRESH


def _shared_confidence(
    state: SharedHandoffReadinessState,
) -> RepositoryIntelligenceConfidence:
    if state == SharedHandoffReadinessState.READY:
        return RepositoryIntelligenceConfidence.HIGH
    if state in {
        SharedHandoffReadinessState.ACCEPTED_WITH_RISK,
        SharedHandoffReadinessState.STALE_EVIDENCE,
    }:
        return RepositoryIntelligenceConfidence.MEDIUM
    if state == SharedHandoffReadinessState.BLOCKED:
        return RepositoryIntelligenceConfidence.LOW
    return RepositoryIntelligenceConfidence.UNKNOWN


__all__ = ["build_shared_changeset_handoff_readiness"]
