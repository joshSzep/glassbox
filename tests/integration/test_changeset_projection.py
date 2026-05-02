"""Integration tests for changeset projection schema and rebuild semantics."""

import sqlite3
from pathlib import Path

from glassbox.core import ChangesetCreated
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRefreshed
from glassbox.core import ChangesetReadinessDecided
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetReviewBriefCreated
from glassbox.core import ChangesetRiskLevel
from glassbox.core import ChangesetSourceAttached
from glassbox.core import ChangesetSourceKind
from glassbox.core import ChangesetVerificationPostureUpdated
from glassbox.core import ChangesetVerificationState
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_turn_id
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import append_events
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.store.sqlite import rebuild_session_projections


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def test_changeset_projection_queries_current_state_and_references(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    task_id = new_task_id()
    turn_id = new_turn_id()
    source_session_id = new_session_id()
    inventory_artifact_id = new_artifact_id()
    brief_artifact_id = new_artifact_id()
    verification_id = new_task_verification_id()
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
                        objective="review local changes",
                        summary="adds projection rows",
                        task_id=task_id,
                        turn_id=turn_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetSourceAttached(
                        changeset_id=changeset_id,
                        source_kind=ChangesetSourceKind.SESSION,
                        source_session_id=source_session_id,
                        reason="created from an existing session",
                        limitation="session is imported",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetInventoryRefreshed(
                        changeset_id=changeset_id,
                        artifact_id=inventory_artifact_id,
                        changed_path_count=3,
                        source_digest="sha256:inventory",
                        risk_level=ChangesetRiskLevel.HIGH,
                        risk_summary="runtime schema changed",
                        unresolved_risk_count=2,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetVerificationPostureUpdated(
                        changeset_id=changeset_id,
                        state=ChangesetVerificationState.FAILED,
                        summary="unit test failed",
                        verification_id=verification_id,
                        failed_count=1,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetReviewBriefCreated(
                        changeset_id=changeset_id,
                        artifact_id=brief_artifact_id,
                        inventory_artifact_id=inventory_artifact_id,
                        verification_id=verification_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetReadinessDecided(
                        changeset_id=changeset_id,
                        readiness_kind=ChangesetReadinessKind.COMMIT,
                        state=ChangesetReadinessState.FAILED_CHECKS,
                        reason="verification failed",
                        blockers=["unit test failed"],
                        safe_next_actions=["fix failing test"],
                        inventory_artifact_id=inventory_artifact_id,
                        review_brief_artifact_id=brief_artifact_id,
                        verification_id=verification_id,
                    ),
                ),
            ],
        )
        repository = SQLiteSessionRepository(connection)

        changesets = repository.list_changesets(session_id=session_id)
        changeset = repository.get_changeset(changeset_id)
        sources = repository.list_changeset_sources(session_id, changeset_id)
        inventory = repository.get_changeset_inventory(session_id, changeset_id)
        verification = repository.get_changeset_verification_posture(
            session_id,
            changeset_id,
        )
        briefs = repository.list_changeset_review_briefs(session_id, changeset_id)
        readiness = repository.list_changeset_readiness(session_id, changeset_id)

    finally:
        connection.close()

    assert len(changesets) == 1
    assert changeset is not None
    assert changeset.objective == "review local changes"
    assert changeset.status == "active"
    assert changeset.latest_inventory_artifact_id == inventory_artifact_id
    assert changeset.latest_verification_id == verification_id
    assert changeset.latest_review_brief_artifact_id == brief_artifact_id
    assert changeset.risk_level == ChangesetRiskLevel.HIGH
    assert changeset.risk_summary == "runtime schema changed"
    assert changeset.unresolved_risk_count == 2
    assert changeset.accepted_risk_count == 0
    assert len(sources) == 1
    assert sources[0].source_kind == ChangesetSourceKind.SESSION
    assert sources[0].source_session_id == source_session_id
    assert sources[0].limitation == "session is imported"
    assert inventory is not None
    assert inventory.freshness == ChangesetInventoryFreshness.FRESH
    assert inventory.changed_path_count == 3
    assert inventory.risk_level == ChangesetRiskLevel.HIGH
    assert inventory.unresolved_risk_count == 2
    assert verification is not None
    assert verification.state == ChangesetVerificationState.FAILED
    assert verification.failed_count == 1
    assert [brief.artifact_id for brief in briefs] == [brief_artifact_id]
    assert briefs[0].render_targets == ["markdown", "json"]
    assert len(readiness) == 1
    assert readiness[0].readiness_kind == ChangesetReadinessKind.COMMIT
    assert readiness[0].state == ChangesetReadinessState.FAILED_CHECKS
    assert readiness[0].blockers == ["unit test failed"]


def test_changeset_projection_rebuilds_from_canonical_events(tmp_path: Path) -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
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
                        objective="restore projection",
                    ),
                ),
            ],
        )
        with connection:
            connection.execute(
                "delete from changesets where session_id = ?",
                (str(session_id),),
            )

        rebuild_session_projections(connection, session_id)
        changeset = SQLiteSessionRepository(connection).get_changeset(changeset_id)
    finally:
        connection.close()

    assert changeset is not None
    assert changeset.objective == "restore projection"


def test_changeset_projection_tracks_latest_inventory_after_supersede(
    tmp_path: Path,
) -> None:
    session_id = new_session_id()
    changeset_id = new_changeset_id()
    first_artifact_id = new_artifact_id()
    second_artifact_id = new_artifact_id()
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
                        objective="refresh inventory",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetInventoryRefreshed(
                        changeset_id=changeset_id,
                        artifact_id=first_artifact_id,
                        freshness=ChangesetInventoryFreshness.FRESH,
                        changed_path_count=1,
                        source_digest="sha256:first",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetInventoryRefreshed(
                        changeset_id=changeset_id,
                        artifact_id=first_artifact_id,
                        freshness=ChangesetInventoryFreshness.SUPERSEDED,
                        changed_path_count=1,
                        source_digest="sha256:first",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ChangesetInventoryRefreshed(
                        changeset_id=changeset_id,
                        artifact_id=second_artifact_id,
                        freshness=ChangesetInventoryFreshness.FRESH,
                        changed_path_count=2,
                        source_digest="sha256:second",
                        previous_artifact_id=first_artifact_id,
                    ),
                ),
            ],
        )
        inventory = SQLiteSessionRepository(connection).get_changeset_inventory(
            session_id,
            changeset_id,
        )
        changeset = SQLiteSessionRepository(connection).get_changeset(changeset_id)
    finally:
        connection.close()

    assert inventory is not None
    assert inventory.artifact_id == second_artifact_id
    assert inventory.previous_artifact_id == first_artifact_id
    assert inventory.freshness == ChangesetInventoryFreshness.FRESH
    assert inventory.changed_path_count == 2
    assert changeset is not None
    assert changeset.latest_inventory_artifact_id == second_artifact_id
