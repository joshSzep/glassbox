"""Session-level v17 handoff readiness derivation."""

from collections.abc import Sequence

from glassbox.core import CheckpointAbsenceReason
from glassbox.core import HandoffIntent
from glassbox.core import HandoffReadiness
from glassbox.core import HandoffReadinessReason
from glassbox.core import HandoffReadinessReasonKind
from glassbox.core import HandoffReadinessState
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import SessionId
from glassbox.runtime.handoff_readiness_reasons import confidence_for_state
from glassbox.runtime.handoff_readiness_reasons import evidence_ref
from glassbox.runtime.handoff_readiness_reasons import freshness_for_state
from glassbox.runtime.session_queries import SessionQueryService
from glassbox.runtime.session_queries import SessionSnapshotView


class SessionHandoffReadinessService:
    """Read-only service for session handoff readiness."""

    def __init__(self, query_service: SessionQueryService) -> None:
        self._query_service = query_service

    def preview(
        self,
        session_id: SessionId,
        *,
        intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
    ) -> HandoffReadiness:
        snapshot = self._query_service.get_session_snapshot(session_id)
        return derive_session_handoff_readiness(snapshot, intent=intent)


def derive_session_handoff_readiness(
    snapshot: SessionSnapshotView,
    *,
    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
) -> HandoffReadiness:
    """Derive advisory readiness for handing off a session."""

    reasons: list[HandoffReadinessReason] = []
    supporting_evidence: list[NextActionEvidenceRef] = []
    missing_evidence: list[NextActionEvidenceRef] = []
    stale_evidence: list[NextActionEvidenceRef] = []
    local_only_evidence: list[HandoffReadinessReason] = []
    accepted_risks: list[HandoffReadinessReason] = []
    limitations: list[str] = []

    if snapshot.transcript:
        supporting_evidence.append(
            _evidence(
                NextActionEvidenceKind.EVENT,
                "session-transcript",
                f"{len(snapshot.transcript)} projected transcript message(s)",
            )
        )
    else:
        missing_evidence.append(
            _evidence(
                NextActionEvidenceKind.EVENT,
                "session-transcript",
                "No projected transcript messages are available.",
            )
        )

    if snapshot.latest_checkpoint is not None:
        supporting_evidence.append(
            _evidence(
                NextActionEvidenceKind.ARTIFACT,
                str(snapshot.latest_checkpoint.checkpoint_id),
                f"Latest checkpoint: {snapshot.latest_checkpoint.next_action}",
                freshness="fresh",
            )
        )
        if snapshot.latest_checkpoint.blockers:
            reasons.append(
                HandoffReadinessReason(
                    kind=HandoffReadinessReasonKind.MISSING_EVIDENCE,
                    summary=snapshot.latest_checkpoint.blockers[0],
                )
            )
    elif snapshot.checkpoint_absence is not None:
        missing_evidence.append(
            _evidence(
                NextActionEvidenceKind.ARTIFACT,
                snapshot.checkpoint_absence.reason.value,
                snapshot.checkpoint_absence.message,
            )
        )

    if snapshot.projection_health.state != "ok":
        stale_evidence.append(
            _evidence(
                NextActionEvidenceKind.PROJECTION,
                "projection-health",
                snapshot.projection_health.detail or snapshot.projection_health.state,
                freshness=snapshot.projection_health.state,
            )
        )
        limitations.append(
            "Projection health is degraded; rebuild projections before relying "
            "on handoff claims."
        )

    if snapshot.pending_approval_id is not None:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.POLICY_BLOCKER,
                summary=(
                    f"Pending approval {snapshot.pending_approval_id} blocks "
                    "continuation."
                ),
            )
        )
    if snapshot.pending_question_id is not None:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.MISSING_EVIDENCE,
                summary=(
                    f"Pending operator answer {snapshot.pending_question_id} "
                    "blocks continuation."
                ),
            )
        )
    if snapshot.session_failure_message is not None:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.UNSUPPORTED_EVIDENCE,
                summary=f"Session failed: {snapshot.session_failure_message}",
            )
        )
    if snapshot.latest_provider_recovery is not None:
        limitations.append(
            "Provider recovery evidence is advisory and should be inspected before "
            "continuation."
        )
    if snapshot.latest_checkpoint is not None and snapshot.latest_checkpoint.blockers:
        limitations.extend(snapshot.latest_checkpoint.blockers[:3])
    if _is_imported_inspection_only(snapshot):
        limitations.append(
            "Imported sessions remain historical inspection state until an explicit "
            "fork or new-session workflow is chosen."
        )
    if snapshot.latest_checkpoint is None and intent in {
        HandoffIntent.CONTINUE_WORK,
        HandoffIntent.FUTURE_SELF,
        HandoffIntent.FORK_RECOMMENDED,
    }:
        limitations.append(
            "No latest checkpoint is available for continuation-oriented handoff."
        )

    local_only_evidence.extend(_local_only_reasons(snapshot))
    if local_only_evidence:
        limitations.append(
            "Some session evidence is local-only and cannot be verified from a "
            "portable package alone."
        )

    state = _session_handoff_state(
        snapshot,
        intent=intent,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
    )
    freshness = freshness_for_state(state)
    confidence = confidence_for_state(state)

    return HandoffReadiness(
        source=HandoffSourceRef(
            kind=HandoffSourceKind.SESSION,
            primary_id=str(snapshot.session_id),
            label="session",
        ),
        intent=intent,
        state=state,
        confidence=confidence,
        freshness=freshness,
        reasons=reasons,
        supporting_evidence=supporting_evidence,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
        accepted_risks=accepted_risks,
        limitations=list(dict.fromkeys(limitations))[:50],
        safe_first_commands=_safe_first_commands(snapshot.session_id),
        non_claims=[
            "session handoff readiness is advisory local posture, not approval",
            (
                "session handoff readiness does not resume, fork, approve, "
                "answer, stage, commit, push, merge, deploy, or publish"
            ),
            "readiness does not prove local-only evidence travelled in a package",
            (
                "imported sessions remain inspection-only unless explicitly "
                "forked or continued through another local workflow"
            ),
        ],
    )


