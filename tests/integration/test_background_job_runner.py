"""Integration coverage for daemon read-only background job runner."""

import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import cast

import pytest

from glassbox.core import ApprovalRequested
from glassbox.core import AutonomyMode
from glassbox.core import BackgroundJobKind
from glassbox.core import BackgroundJobState
from glassbox.core import ContinuationWindowExpired
from glassbox.core import EventEnvelope
from glassbox.core import PauseWindowPolicy
from glassbox.core import PauseWindowTriggered
from glassbox.core import RuntimeNoteRecorded
from glassbox.core import SessionStarted
from glassbox.core import TaskCreated
from glassbox.core import TaskPlanProposed
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepProposal
from glassbox.core import new_approval_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_turn_id
from glassbox.runtime.autonomy import default_budget_for_autonomy_mode
from glassbox.runtime.background_jobs import run_background_job_worker_loop
from glassbox.runtime.background_jobs import run_background_job_worker_once
from glassbox.runtime.background_jobs import run_background_job_worker_once_async
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.pause_windows import schedule_pause_window
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.workspace_topology import load_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path
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


def test_worker_refreshes_repository_index(tmp_path: Path) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n",
        encoding="utf-8",
    )

    _seed_session(db_path, tmp_path, session_id)
    with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.DERIVED_INDEX,
            job_type="repository-index-refresh",
            title="Refresh repository index",
        )

        tick = run_background_job_worker_once(
            runtime_context,
            worker_id="test-worker",
        )
        updated = repository.get_background_job(job.job_id)
        snapshot = load_repository_index(tmp_path)

    assert tick.claimed_count == 1
    assert tick.completed_count == 1
    assert updated is not None
    assert updated.state == BackgroundJobState.COMPLETED
    assert repository_index_path(tmp_path).exists()
    assert any(entry.symbol == "UsefulThing" for entry in snapshot.entries)
    assert updated.progress_message is not None
    assert "Repository index refresh wrote" in updated.progress_message


def test_worker_refreshes_repository_intelligence_snapshots(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\n',
        encoding="utf-8",
    )

    _seed_session(db_path, tmp_path, session_id)
    with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.DERIVED_INDEX,
            job_type="repository-intelligence-refresh",
            title="Refresh repository intelligence",
        )

        tick = run_background_job_worker_once(
            runtime_context,
            worker_id="test-worker",
        )
        updated = repository.get_background_job(job.job_id)
        index_snapshot = load_repository_index(tmp_path)
        topology_snapshot = load_workspace_topology(tmp_path)

    assert tick.claimed_count == 1
    assert tick.completed_count == 1
    assert updated is not None
    assert updated.state == BackgroundJobState.COMPLETED
    assert repository_index_path(tmp_path).exists()
    assert workspace_topology_path(tmp_path).exists()
    assert any(entry.symbol == "UsefulThing" for entry in index_snapshot.entries)
    assert {component.component_id for component in topology_snapshot.components} >= {
        "package:fixture",
    }
    assert updated.progress_message is not None
    assert "Repository intelligence refresh wrote" in updated.progress_message
    assert "Summary artifact:" in updated.progress_message
    artifact_path = updated.progress_message.rsplit("Summary artifact: ", 1)[1].rstrip(
        "."
    )
    artifact_text = (tmp_path / artifact_path).read_text(encoding="utf-8")
    assert "source_mutation: none" in artifact_text
    assert "policy_mutation: none" in artifact_text
    assert "command_recipes_authority: advisory" in artifact_text
    assert "release_authority: deterministic" in artifact_text


def test_worker_scans_workspace_memory_candidates(tmp_path: Path) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()

    _seed_session(db_path, tmp_path, session_id)
    with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=RuntimeNoteRecorded(
                    category="operator",
                    message="Prefer uv run pytest for backend tests.",
                ),
            )
        )
        job = repository.enqueue_background_job(
            session_id,
            kind=BackgroundJobKind.DERIVED_INDEX,
            job_type="workspace-memory-candidate-scan",
            title="Scan workspace memory candidates",
            payload={"session_id": str(session_id), "max_candidates": 5},
        )

        tick = run_background_job_worker_once(
            runtime_context,
            worker_id="test-worker",
        )
        updated = repository.get_background_job(job.job_id)

    assert tick.claimed_count == 1
    assert tick.completed_count == 1
    assert updated is not None
    assert updated.state == BackgroundJobState.COMPLETED
    assert updated.progress_message is not None
    assert "Workspace memory candidate scan found 1" in updated.progress_message


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


