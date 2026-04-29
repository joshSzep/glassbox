"""Integration coverage for daemon read-only background job runner."""

import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pytest

from glassbox.core import BackgroundJobKind
from glassbox.core import BackgroundJobState
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import new_session_id
from glassbox.runtime.background_jobs import run_background_job_worker_loop
from glassbox.runtime.background_jobs import run_background_job_worker_once
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_worker_completes_projection_health_refresh_job(tmp_path: Path) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()

    _seed_session(db_path, tmp_path, session_id)
    with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
            job_type="projection-health-refresh",
            title="Refresh projection health",
        )

        tick = run_background_job_worker_once(
            runtime_context,
            worker_id="test-worker",
            now=datetime(2026, 4, 25, 12, tzinfo=UTC),
        )
        updated = repository.get_background_job(job.job_id)
        events = repository.read_session_events(session_id)

    assert tick.claimed_count == 1
    assert tick.completed_count == 1
    assert tick.failed_count == 0
    assert updated is not None
    assert updated.state == BackgroundJobState.COMPLETED
    assert updated.progress_message is not None
    assert "Projection health refresh inspected" in updated.progress_message
    assert [
        event.event_type
        for event in events
        if event.event_type.startswith("BackgroundJob")
    ] == [
        "BackgroundJobCreated",
        "BackgroundJobClaimed",
        "BackgroundJobHeartbeat",
        "BackgroundJobProgressRecorded",
        "BackgroundJobCompleted",
    ]


def test_worker_recovers_stale_claim_and_blocks_duplicate_claim(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    now = datetime(2026, 4, 25, 12, tzinfo=UTC)

    _seed_session(db_path, tmp_path, session_id)
    with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
            job_type="projection-health-refresh",
            title="Refresh projection health",
        )
        repository.claim_background_job(
            job.job_id,
            worker_id="worker-a",
            claim_token="claim-a",
            lease_expires_at=now + timedelta(minutes=5),
            now=now,
        )
        with pytest.raises(ValueError, match="already claimed"):
            repository.claim_background_job(
                job.job_id,
                worker_id="worker-b",
                claim_token="claim-b",
                lease_expires_at=now + timedelta(minutes=10),
                now=now,
            )

        tick = run_background_job_worker_once(
            runtime_context,
            worker_id="test-worker",
            now=now + timedelta(minutes=6),
        )
        updated = repository.get_background_job(job.job_id)

    assert tick.recovered_stale_count == 1
    assert updated is not None
    assert updated.state == BackgroundJobState.STALE


def test_worker_acknowledges_requested_cancellation(tmp_path: Path) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()

    _seed_session(db_path, tmp_path, session_id)
    with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
            job_type="projection-health-refresh",
            title="Refresh projection health",
        )
        repository.cancel_background_job(job.job_id, reason="stop before running")

        tick = run_background_job_worker_once(
            runtime_context,
            worker_id="test-worker",
        )
        updated = repository.get_background_job(job.job_id)

    assert tick.cancelled_count == 1
    assert updated is not None
    assert updated.state == BackgroundJobState.CANCELLED
    assert updated.cancelled_by == "test-worker"


def test_worker_fails_unknown_read_only_job_type(tmp_path: Path) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()

    _seed_session(db_path, tmp_path, session_id)
    with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
            job_type="unknown-job",
            title="Unknown job",
        )

        tick = run_background_job_worker_once(
            runtime_context,
            worker_id="test-worker",
        )
        updated = repository.get_background_job(job.job_id)

    assert tick.claimed_count == 1
    assert tick.failed_count == 1
    assert updated is not None
    assert updated.state == BackgroundJobState.FAILED
    assert updated.failure_message == (
        "unsupported read-only background job type: unknown-job"
    )


def test_worker_loop_stops_cleanly(tmp_path: Path) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    _seed_session(db_path, tmp_path, session_id)

    async def run_loop() -> None:
        with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
            stop_event = asyncio.Event()
            task = asyncio.create_task(
                run_background_job_worker_loop(
                    runtime_context,
                    stop_event=stop_event,
                    worker_id="test-worker",
                    poll_interval_seconds=0.01,
                )
            )
            await asyncio.sleep(0)
            stop_event.set()
            await asyncio.wait_for(task, timeout=1)

    asyncio.run(run_loop())


def _seed_session(db_path: Path, workspace_root: Path, session_id) -> None:
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
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
    finally:
        connection.close()
