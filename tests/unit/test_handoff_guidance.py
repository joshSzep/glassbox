"""Unit tests for fork-or-continue handoff guidance."""

from datetime import UTC
from datetime import datetime
from pathlib import Path
from uuid import UUID

from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffCustodyState
from glassbox.core import HandoffIntent
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffProjectionRecord
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffSourceKind
from glassbox.core import ProjectionHealth
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.core import SessionStatus
from glassbox.runtime.handoff_guidance import derive_handoff_guidance


def test_guidance_recommends_new_session_for_imported_continue_work() -> None:
    guidance = derive_handoff_guidance(
        _record(intent=HandoffIntent.CONTINUE_WORK),
        session=_session(),
        session_state=_state(),
        projection_health=_projection_health(),
    )

    assert guidance.state == "continue-new-session"
    assert _recommended_path(guidance) == "new-session"
    assert any("inspection-only" in claim for claim in guidance.non_claims)


def test_guidance_blocks_incompatible_package() -> None:
    guidance = derive_handoff_guidance(
        _record(compatibility_state=HandoffCompatibilityState.INVALID),
        session=_session(),
        session_state=_state(),
        projection_health=_projection_health(),
    )

    assert guidance.state == "reject-handoff"
    assert [blocker.kind for blocker in guidance.blockers] == [
        "incompatible-package",
        "missing-package-artifact",
    ]


def test_guidance_recommends_refresh_for_stale_projection() -> None:
    guidance = derive_handoff_guidance(
        _record(),
        session=_session(),
        session_state=_state(),
        projection_health=ProjectionHealth(
            state="stale",
            canonical_last_sequence=4,
            projected_last_sequence=2,
            lag=2,
            detail="projection lag",
        ),
    )

    assert guidance.state == "refresh-repository"
    assert any(
        blocker.kind == "stale-repository-state" for blocker in guidance.blockers
    )


def test_guidance_recommends_verification_for_changeset_package() -> None:
    guidance = derive_handoff_guidance(
        _record(
            source_kind=HandoffSourceKind.CHANGESET,
            package_kind=HandoffPackageKind.CHANGESET,
            intent=HandoffIntent.VERIFICATION_NEEDED,
            source_id="changeset-1",
        ),
        session=_session(),
        session_state=_state(),
        projection_health=_projection_health(),
    )

    assert guidance.state == "run-verification"
    assert any(
        "changeset show" in command.display for command in guidance.safe_commands
    )


def _recommended_path(guidance) -> str:
    return next(path.path_id for path in guidance.paths if path.recommended)


def _record(
    *,
    source_kind: HandoffSourceKind = HandoffSourceKind.SESSION,
    package_kind: HandoffPackageKind = HandoffPackageKind.SESSION,
    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
    compatibility_state: HandoffCompatibilityState = (
        HandoffCompatibilityState.SUPPORTED
    ),
    source_id: str = "00000000-0000-0000-0000-000000000002",
) -> HandoffProjectionRecord:
    now = datetime(2026, 5, 18, tzinfo=UTC)
    return HandoffProjectionRecord(
        session_id="00000000-0000-0000-0000-000000000001",
        package_id="pkg-guidance",
        source_kind=source_kind,
        source_id=source_id,
        package_kind=package_kind,
        intent=intent,
        compatibility_state=compatibility_state,
        redaction_posture=HandoffRedactionPosture.REDACTED,
        custody_state=HandoffCustodyState.IMPORTED_INSPECTED,
        imported=True,
        created_at=now,
        updated_at=now,
        last_event_type="ImportedHandoffInspected",
        last_sequence=1,
    )


def _session() -> SessionRecord:
    now = datetime(2026, 5, 18, tzinfo=UTC)
    return SessionRecord(
        session_id=UUID("00000000-0000-0000-0000-000000000001"),
        status=SessionStatus.COMPLETED,
        created_at=now,
        updated_at=now,
        cwd=Path("."),
        model_name="openai:gpt-5.4",
        approval_mode="confirm",
        last_sequence=1,
    )


def _state() -> SessionState:
    return SessionState(
        session_id=UUID("00000000-0000-0000-0000-000000000001"),
        status=SessionStatus.COMPLETED,
    )


def _projection_health() -> ProjectionHealth:
    return ProjectionHealth(
        state="ok",
        canonical_last_sequence=1,
        projected_last_sequence=1,
        lag=0,
    )
