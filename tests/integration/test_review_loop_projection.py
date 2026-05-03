"""Integration tests for review feedback projections and query helpers."""

import sqlite3
from pathlib import Path

from glassbox.core import ChangesetCreated
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import EventEnvelope
from glassbox.core import ManualEvidenceArchived
from glassbox.core import ManualEvidenceAttached
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRedactionStatus
from glassbox.core import ManualEvidenceRejected
from glassbox.core import ManualEvidenceState
from glassbox.core import ManualEvidenceSuperseded
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackArchived
from glassbox.core import ReviewFeedbackCreated
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackDispositionUpdated
from glassbox.core import ReviewFeedbackFixupInventoryAttached
from glassbox.core import ReviewFeedbackFixupPathSummary
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackReopened
from glassbox.core import ReviewFeedbackResolved
from glassbox.core import ReviewFeedbackRiskAccepted
from glassbox.core import ReviewFeedbackScopeAttached
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.core import ReviewFixupSourceKind
from glassbox.core import SessionStarted
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_manual_evidence_id
from glassbox.core import new_review_feedback_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_turn_id
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.store.sqlite import rebuild_session_projections


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def test_review_feedback_projection_queries_current_state_and_scopes(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    archived_feedback_id = new_review_feedback_id()
    task_id = new_task_id()
    turn_id = new_turn_id()
    file_path = "src/glassbox/store/sqlite_projection_review_loop.py"
    connection = _open_initialized_database(tmp_path)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetCreated(
                        changeset_id=changeset_id,
                        objective="track local review feedback",
                        task_id=task_id,
                        turn_id=turn_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackCreated(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        feedback_kind=ReviewFeedbackKind.REQUESTED_CHANGE,
                        provenance=ReviewFeedbackProvenance.REVIEWER,
                        summary="Projection should expose file-scoped feedback",
                        body="Keep the list query bounded and redacted.",
                        source_label="local-review",
                        reviewer_label="reviewer-1",
                        task_id=task_id,
                        turn_id=turn_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackScopeAttached(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        scope_kind=ReviewFeedbackScopeKind.FILE,
                        reason="The requested change is tied to a file range.",
                        file_path=file_path,
                        line_start=12,
                        line_end=18,
                        task_id=task_id,
                        turn_id=turn_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackDispositionUpdated(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        disposition=ReviewFeedbackDisposition.IN_PROGRESS,
                        reason="Work started locally.",
                        updated_by="operator",
                        task_id=task_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackResolved(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        resolution_summary="Projection query now covers scopes.",
                        residual_risk="Needs one rebuild test.",
                        task_id=task_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackReopened(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        reason="Coverage gap remained.",
                        reopened_by="operator",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackRiskAccepted(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        risk_summary="File filtering depends on path metadata.",
                        acceptance_reason="The canonical event keeps the source truth.",
                        accepted_by="operator",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackCreated(
                        feedback_id=archived_feedback_id,
                        changeset_id=changeset_id,
                        feedback_kind=ReviewFeedbackKind.OBSERVATION,
                        provenance=ReviewFeedbackProvenance.OPERATOR,
                        summary="Superseded local note",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackScopeAttached(
                        feedback_id=archived_feedback_id,
                        changeset_id=changeset_id,
                        scope_kind=ReviewFeedbackScopeKind.FILE,
                        reason="The note was attached before being archived.",
                        file_path=file_path,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackArchived(
                        feedback_id=archived_feedback_id,
                        changeset_id=changeset_id,
                        reason="Merged into the requested-change feedback.",
                        replacement_feedback_id=feedback_id,
                    ),
                ),
            ],
        )
        repository = SQLiteSessionRepository(connection)

        service = ChangesetQueryService(repository)

        active_feedback = service.list_review_feedback(
            session_id=session_id,
            changeset_id=changeset_id,
        )
        accepted_feedback = service.list_review_feedback(
            session_id=session_id,
            changeset_id=changeset_id,
            disposition=ReviewFeedbackDisposition.ACCEPTED_WITH_RISK,
        )
        file_feedback = service.list_review_feedback(
            session_id=session_id,
            file_path=file_path,
            include_archived=True,
        )
        archived_feedback = service.list_review_feedback(
            session_id=session_id,
            include_archived=True,
        )
        record = service.get_review_feedback(feedback_id)
        scopes = service.list_review_feedback_scopes(session_id, feedback_id)
    finally:
        connection.close()

    assert [item.feedback_id for item in active_feedback] == [feedback_id]
    assert [item.feedback_id for item in accepted_feedback] == [feedback_id]
    assert {item.feedback_id for item in file_feedback} == {
        feedback_id,
        archived_feedback_id,
    }
    assert {item.feedback_id for item in archived_feedback} == {
        feedback_id,
        archived_feedback_id,
    }
    assert record is not None
    assert record.disposition == ReviewFeedbackDisposition.ACCEPTED_WITH_RISK
    assert record.feedback_kind == ReviewFeedbackKind.REQUESTED_CHANGE
    assert record.provenance == ReviewFeedbackProvenance.REVIEWER
    assert record.risk_summary == "File filtering depends on path metadata."
    assert record.acceptance_reason == "The canonical event keeps the source truth."
    assert record.resolution_summary == "Projection query now covers scopes."
    assert record.reopened_count == 1
    assert record.task_id == task_id
    assert len(scopes) == 1
    assert scopes[0].scope_kind == ReviewFeedbackScopeKind.FILE
    assert scopes[0].file_path == file_path
    assert scopes[0].line_start == 12
    assert scopes[0].line_end == 18


def test_review_feedback_projection_rebuilds_from_canonical_events(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    connection = _open_initialized_database(tmp_path)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetCreated(
                        changeset_id=changeset_id,
                        objective="rebuild review feedback",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackCreated(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        feedback_kind=ReviewFeedbackKind.REVIEWER_QUESTION,
                        summary="Does rebuild restore review questions?",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackScopeAttached(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        scope_kind=ReviewFeedbackScopeKind.CHANGESET,
                        reason="Question applies to the whole changeset.",
                    ),
                ),
            ],
        )
        with connection:
            connection.execute(
                "delete from review_feedback_scopes where session_id = ?",
                (str(session_id),),
            )
            connection.execute(
                "delete from review_feedback where session_id = ?",
                (str(session_id),),
            )

        rebuild_session_projections(connection, session_id)
        repository = SQLiteSessionRepository(connection)
        record = repository.get_review_feedback(feedback_id)
        scopes = repository.list_review_feedback_scopes(session_id, feedback_id)
    finally:
        connection.close()

    assert record is not None
    assert record.summary == "Does rebuild restore review questions?"
    assert record.disposition == ReviewFeedbackDisposition.OPEN
    assert len(scopes) == 1
    assert scopes[0].scope_kind == ReviewFeedbackScopeKind.CHANGESET


def test_review_feedback_fixup_inventory_projection_links_paths(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    artifact_id = new_artifact_id()
    file_path = "src/glassbox/runtime/changesets.py"
    connection = _open_initialized_database(tmp_path)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetCreated(
                        changeset_id=changeset_id,
                        objective="link fixup inventory",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackCreated(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        feedback_kind=ReviewFeedbackKind.REQUESTED_CHANGE,
                        summary="Attach fixup inventory paths.",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackScopeAttached(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        scope_kind=ReviewFeedbackScopeKind.FILE,
                        reason="requested change names the runtime path",
                        file_path=file_path,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackFixupInventoryAttached(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        artifact_id=artifact_id,
                        artifact_schema_version=1,
                        source_kind=ReviewFixupSourceKind.MANUAL_WORKSPACE_EDIT,
                        source_summary="operator recorded bounded fixup inventory",
                        source_digest="sha256:abc",
                        inventory_freshness=ChangesetInventoryFreshness.FRESH,
                        changed_path_count=2,
                        matched_scope_path_count=1,
                        paths=[
                            ReviewFeedbackFixupPathSummary(
                                path=file_path,
                                change_kind="modified",
                                generated=False,
                                test_file=False,
                                docs_file=False,
                                policy_sensitive=False,
                                risk_level="high",
                                provenance_confidence="unknown",
                                matches_feedback_scope=True,
                                summary=f"{file_path}: matches feedback scope",
                            ),
                            ReviewFeedbackFixupPathSummary(
                                path="tests/unit/test_changeset.py",
                                change_kind="modified",
                                generated=False,
                                test_file=True,
                                docs_file=False,
                                policy_sensitive=False,
                                risk_level="low",
                                provenance_confidence="unknown",
                                matches_feedback_scope=False,
                                summary="tests/unit/test_changeset.py: test path",
                            ),
                        ],
                    ),
                ),
            ],
        )
        repository = SQLiteSessionRepository(connection)
        inventories = repository.list_review_feedback_fixup_inventories(
            session_id,
            feedback_id,
        )
        paths = repository.list_review_feedback_fixup_paths(
            session_id,
            feedback_id,
            artifact_id,
        )
        record = repository.get_review_feedback(feedback_id)
    finally:
        connection.close()

    assert record is not None
    assert record.last_sequence == inventories[0].last_sequence
    assert inventories[0].source_kind == ReviewFixupSourceKind.MANUAL_WORKSPACE_EDIT
    assert inventories[0].changed_path_count == 2
    assert inventories[0].matched_scope_path_count == 1
    assert inventories[0].source_digest == "sha256:abc"
    assert [path.path for path in paths] == [
        file_path,
        "tests/unit/test_changeset.py",
    ]
    assert paths[0].matches_feedback_scope is True
    assert paths[1].test_file is True


def test_manual_evidence_projection_queries_and_rebuilds(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    feedback_id = new_review_feedback_id()
    evidence_id = new_manual_evidence_id()
    replacement_id = new_manual_evidence_id()
    rejected_id = new_manual_evidence_id()
    artifact_id = new_artifact_id()
    replacement_artifact_id = new_artifact_id()
    connection = _open_initialized_database(tmp_path)
    try:
        append_events(
            connection,
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd="/tmp/glassbox",
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetCreated(
                        changeset_id=changeset_id,
                        objective="retain manual evidence",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ReviewFeedbackCreated(
                        feedback_id=feedback_id,
                        changeset_id=changeset_id,
                        feedback_kind=ReviewFeedbackKind.REQUESTED_CHANGE,
                        summary="Add manual evidence retention.",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ManualEvidenceAttached(
                        evidence_id=evidence_id,
                        evidence_kind=ManualEvidenceKind.MANUAL_COMMAND,
                        target_kind=ManualEvidenceTargetKind.FEEDBACK,
                        target_id=str(feedback_id),
                        changeset_id=changeset_id,
                        feedback_id=feedback_id,
                        artifact_id=artifact_id,
                        artifact_schema_version=1,
                        summary="operator says pytest passed outside Glassbox",
                        source_label="operator-shell",
                        redaction_status=ManualEvidenceRedactionStatus.PASSED,
                        freshness=ManualEvidenceFreshness.CURRENT,
                        limitations=["manual summary only"],
                        non_claims=["not retained command evidence"],
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ManualEvidenceAttached(
                        evidence_id=replacement_id,
                        evidence_kind=ManualEvidenceKind.MANUAL_COMMAND,
                        target_kind=ManualEvidenceTargetKind.FEEDBACK,
                        target_id=str(feedback_id),
                        changeset_id=changeset_id,
                        feedback_id=feedback_id,
                        artifact_id=replacement_artifact_id,
                        artifact_schema_version=1,
                        summary="operator says focused pytest passed after rerun",
                        source_label="operator-shell",
                        redaction_status=ManualEvidenceRedactionStatus.PASSED,
                        freshness=ManualEvidenceFreshness.CURRENT,
                        limitations=["manual summary only"],
                        non_claims=["not retained command evidence"],
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ManualEvidenceSuperseded(
                        evidence_id=evidence_id,
                        replacement_evidence_id=replacement_id,
                        reason="newer rerun summary replaced the first note",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ManualEvidenceRejected(
                        evidence_id=rejected_id,
                        evidence_kind=ManualEvidenceKind.SANITIZED_LOG,
                        target_kind=ManualEvidenceTargetKind.CHANGESET,
                        target_id=str(changeset_id),
                        changeset_id=changeset_id,
                        summary="raw log was rejected",
                        source_label="operator-shell",
                        reason="secret-looking-value detected",
                        redaction_findings=["secret-looking-value"],
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ManualEvidenceArchived(
                        evidence_id=replacement_id,
                        reason="manual note became stale after another fixup",
                    ),
                ),
            ],
        )
        repository = SQLiteSessionRepository(connection)
        active = repository.list_manual_evidence(
            session_id=session_id,
            changeset_id=changeset_id,
        )
        all_evidence = repository.list_manual_evidence(
            session_id=session_id,
            changeset_id=changeset_id,
            include_archived=True,
            include_rejected=True,
            include_superseded=True,
        )
        target_evidence = repository.list_manual_evidence(
            session_id=session_id,
            target_kind=ManualEvidenceTargetKind.FEEDBACK,
            target_id=str(feedback_id),
            include_archived=True,
            include_superseded=True,
        )
        superseded = repository.get_manual_evidence(evidence_id)

        with connection:
            connection.execute(
                "delete from manual_evidence where session_id = ?",
                (str(session_id),),
            )
        rebuild_session_projections(connection, session_id)
        rebuilt = repository.get_manual_evidence(evidence_id)
    finally:
        connection.close()

    assert active == []
    assert {item.evidence_id for item in all_evidence} == {
        evidence_id,
        replacement_id,
        rejected_id,
    }
    assert [item.evidence_id for item in target_evidence] == [
        replacement_id,
        evidence_id,
    ]
    assert superseded is not None
    assert superseded.state == ManualEvidenceState.SUPERSEDED
    assert superseded.replacement_evidence_id == replacement_id
    assert superseded.non_claims == ["not retained command evidence"]
    assert rebuilt is not None
    assert rebuilt.state == ManualEvidenceState.SUPERSEDED
