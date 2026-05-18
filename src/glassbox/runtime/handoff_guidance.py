"""Fork-or-continue guidance for imported handoff records."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffCustodyState
from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import ProjectionHealth
from glassbox.core import SessionId
from glassbox.core import SessionRecord
from glassbox.core import SessionState

type HandoffGuidanceState = Literal[
    "inspect-only",
    "fork-recommended",
    "continue-new-session",
    "run-verification",
    "refresh-repository",
    "reject-handoff",
]


class HandoffGuidanceBlocker(BaseModel):
    """One explicit reason that blocks or limits continuation."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=1000)
    severity: str = Field(default="medium", min_length=1, max_length=40)


class HandoffContinuationPath(BaseModel):
    """One possible recipient path after inspecting an imported handoff."""

    model_config = ConfigDict(extra="forbid")

    path_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1000)
    recommended: bool = False
    requires_explicit_mutation: bool = False


class HandoffGuidance(BaseModel):
    """Recipient-facing fork-or-continue guidance."""

    model_config = ConfigDict(extra="forbid")

    package_id: str = Field(min_length=1, max_length=300)
    session_id: str = Field(min_length=1, max_length=80)
    state: HandoffGuidanceState
    summary: str = Field(min_length=1, max_length=2000)
    blockers: list[HandoffGuidanceBlocker] = Field(default_factory=list, max_length=20)
    paths: list[HandoffContinuationPath] = Field(default_factory=list, max_length=10)
    safe_commands: list[HandoffSafeCommand] = Field(default_factory=list, max_length=20)
    non_claims: list[str] = Field(default_factory=list, max_length=20)


def derive_handoff_guidance(
    record: HandoffProjectionRecord,
    *,
    session: SessionRecord | None,
    session_state: SessionState | None,
    projection_health: ProjectionHealth | None,
) -> HandoffGuidance:
    """Derive advisory recipient guidance without mutating local state."""

    blockers = _blockers(record, session, session_state, projection_health)
    state = _guidance_state(record, blockers)
    return HandoffGuidance(
        package_id=record.package_id,
        session_id=record.session_id,
        state=state,
        summary=_summary(state, record),
        blockers=blockers,
        paths=_paths(state, record, blockers),
        safe_commands=_safe_commands(record),
        non_claims=[
            "guidance is advisory and does not approve continuation",
            (
                "imported sessions remain inspection-only until an explicit "
                "local workflow is chosen"
            ),
            "guidance does not resume provider streams or imported live turns",
        ],
    )


def load_handoff_guidance(repository, session_id: SessionId, package_id: str):
    """Load a projected handoff and derive guidance from local projections."""

    record = repository.get_handoff(session_id, package_id)
    if record is None:
        raise ValueError(
            f"unknown handoff package for session {session_id}: {package_id}"
        )
    return derive_handoff_guidance(
        record,
        session=repository.get_session(session_id),
        session_state=repository.get_session_state(session_id),
        projection_health=repository.inspect_session_projection_health(session_id),
    )


def _guidance_state(
    record: HandoffProjectionRecord,
    blockers: list[HandoffGuidanceBlocker],
) -> HandoffGuidanceState:
    blocker_kinds = {blocker.kind for blocker in blockers}
    if "incompatible-package" in blocker_kinds or "rejected-handoff" in blocker_kinds:
        return "reject-handoff"
    if "stale-repository-state" in blocker_kinds:
        return "refresh-repository"
    if record.source_kind == HandoffSourceKind.CHANGESET or (
        record.intent == HandoffIntent.VERIFICATION_NEEDED
    ):
        return "run-verification"
    if record.intent == HandoffIntent.FORK_RECOMMENDED:
        return "fork-recommended"
    if record.intent in {HandoffIntent.CONTINUE_WORK, HandoffIntent.FUTURE_SELF}:
        return "continue-new-session"
    return "inspect-only"


def _blockers(
    record: HandoffProjectionRecord,
    session: SessionRecord | None,
    session_state: SessionState | None,
    projection_health: ProjectionHealth | None,
) -> list[HandoffGuidanceBlocker]:
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


def _paths(
    state: HandoffGuidanceState,
    record: HandoffProjectionRecord,
    blockers: list[HandoffGuidanceBlocker],
) -> list[HandoffContinuationPath]:
    return [
        HandoffContinuationPath(
            path_id="inspect-only",
            title="Inspect only",
            summary="Review the imported history, package posture, and blockers.",
            recommended=state == "inspect-only",
        ),
        HandoffContinuationPath(
            path_id="fork",
            title="Fork from imported history",
            summary="Use a separate explicit fork workflow after inspection.",
            recommended=state == "fork-recommended",
            requires_explicit_mutation=True,
        ),
        HandoffContinuationPath(
            path_id="new-session",
            title="Continue in a new local session",
            summary=(
                "Start a new session with inspected context instead of resuming import."
            ),
            recommended=state == "continue-new-session",
            requires_explicit_mutation=True,
        ),
        HandoffContinuationPath(
            path_id="verify",
            title="Run local verification",
            summary="Inspect retained verification gaps before choosing checks.",
            recommended=state == "run-verification",
            requires_explicit_mutation=True,
        ),
        HandoffContinuationPath(
            path_id="reject",
            title="Reject the handoff",
            summary="Retain a rejection reason when blockers prevent safe follow-up.",
            recommended=state == "reject-handoff"
            or record.custody_state == HandoffCustodyState.REJECTED,
            requires_explicit_mutation=True,
        ),
    ]


def _safe_commands(record: HandoffProjectionRecord) -> list[HandoffSafeCommand]:
    commands = [
        _safe_command(
            f"glassbox handoff show {record.session_id} {record.package_id}",
            "Inspect projected handoff custody state.",
        ),
        _safe_command(
            f"glassbox session status {record.session_id}",
            "Inspect imported historical session status.",
        ),
    ]
    if record.source_kind == HandoffSourceKind.CHANGESET and record.source_id:
        commands.append(
            _safe_command(
                f"glassbox changeset show {record.source_id}",
                "Inspect changeset evidence before verification or review.",
            )
        )
    return commands


def _summary(
    state: HandoffGuidanceState,
    record: HandoffProjectionRecord,
) -> str:
    summaries = {
        "inspect-only": "Inspect the handoff before choosing any mutation.",
        "fork-recommended": "Fork is the clearest explicit continuation path.",
        "continue-new-session": (
            "Continue by starting a new local session after inspection."
        ),
        "run-verification": "Verification should be inspected and chosen locally.",
        "refresh-repository": "Refresh stale local state before trusting guidance.",
        "reject-handoff": "Reject or replace the handoff before follow-up.",
    }
    if not record.imported:
        return "Non-imported handoffs are guidance-only until imported or inspected."
    return summaries[state]


def _blocker(
    kind: str,
    summary: str,
    *,
    severity: str = "medium",
) -> HandoffGuidanceBlocker:
    return HandoffGuidanceBlocker(kind=kind, summary=summary, severity=severity)


def _safe_command(display: str, purpose: str) -> HandoffSafeCommand:
    return HandoffSafeCommand(command=display.split(), display=display, purpose=purpose)


__all__ = [
    "HandoffContinuationPath",
    "HandoffGuidance",
    "HandoffGuidanceBlocker",
    "HandoffGuidanceState",
    "derive_handoff_guidance",
    "load_handoff_guidance",
]