def _session_handoff_state(
    snapshot: SessionSnapshotView,
    *,
    intent: HandoffIntent,
    missing_evidence: Sequence[NextActionEvidenceRef],
    stale_evidence: Sequence[NextActionEvidenceRef],
    local_only_evidence: Sequence[HandoffReadinessReason],
) -> HandoffReadinessState:
    if snapshot.projection_health.state == "unavailable":
        return HandoffReadinessState.BLOCKED
    if snapshot.pending_approval_id is not None:
        return HandoffReadinessState.AWAITING_APPROVAL
    if snapshot.pending_question_id is not None:
        return HandoffReadinessState.AWAITING_ANSWER
    if snapshot.session_failure_message is not None or snapshot.status == "failed":
        return HandoffReadinessState.FAILED_NEEDS_TRIAGE
    if stale_evidence:
        return HandoffReadinessState.STALE_EVIDENCE
    if _is_imported_inspection_only(snapshot):
        return HandoffReadinessState.HISTORICAL_ONLY
    if snapshot.latest_checkpoint is None and intent in {
        HandoffIntent.CONTINUE_WORK,
        HandoffIntent.FUTURE_SELF,
        HandoffIntent.FORK_RECOMMENDED,
    }:
        return HandoffReadinessState.NEEDS_CONTEXT
    if (
        intent == HandoffIntent.VERIFICATION_NEEDED
        and snapshot.latest_checkpoint is None
    ):
        return HandoffReadinessState.NEEDS_VERIFICATION
    if not snapshot.transcript and missing_evidence:
        return HandoffReadinessState.NEEDS_CONTEXT
    if local_only_evidence and intent != HandoffIntent.FUTURE_SELF:
        return HandoffReadinessState.LOCAL_ONLY_EVIDENCE
    if (
        snapshot.status in {"completed", "cancelled"}
        and intent == HandoffIntent.CONTINUE_WORK
    ):
        return HandoffReadinessState.HISTORICAL_ONLY
    return HandoffReadinessState.READY


def _safe_first_commands(session_id: SessionId) -> list[HandoffSafeCommand]:
    return [
        HandoffSafeCommand(
            command=["glassbox", "session", "status", str(session_id), "--cwd", "."],
            display=f"glassbox session status {session_id} --cwd .",
            purpose="Inspect projected session status without resuming work.",
        ),
        HandoffSafeCommand(
            command=[
                "glassbox",
                "session",
                "evidence-graph",
                str(session_id),
                "--summary",
                "--cwd",
                ".",
            ],
            display=f"glassbox session evidence-graph {session_id} --summary --cwd .",
            purpose="Inspect bounded evidence support for the session.",
        ),
        HandoffSafeCommand(
            command=[
                "glassbox",
                "session",
                "compactions",
                str(session_id),
                "--cwd",
                ".",
            ],
            display=f"glassbox session compactions {session_id} --cwd .",
            purpose="Inspect retained compaction and checkpoint context.",
        ),
    ]


def _local_only_reasons(
    snapshot: SessionSnapshotView,
) -> list[HandoffReadinessReason]:
    reasons: list[HandoffReadinessReason] = []
    if snapshot.recent_tool_attempts:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE,
                summary=(
                    "Recent tool-attempt output remains local and is summarized "
                    "rather than exported as raw logs."
                ),
                portable=False,
            )
        )
    if (
        snapshot.latest_checkpoint is not None
        and snapshot.latest_checkpoint.artifact_id
    ):
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE,
                summary=(
                    "Checkpoint artifact contents remain managed local evidence "
                    "unless a later export profile includes a redacted summary."
                ),
                portable=False,
            )
        )
    return reasons


def _is_imported_inspection_only(snapshot: SessionSnapshotView) -> bool:
    return (
        snapshot.checkpoint_absence is not None
        and snapshot.checkpoint_absence.reason
        == CheckpointAbsenceReason.IMPORTED_INSPECTION_ONLY
    )


def _evidence(
    kind: NextActionEvidenceKind,
    ref_id: str,
    summary: str,
    *,
    freshness: str | None = None,
) -> NextActionEvidenceRef:
    return evidence_ref(kind, ref_id, summary, freshness=freshness)


__all__ = [
    "SessionHandoffReadinessService",
    "derive_session_handoff_readiness",
]
