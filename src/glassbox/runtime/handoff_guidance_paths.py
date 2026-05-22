"""Path and safe-command derivation for imported handoff guidance."""

from glassbox.core import HandoffCustodyState
from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.runtime.handoff_guidance_models import HandoffContinuationPath
from glassbox.runtime.handoff_guidance_models import HandoffGuidanceBlocker
from glassbox.runtime.handoff_guidance_models import HandoffGuidanceState


def guidance_state(
    record: HandoffProjectionRecord,
    blockers: list[HandoffGuidanceBlocker],
) -> HandoffGuidanceState:
    """Choose the recipient guidance state from blockers and intent."""

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


def guidance_paths(
    state: HandoffGuidanceState,
    record: HandoffProjectionRecord,
) -> list[HandoffContinuationPath]:
    """Return ranked recipient follow-up paths without performing mutation."""

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


def guidance_summary(
    state: HandoffGuidanceState,
    record: HandoffProjectionRecord,
) -> str:
    """Return non-claim summary copy for the selected guidance state."""

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


def safe_commands(record: HandoffProjectionRecord) -> list[HandoffSafeCommand]:
    """Build read-only commands for inspecting a handoff guidance result."""

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


def _safe_command(display: str, purpose: str) -> HandoffSafeCommand:
    return HandoffSafeCommand(command=display.split(), display=display, purpose=purpose)


__all__ = [
    "guidance_paths",
    "guidance_state",
    "guidance_summary",
    "safe_commands",
]
