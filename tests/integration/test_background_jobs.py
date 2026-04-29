"""Integration coverage for event-sourced background job projections and CLI."""

import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pytest

from glassbox.cli import main
from glassbox.core import BackgroundJobCancelled
from glassbox.core import BackgroundJobFailureKind
from glassbox.core import BackgroundJobKind
from glassbox.core import BackgroundJobRecoveryReason
from glassbox.core import BackgroundJobRecoveryRecorded
from glassbox.core import BackgroundJobState
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_background_job_id
from glassbox.core import new_session_id
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_background_job_projection_rebuilds_all_terminal_and_stale_states(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    completed_id = new_background_job_id()
    failed_id = new_background_job_id()
    cancelled_id = new_background_job_id()
    stale_id = new_background_job_id()

    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        _start_session(repository, session_id, tmp_path)
        completed = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
            job_type="compact-artifacts",
            title="Compact artifacts",
            job_id=completed_id,
        )
        failed = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.DERIVED_INDEX,
            job_type="rebuild-index",
            title="Rebuild index",
            job_id=failed_id,
        )
        cancelled = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.MUTATING_CONTINUATION,
            job_type="continue-session",
            title="Continue session",
            job_id=cancelled_id,
        )
        stale = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
            job_type="scan-workspace",
            title="Scan workspace",
            job_id=stale_id,
        )
        repository.complete_background_job(completed.job_id, summary="done")
        repository.fail_background_job(
            failed.job_id,
            failure_kind=BackgroundJobFailureKind.TOOL_ERROR,
            message="index failed",
        )
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BackgroundJobCancelled(
                    job_id=cancelled.job_id,
                    cancelled_by="runtime",
                    reason="operator requested cancellation",
                ),
            )
        )
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BackgroundJobRecoveryRecorded(
                    job_id=stale.job_id,
                    reason=BackgroundJobRecoveryReason.STALE_CLAIM,
                    previous_state=BackgroundJobState.RUNNING,
                    detail="lease expired",
                ),
            )
        )

        with connection:
            connection.execute("delete from background_jobs")
        repository.rebuild_session_projections(session_id)

        records = {job.job_id: job for job in repository.list_background_jobs()}
    finally:
        connection.close()

    assert records[completed_id].state == BackgroundJobState.COMPLETED
    assert records[failed_id].state == BackgroundJobState.FAILED
    assert records[failed_id].failure_message == "index failed"
    assert records[cancelled_id].state == BackgroundJobState.CANCELLED
    assert records[stale_id].state == BackgroundJobState.STALE
    assert records[stale_id].recovery_reason == BackgroundJobRecoveryReason.STALE_CLAIM


def test_background_job_claim_respects_active_and_stale_leases(tmp_path: Path) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    now = datetime(2026, 4, 25, 12, tzinfo=UTC)

    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        _start_session(repository, session_id, tmp_path)
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
            job_type="scan-workspace",
            title="Scan workspace",
        )
        repository.claim_background_job(
            job.job_id,
            worker_id="worker-a",
            claim_token="claim-a",
            lease_expires_at=now - timedelta(seconds=1),
            now=now,
        )
        reclaimed = repository.claim_background_job(
            job.job_id,
            worker_id="worker-b",
            claim_token="claim-b",
            lease_expires_at=now + timedelta(minutes=5),
            now=now,
        )
    finally:
        connection.close()

    assert reclaimed.worker_id == "worker-b"
    assert reclaimed.claim_token == "claim-b"
    assert reclaimed.attempt == 2


def test_background_job_cancellation_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()

    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        _start_session(repository, session_id, tmp_path)
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
            job_type="scan-workspace",
            title="Scan workspace",
        )
        first = repository.cancel_background_job(job.job_id, reason="stop")
        second = repository.cancel_background_job(job.job_id, reason="stop again")
        events = repository.read_session_events(session_id)
    finally:
        connection.close()

    cancellation_events = [
        event
        for event in events
        if event.event_type == "BackgroundJobCancellationRequested"
    ]
    assert first.state == BackgroundJobState.CANCELLATION_REQUESTED
    assert second.state == BackgroundJobState.CANCELLATION_REQUESTED
    assert len(cancellation_events) == 1


def test_job_cli_lists_shows_and_cancels_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    job_id = _seed_background_job(db_path, tmp_path, session_id)

    list_exit = main(
        [
            "job",
            "list",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    list_payload = json.loads(capsys.readouterr().out)

    show_exit = main(
        [
            "job",
            "show",
            str(job_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    show_payload = json.loads(capsys.readouterr().out)

    cancel_exit = main(
        [
            "job",
            "cancel",
            str(job_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--reason",
            "operator stop",
            "--json",
        ]
    )
    cancel_payload = json.loads(capsys.readouterr().out)

    assert list_exit == 0
    assert [job["job_id"] for job in list_payload] == [str(job_id)]
    assert show_exit == 0
    assert show_payload["job_id"] == str(job_id)
    assert cancel_exit == 0
    assert cancel_payload["state"] == "cancellation_requested"
    assert cancel_payload["cancellation_reason"] == "operator stop"


def _seed_background_job(db_path: Path, workspace_root: Path, session_id) -> object:
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        _start_session(repository, session_id, workspace_root)
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
            job_type="scan-workspace",
            title="Scan workspace",
            payload={"paths": ["src"]},
        )
        return job.job_id
    finally:
        connection.close()


def _start_session(
    repository: SQLiteSessionRepository,
    session_id,
    workspace_root: Path,
) -> None:
    repository.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=SessionStarted(
                cwd=str(workspace_root),
                model_name="openai:gpt-5.4",
                approval_mode="confirm",
            ),
        )
    )
