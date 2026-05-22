"""Blocker and limitation derivation for imported handoff guidance."""

from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffProjectionRecord
from glassbox.core import ProjectionHealth
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.runtime.handoff_guidance_models import HandoffGuidanceBlocker


def guidance_blockers(
    record: HandoffProjectionRecord,
    session: SessionRecord | None,
    session_state: SessionState | None,
    projection_health: ProjectionHealth | None,
) -> list[HandoffGuidanceBlocker]:
    """Derive explicit blockers that constrain recipient follow-up."""

    blockers: list[HandoffGuidanceBlocker] = []
    if not record.imported:
        blockers.append(
            _blocker(
                "unsupported-live-continuation",
                "This handoff record is not an imported historical package.",
            )
        )
    if record.compatibility_state in {
        HandoffCompatibilityState.INVALID,
        HandoffCompatibilityState.UNSUPPORTED,
        HandoffCompatibilityState.FUTURE_VERSION,
    }:
        blockers.append(
            _blocker(
                "incompatible-package",
                (
                    "Package compatibility blocks continuation until a supported "
                    "package is supplied."
                ),
                severity="high",
            )
        )
    if record.local_only_count > 0:
        blockers.append(
            _blocker(
                "local-only-evidence",
                "Some supporting evidence stayed in the source workspace.",
            )
        )
    if session is not None and session.status == "failed":
        blockers.append(
            _blocker(
                "failed-imported-session",
                "Imported historical session ended failed and needs triage first.",
            )
        )
    if session_state is not None and (
        session_state.pending_approval_id is not None
        or session_state.pending_question_id is not None
    ):
        blockers.append(
            _blocker(
                "unresolved-approval-or-question",
                "Imported state contains unresolved approval or question posture.",
            )
        )
    if projection_health is not None and (
        projection_health.degraded or projection_health.state != "ok"
    ):
        blockers.append(
            _blocker(
                "stale-repository-state",
                projection_health.detail
                or "Local projections are degraded; refresh before acting.",
            )
        )
    if record.artifact_id is None:
        blockers.append(
            _blocker(
                "missing-package-artifact",
                "No managed package artifact is linked to this handoff record.",
                severity="low",
            )
        )
    return blockers


def _blocker(
    kind: str,
    summary: str,
    *,
    severity: str = "medium",
) -> HandoffGuidanceBlocker:
    return HandoffGuidanceBlocker(kind=kind, summary=summary, severity=severity)


__all__ = ["guidance_blockers"]
