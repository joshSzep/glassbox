"""Integration tests for review feedback projections and query helpers."""

import sqlite3
from pathlib import Path

from glassbox.core import ChangesetCreated
from glassbox.core import EventEnvelope
from glassbox.core import ReviewFeedbackArchived
from glassbox.core import ReviewFeedbackCreated
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackDispositionUpdated
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackReopened
from glassbox.core import ReviewFeedbackResolved
from glassbox.core import ReviewFeedbackRiskAccepted
from glassbox.core import ReviewFeedbackScopeAttached
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.core import SessionStarted
from glassbox.core import new_changeset_id
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
