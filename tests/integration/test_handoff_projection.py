"""Integration tests for durable handoff workflow projections."""

from pathlib import Path

from glassbox.core import EventEnvelope
from glassbox.core import HandoffArchived
from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffCustodyAccepted
from glassbox.core import HandoffCustodyProposed
from glassbox.core import HandoffCustodyState
from glassbox.core import HandoffIntent
from glassbox.core import HandoffPackageCreated
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffSourceKind
from glassbox.core import ImportedHandoffAcceptedForFollowUp
from glassbox.core import ImportedHandoffInspected
from glassbox.core import SessionStarted
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import rebuild_session_projections
from glassbox.store.sqlite_query_handoff import get_handoff
from glassbox.store.sqlite_query_handoff import list_handoffs
from tests.integration.fault_test_support import open_initialized_database


def test_handoff_package_custody_projection_rebuilds(tmp_path: Path) -> None:
    connection = open_initialized_database(tmp_path)
    session_id = new_session_id()
    task_id = new_task_id()
    package_id = "pkg-session-review"
    try:
        append_events(
            connection,
            [
                _session_started(session_id, tmp_path),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=HandoffPackageCreated(
                        package_id=package_id,
                        source_kind=HandoffSourceKind.SESSION,
                        source_id=str(session_id),
                        package_kind=HandoffPackageKind.SESSION,
                        intent=HandoffIntent.REVIEW_ONLY,
                        artifact_id=new_artifact_id(),
                        package_digest="abc123",
                        compatibility_state=HandoffCompatibilityState.SUPPORTED,
                        redaction_posture=HandoffRedactionPosture.REVIEWER_SAFE,
                        local_only_count=2,
                        expected_custodian="bob",
                        exported_by="alice",
                        note="review the handoff",
                        task_id=task_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=HandoffCustodyProposed(
                        package_id=package_id,
                        source_kind=HandoffSourceKind.SESSION,
                        intent=HandoffIntent.REVIEW_ONLY,
                        proposed_custodian="bob",
                        proposed_by="alice",
                        reason="ready for local review",
                        task_id=task_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=HandoffCustodyAccepted(
                        package_id=package_id,
                        accepted_by="bob",
                        reason="will inspect evidence",
                        follow_up_intent=HandoffIntent.REVIEW_ONLY,
                        safe_next_actions=[
                            "glassbox handoff inspect pkg-session-review"
                        ],
                        task_id=task_id,
                    ),
                ),
            ],
        )

        before = get_handoff(connection, session_id, package_id)
        rebuild_session_projections(connection, session_id)
        after = get_handoff(connection, session_id, package_id)
        by_task = list_handoffs(connection, session_id=session_id, task_id=task_id)
        repository = SQLiteSessionRepository(connection)
        from_repository = repository.get_handoff(session_id, package_id)
    finally:
        connection.close()

    assert before is not None
    assert before == after
    assert from_repository == after
    assert after is not None
    assert after.custody_state == HandoffCustodyState.ACCEPTED
    assert after.current_custodian == "bob"
    assert after.expected_custodian == "bob"
    assert after.exported_by == "alice"
    assert after.package_digest == "abc123"
    assert after.local_only_count == 2
    assert after.safe_next_actions == ["glassbox handoff inspect pkg-session-review"]
    assert [handoff.package_id for handoff in by_task] == [package_id]


def test_imported_handoff_projection_accept_and_archive(tmp_path: Path) -> None:
    connection = open_initialized_database(tmp_path)
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    package_id = "pkg-imported"
    try:
        append_events(
            connection,
            [
                _session_started(session_id, tmp_path),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ImportedHandoffInspected(
                        package_id=package_id,
                        source_kind=HandoffSourceKind.CHANGESET,
                        source_id=str(changeset_id),
                        package_kind=HandoffPackageKind.CHANGESET,
                        intent=HandoffIntent.VERIFICATION_NEEDED,
                        package_digest="digest-1",
                        compatibility_state=(
                            HandoffCompatibilityState.SUPPORTED_WITH_WARNINGS
                        ),
                        redaction_posture=HandoffRedactionPosture.REDACTED,
                        local_only_count=3,
                        inspected_by="recipient",
                        safe_next_actions=["glassbox handoff inspect pkg-imported"],
                        changeset_id=changeset_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ImportedHandoffAcceptedForFollowUp(
                        package_id=package_id,
                        accepted_by="recipient",
                        follow_up_intent=HandoffIntent.VERIFICATION_NEEDED,
                        reason="will run local verification",
                        changeset_id=changeset_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=HandoffArchived(
                        package_id=package_id,
                        archived_by="recipient",
                        reason="follow-up recorded elsewhere",
                        changeset_id=changeset_id,
                    ),
                ),
            ],
        )

        visible = list_handoffs(connection, session_id=session_id)
        archived = list_handoffs(
            connection,
            session_id=session_id,
            include_archived=True,
        )
        record = archived[0]
    finally:
        connection.close()

    assert visible == []
    assert record.package_id == package_id
    assert record.imported is True
    assert record.archived is True
    assert record.custody_state == HandoffCustodyState.ARCHIVED
    assert record.follow_up_intent == HandoffIntent.VERIFICATION_NEEDED
    assert record.changeset_id == str(changeset_id)


def _session_started(session_id, tmp_path: Path) -> EventEnvelope:
    return EventEnvelope(
        session_id=session_id,
        sequence=0,
        payload=SessionStarted(
            cwd=str(tmp_path),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
        ),
    )