def test_async_worker_runs_one_task_continuation_step(tmp_path: Path) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    _seed_task(
        db_path,
        tmp_path,
        session_id,
        task_id,
        step_id,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
    )

    async def run_once() -> None:
        with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
            repository = runtime_context.repositories.sessions
            job = repository.enqueue_background_job(
                session_id,
                kind=BackgroundJobKind.MUTATING_CONTINUATION,
                job_type="task-continuation-step",
                title="Continue task",
                payload={"task_id": str(task_id)},
                task_id=task_id,
            )
            tick = await run_background_job_worker_once_async(
                runtime_context,
                worker_id="test-worker",
            )
            updated_job = repository.get_background_job(job.job_id)
            task_repository = cast(TaskPlanRepository, repository)
            steps = task_repository.list_task_steps(session_id, task_id)
            task = task_repository.get_task(task_id)
            messages = repository.list_transcript_messages(session_id)

        assert tick.claimed_count == 1
        assert tick.completed_count == 1
        assert updated_job is not None
        assert updated_job.state == BackgroundJobState.COMPLETED
        assert task is not None
        assert task.status.value == "completed"
        assert steps[0].status.value == "completed"
        assert any(
            "Continue task" in part.text
            for message in messages
            for part in message.parts
        )

    asyncio.run(run_once())


