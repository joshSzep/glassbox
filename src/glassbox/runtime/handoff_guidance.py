"""Fork-or-continue guidance facade for imported handoff records."""

from glassbox.core import HandoffProjectionRecord
from glassbox.core import ProjectionHealth
from glassbox.core import SessionId
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.runtime.handoff_guidance_blockers import guidance_blockers
from glassbox.runtime.handoff_guidance_models import HandoffContinuationPath
from glassbox.runtime.handoff_guidance_models import HandoffGuidance
from glassbox.runtime.handoff_guidance_models import HandoffGuidanceBlocker
from glassbox.runtime.handoff_guidance_models import HandoffGuidanceState
from glassbox.runtime.handoff_guidance_paths import guidance_paths
from glassbox.runtime.handoff_guidance_paths import guidance_state
from glassbox.runtime.handoff_guidance_paths import guidance_summary
from glassbox.runtime.handoff_guidance_paths import safe_commands
from glassbox.runtime.handoff_repository_contracts import HandoffGuidanceRepository


def derive_handoff_guidance(
    record: HandoffProjectionRecord,
    *,
    session: SessionRecord | None,
    session_state: SessionState | None,
    projection_health: ProjectionHealth | None,
) -> HandoffGuidance:
    """Derive advisory recipient guidance without mutating local state."""

    blockers = guidance_blockers(record, session, session_state, projection_health)
    state = guidance_state(record, blockers)
    return HandoffGuidance(
        package_id=record.package_id,
        session_id=record.session_id,
        state=state,
        summary=guidance_summary(state, record),
        blockers=blockers,
        paths=guidance_paths(state, record),
        safe_commands=safe_commands(record),
        non_claims=[
            "guidance is advisory and does not approve continuation",
            (
                "imported sessions remain inspection-only until an explicit "
                "local workflow is chosen"
            ),
            "guidance does not resume provider streams or imported live turns",
        ],
    )


def load_handoff_guidance(
    repository: HandoffGuidanceRepository,
    session_id: SessionId,
    package_id: str,
) -> HandoffGuidance:
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


__all__ = [
    "HandoffContinuationPath",
    "HandoffGuidance",
    "HandoffGuidanceBlocker",
    "HandoffGuidanceState",
    "derive_handoff_guidance",
    "load_handoff_guidance",
]
