"""Shared reason and evidence helpers for handoff readiness services."""

from collections.abc import Container

from glassbox.core import HandoffEvidenceFreshness
from glassbox.core import HandoffReadinessState
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import RepositoryIntelligenceConfidence


def evidence_ref(
    kind: NextActionEvidenceKind,
    ref_id: str,
    summary: str,
    *,
    freshness: str | None = None,
) -> NextActionEvidenceRef:
    """Build a bounded handoff evidence reference."""

    return NextActionEvidenceRef(
        kind=kind,
        ref_id=ref_id,
        summary=summary,
        freshness=freshness,
    )


def freshness_for_state(
    state: HandoffReadinessState,
    *,
    degraded_states: Container[HandoffReadinessState] = (
        HandoffReadinessState.BLOCKED,
    ),
) -> HandoffEvidenceFreshness:
    """Map readiness state to shared evidence freshness posture."""

    if state == HandoffReadinessState.STALE_EVIDENCE:
        return HandoffEvidenceFreshness.STALE
    if state in {
        HandoffReadinessState.NEEDS_CONTEXT,
        HandoffReadinessState.NEEDS_VERIFICATION,
    }:
        return HandoffEvidenceFreshness.MISSING
    if state in degraded_states:
        return HandoffEvidenceFreshness.DEGRADED
    return HandoffEvidenceFreshness.FRESH


def confidence_for_state(
    state: HandoffReadinessState,
    *,
    degraded_states: Container[HandoffReadinessState] = (
        HandoffReadinessState.BLOCKED,
    ),
) -> RepositoryIntelligenceConfidence:
    """Map readiness state to shared confidence posture."""

    if state in {HandoffReadinessState.READY, HandoffReadinessState.HISTORICAL_ONLY}:
        return RepositoryIntelligenceConfidence.HIGH
    if state in {
        HandoffReadinessState.LOCAL_ONLY_EVIDENCE,
        HandoffReadinessState.STALE_EVIDENCE,
        HandoffReadinessState.ACCEPTED_WITH_RISK,
    }:
        return RepositoryIntelligenceConfidence.MEDIUM
    if state in degraded_states:
        return RepositoryIntelligenceConfidence.LOW
    return RepositoryIntelligenceConfidence.UNKNOWN


__all__ = [
    "confidence_for_state",
    "evidence_ref",
    "freshness_for_state",
]