def test_async_worker_pauses_continuation_without_explicit_budget(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    _seed_task(db_path, tmp_path, session_id, task_id, step_id)

    async def run_once() -> None:
        with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
            repository = runtime_context.repositories.sessions
            job = repository.enqueue_background_job(
                session_id,
                kind=BackgroundJobKind.MUTATING_CONTINUATION,
                job_type="task-continuation-step",
                title="Continue task",
                task_id=task_id,
            )
            await run_background_job_worker_once_async(
                runtime_context,
                worker_id="test-worker",
            )
            updated_job = repository.get_background_job(job.job_id)
            task = cast(TaskPlanRepository, repository).get_task(task_id)

        assert updated_job is not None
        assert updated_job.state == BackgroundJobState.COMPLETED
        assert task is not None
        assert task.status.value == "paused"
        assert task.blocked_reason is not None
        assert task.blocked_reason.value == "budget_exhausted"

    asyncio.run(run_once())


def test_async_worker_stops_expired_continuation_window(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    approval_id = new_approval_id()
    expired_at = datetime(2026, 4, 29, 10, tzinfo=UTC)
    _seed_task(
        db_path,
        tmp_path,
        session_id,
        task_id,
        step_id,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
    )

    async def run_once() -> None:
        with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
            repository = runtime_context.repositories.sessions
            job = repository.enqueue_background_job(
                session_id,
                kind=BackgroundJobKind.MUTATING_CONTINUATION,
                job_type="task-continuation-step",
                title="Continue task",
                task_id=task_id,
                payload={
                    "continuation_window_approval_id": str(approval_id),
                    "continuation_window_approved_until": expired_at.isoformat(),
                    "continuation_window_minutes": 10,
                    "task_id": str(task_id),
                },
            )
            await run_background_job_worker_once_async(
                runtime_context,
                worker_id="test-worker",
            )
            updated_job = repository.get_background_job(job.job_id)
            task = cast(TaskPlanRepository, repository).get_task(task_id)
            events = repository.read_session_events(session_id)

        assert updated_job is not None
        assert updated_job.state == BackgroundJobState.COMPLETED
        assert task is not None
        assert task.status.value == "paused"
        assert task.blocked_reason is not None
        assert task.blocked_reason.value == "continuation_window_expired"
        expiry = next(
            event.payload
            for event in events
            if isinstance(event.payload, ContinuationWindowExpired)
        )
        assert expiry.approval_id == approval_id
        assert expiry.job_id == job.job_id

    asyncio.run(run_once())


def test_async_worker_honors_scheduled_pause_before_risky_action(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    _seed_task(
        db_path,
        tmp_path,
        session_id,
        task_id,
        step_id,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
    )
    pause_event = schedule_pause_window(
        scope="task",
        task_id=task_id,
        policy=PauseWindowPolicy.BEFORE_RISKY_ACTION,
        reason="operator wants review before mutation",
    )
    connection = open_database(db_path)
    try:
        SQLiteSessionRepository(connection).append_event(
            EventEnvelope(session_id=session_id, sequence=0, payload=pause_event)
        )
    finally:
        connection.close()

    async def run_once() -> None:
        with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
            repository = runtime_context.repositories.sessions
            job = repository.enqueue_background_job(
                session_id,
                kind=BackgroundJobKind.MUTATING_CONTINUATION,
                job_type="task-continuation-step",
                title="Continue task",
                task_id=task_id,
            )
            await run_background_job_worker_once_async(
                runtime_context,
                worker_id="test-worker",
            )
            updated_job = repository.get_background_job(job.job_id)
            task = cast(TaskPlanRepository, repository).get_task(task_id)
            events = repository.read_session_events(session_id)

        assert updated_job is not None
        assert updated_job.state == BackgroundJobState.COMPLETED
        assert task is not None
        assert task.blocked_reason is not None
        assert task.blocked_reason.value == "scheduled_pause"
        triggered = next(
            event.payload
            for event in events
            if isinstance(event.payload, PauseWindowTriggered)
        )
        assert triggered.pause_window_id == pause_event.pause_window_id
        assert triggered.job_id == job.job_id

    asyncio.run(run_once())


def test_async_worker_pauses_continuation_for_pending_approval(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    _seed_task(
        db_path,
        tmp_path,
        session_id,
        task_id,
        step_id,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
    )
    connection = open_database(db_path)
    try:
        SQLiteSessionRepository(connection).append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=ApprovalRequested(
                    approval_id=new_approval_id(),
                    turn_id=new_turn_id(),
                    reason="needs approval",
                    subject="tool call",
                ),
            )
        )
    finally:
        connection.close()

    async def run_once() -> None:
        with open_runtime_context(tmp_path, db_path=db_path) as runtime_context:
            repository = runtime_context.repositories.sessions
            job = repository.enqueue_background_job(
                session_id,
                kind=BackgroundJobKind.MUTATING_CONTINUATION,
                job_type="task-continuation-step",
                title="Continue task",
                task_id=task_id,
            )
            await run_background_job_worker_once_async(
                runtime_context,
                worker_id="test-worker",
            )
            updated_job = repository.get_background_job(job.job_id)
            task = cast(TaskPlanRepository, repository).get_task(task_id)

        assert updated_job is not None
        assert updated_job.state == BackgroundJobState.COMPLETED
        assert task is not None
        assert task.status.value == "paused"
        assert task.blocked_reason is not None
        assert task.blocked_reason.value == "awaiting_approval"

    asyncio.run(run_once())


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


def _seed_task(
    db_path: Path,
    workspace_root: Path,
    session_id,
    task_id,
    step_id,
    *,
    autonomy_mode: AutonomyMode = AutonomyMode.MANUAL,
) -> None:
    connection = open_database(db_path)
    try:
        initialize_database(connection)
        repository = SQLiteSessionRepository(connection)
        budget = None
        budget_preset = None
        if autonomy_mode != AutonomyMode.MANUAL:
            budget = default_budget_for_autonomy_mode(autonomy_mode)
            budget_preset = autonomy_mode.value
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=SessionStarted(
                        cwd=str(workspace_root),
                        model_name="openai:gpt-5.4",
                        approval_mode="confirm",
                        autonomy_mode=autonomy_mode,
                        autonomy_budget=budget,
                        autonomy_budget_preset=budget_preset,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskCreated(
                        task_id=task_id,
                        title="Continue task",
                        goal="Exercise one background continuation step",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskPlanProposed(
                        task_id=task_id,
                        plan=TaskPlanSnapshot(
                            task_id=task_id,
                            title="Continue task",
                            goal="Exercise one background continuation step",
                            steps=[
                                TaskStepProposal(
                                    step_id=step_id,
                                    title="Run one bounded step",
                                    order=0,
                                )
                            ],
                        ),
                    ),
                ),
            ]
        )
    finally:
        connection.close()
