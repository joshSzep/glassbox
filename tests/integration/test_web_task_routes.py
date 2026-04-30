"""HTTP integration tests for task-plan APIs."""

import asyncio
import sqlite3
from pathlib import Path

import httpx

from glassbox.core import ContinuationWindowRequested
from glassbox.core import ContinuationWindowResolved
from glassbox.core import EventEnvelope
from glassbox.core import LongRunPhase
from glassbox.core import PauseWindowCancelled
from glassbox.core import PauseWindowScheduled
from glassbox.core import SessionStarted
from glassbox.core import TaskCheckpointCreated
from glassbox.core import TaskCreated
from glassbox.core import TaskPlanProposed
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepProposal
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationFailed
from glassbox.core import TaskVerificationPlanned
from glassbox.core import TaskVerificationRetried
from glassbox.core import TaskVerificationStarted
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationFailureDigest
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import new_artifact_id
from glassbox.core import new_session_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.core.types import ApprovalDecision
from glassbox.core.types import TaskPlanStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.core.types import VerificationFailureCategory
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.web import create_app


def test_task_routes_return_pages_and_detail(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            first_task_id = new_task_id()
            second_task_id = new_task_id()
            first_step_id = new_task_step_id()
            second_step_id = new_task_step_id()
            verification_id = new_task_verification_id()
            repo = SQLiteSessionRepository(connection)
            _seed_task(
                repo,
                tmp_path,
                session_id,
                first_task_id,
                [first_step_id, second_step_id],
                verification_id,
                title="First task",
            )
            _seed_task(
                repo,
                tmp_path,
                session_id,
                second_task_id,
                [new_task_step_id()],
                new_task_verification_id(),
                title="Second task",
                start_session=False,
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                list_response = await client.get(
                    "/tasks",
                    params={"session_id": str(session_id), "limit": 1},
                )
                list_next = await client.get(
                    "/tasks",
                    params={"session_id": str(session_id), "cursor": 1, "limit": 1},
                )
                detail_response = await client.get(f"/tasks/{first_task_id}")
                steps_response = await client.get(
                    f"/tasks/{first_task_id}/steps",
                    params={"limit": 1},
                )
                events_response = await client.get(
                    f"/tasks/{first_task_id}/events",
                    params={"limit": 2},
                )

            assert list_response.status_code == 200
            list_body = list_response.json()
            assert list_body["page"] == {
                "cursor": 0,
                "limit": 1,
                "next_cursor": 1,
                "has_more": True,
                "returned_count": 1,
            }
            assert list_body["items"][0]["title"] == "Second task"
            assert list_body["projection_health"]["state"] == "ok"

            assert list_next.status_code == 200
            assert list_next.json()["items"][0]["title"] == "First task"

            assert detail_response.status_code == 200
            detail_body = detail_response.json()
            assert detail_body["task"]["task_id"] == str(first_task_id)
            assert [step["step_id"] for step in detail_body["steps"]] == [
                str(first_step_id),
                str(second_step_id),
            ]
            assert detail_body["verifications"] == [
                {
                    "verification_id": str(verification_id),
                    "check_name": "pytest",
                    "status": "passed",
                    "step_id": str(first_step_id),
                    "summary": "focused tests passed",
                }
            ]
            assert detail_body["verification_summary"]["current_posture"] == "verified"
            assert detail_body["verification_summary"]["latest_success_check_name"] == (
                "pytest"
            )
            assert detail_body["verification_ledger"][0]["verification_id"] == str(
                verification_id
            )
            assert (
                detail_body["verification_ledger"][0]["last_success_sequence"]
                is not None
            )
            assert detail_body["verification_drift"]["posture"] == "unknown"
            assert detail_body["verification_drift"]["error"] is not None
            assert detail_body["last_known_good"]["check_name"] == "pytest"
            assert detail_body["last_known_good"]["evidence_status"] == "unknown"
            assert detail_body["repair_history"]["status"] == "clean"

            assert steps_response.status_code == 200
            steps_body = steps_response.json()
            assert steps_body["page"]["next_cursor"] == 1
            assert steps_body["items"][0]["step_id"] == str(first_step_id)

            assert events_response.status_code == 200
            events_body = events_response.json()
            assert events_body["page"]["next_cursor"] == 3
            assert [event["event_type"] for event in events_body["items"]] == [
                "TaskCreated",
                "TaskPlanProposed",
            ]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_task_detail_reports_last_known_good_and_repair_history(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            task_id = new_task_id()
            step_id = new_task_step_id()
            verification_id = new_task_verification_id()
            failed_verification_id = new_task_verification_id()
            repair_verification_id = new_task_verification_id()
            checkpoint_id = new_task_checkpoint_id()
            artifact_id = new_artifact_id()
            repo = SQLiteSessionRepository(connection)
            _seed_task(
                repo,
                tmp_path,
                session_id,
                task_id,
                [step_id],
                verification_id,
                title="Repair task",
            )
            repo.append_events(
                [
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskCheckpointCreated(
                            checkpoint_id=checkpoint_id,
                            task_id=task_id,
                            objective="Repair task",
                            current_phase=LongRunPhase.VERIFYING,
                            completed_step="initial implementation",
                            next_action="rerun focused tests",
                            verification_status="pytest passed",
                            budget_status="within budget",
                            recovery_guidance="resume from pytest evidence",
                            source_start_sequence=1,
                            source_end_sequence=99,
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskVerificationPlanned(
                            task_id=task_id,
                            verification=VerificationPlanEntry(
                                verification_id=failed_verification_id,
                                check_name="ty check",
                                kind=VerificationCheckKind.TYPECHECK,
                                command=["uv", "run", "ty", "check"],
                                source=VerificationPlanSource.OPERATOR,
                                rationale="type coverage",
                                changed_paths=[
                                    Path("src/glassbox/runtime/task_queries.py")
                                ],
                            ),
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskVerificationFailed(
                            task_id=task_id,
                            verification_id=failed_verification_id,
                            failure=VerificationFailureDigest(
                                category=VerificationFailureCategory.TYPECHECK,
                                summary="task query type gap",
                                exit_code=1,
                                artifact_id=artifact_id,
                            ),
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskVerificationRetried(
                            task_id=task_id,
                            verification_id=failed_verification_id,
                            next_verification_id=repair_verification_id,
                            attempt=2,
                            reason="added typed repair history response",
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskVerificationPlanned(
                            task_id=task_id,
                            verification=VerificationPlanEntry(
                                verification_id=repair_verification_id,
                                check_name="ty check",
                                kind=VerificationCheckKind.TYPECHECK,
                                command=["uv", "run", "ty", "check"],
                                source=VerificationPlanSource.OPERATOR,
                                rationale="type coverage after repair",
                                changed_paths=[
                                    Path("src/glassbox/runtime/task_queries.py")
                                ],
                            ),
                            attempt=2,
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskVerificationCompleted(
                            task_id=task_id,
                            verification_id=repair_verification_id,
                            status=TaskVerificationStatus.PASSED,
                            summary="typecheck passed after repair",
                        ),
                    ),
                ]
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/tasks/{task_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["last_known_good"]["verification_id"] == str(
                repair_verification_id
            )
            assert body["last_known_good"]["checkpoint_id"] == str(checkpoint_id)
            assert body["last_known_good"]["checkpoint_objective"] == "Repair task"
            assert body["repair_history"]["status"] == "repaired"
            assert body["repair_history"]["failure_count"] == 1
            assert body["repair_history"]["retry_count"] == 1
            assert body["repair_history"]["repaired_count"] == 1
            assert body["repair_history"]["attempts"][0]["repaired"] is True
            assert body["repair_history"]["attempts"][0]["failed_summary"] == (
                "task query type gap"
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_task_routes_handle_empty_lists_unknown_ids_and_invalid_pages(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            unknown_task_id = new_task_id()

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                empty_list = await client.get("/tasks")
                unknown_detail = await client.get(f"/tasks/{unknown_task_id}")
                unknown_steps = await client.get(f"/tasks/{unknown_task_id}/steps")
                unknown_events = await client.get(f"/tasks/{unknown_task_id}/events")
                invalid_limit = await client.get("/tasks", params={"limit": 0})
                unknown_session = await client.get(
                    "/tasks",
                    params={"session_id": "00000000-0000-0000-0000-000000000099"},
                )

            assert empty_list.status_code == 200
            assert empty_list.json()["items"] == []
            assert empty_list.json()["projection_health"] is None
            assert unknown_detail.status_code == 404
            assert unknown_steps.status_code == 404
            assert unknown_events.status_code == 404
            assert invalid_limit.status_code == 422
            assert unknown_session.status_code == 404
        finally:
            connection.close()

    asyncio.run(scenario())


def test_task_detail_surfaces_stale_projection_health(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            task_id = new_task_id()
            repo = SQLiteSessionRepository(connection)
            _seed_task(
                repo,
                tmp_path,
                session_id,
                task_id,
                [new_task_step_id()],
                new_task_verification_id(),
            )
            connection.execute(
                "update session_state set last_sequence = 1 where session_id = ?",
                (str(session_id),),
            )
            connection.commit()

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(f"/tasks/{task_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["projection_health"]["state"] == "stale"
            assert body["projection_health"]["degraded"] is True
        finally:
            connection.close()

    asyncio.run(scenario())


def test_task_action_routes_mutate_authoritative_events_and_jobs(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            task_id = new_task_id()
            repo = SQLiteSessionRepository(connection)
            _seed_task(
                repo,
                tmp_path,
                session_id,
                task_id,
                [new_task_step_id()],
                new_task_verification_id(),
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                approve = await client.post(
                    f"/tasks/{task_id}/approve-plan",
                    json={"actor": "qa", "reason": "plan reviewed"},
                )
                detail_after_approve = await client.get(f"/tasks/{task_id}")
                continuation = await client.post(
                    f"/tasks/{task_id}/continue",
                    json={"requested_by": "qa", "reason": "bounded step"},
                )
                pause = await client.post(
                    f"/tasks/{task_id}/pause",
                    json={"actor": "qa", "detail": "waiting on release window"},
                )
                detail_after_pause = await client.get(f"/tasks/{task_id}")
                resume = await client.post(
                    f"/tasks/{task_id}/resume",
                    json={"actor": "qa", "reason": "release window open"},
                )
                budget = await client.post(
                    f"/tasks/{task_id}/budget",
                    json={
                        "actor": "qa",
                        "budget": {
                            "allowed_risk_buckets": ["read_only"],
                            "max_artifact_bytes": 1000,
                            "max_branch_attempts": 0,
                            "max_command_operations": 0,
                            "max_steps": 2,
                            "max_tool_calls": 4,
                            "max_verification_attempts": 1,
                            "max_wall_clock_seconds": 60,
                            "max_write_operations": 0,
                        },
                        "detail": "narrow read-only budget",
                        "mode": "inspect",
                    },
                )
                cancel_job = await client.post(
                    f"/jobs/{continuation.json()['job']['job_id']}/cancel",
                    json={"actor": "qa", "reason": "operator cancelled"},
                )
                cancel_task = await client.post(
                    f"/tasks/{task_id}/cancel",
                    json={"actor": "qa", "reason": "no longer needed"},
                )
                blocked_continue = await client.post(
                    f"/tasks/{task_id}/continue",
                    json={"requested_by": "qa"},
                )

            assert approve.status_code == 200
            assert detail_after_approve.json()["task"]["status"] == "active"
            assert continuation.status_code == 200
            assert continuation.json()["job"]["state"] == "queued"
            assert pause.status_code == 200
            assert detail_after_pause.json()["task"]["status"] == "paused"
            assert detail_after_pause.json()["task"]["blocked_reason"] == "manual_pause"
            assert resume.status_code == 200
            assert budget.status_code == 200
            assert repo.get_budget_posture(session_id, task_id=task_id) is not None
            assert cancel_job.status_code == 200
            assert cancel_job.json()["job"]["state"] == "cancellation_requested"
            assert cancel_task.status_code == 200
            cancelled_task = repo.get_task(task_id)
            assert cancelled_task is not None
            assert cancelled_task.status == TaskPlanStatus.CANCELLED
            assert blocked_continue.status_code == 409
        finally:
            connection.close()

    asyncio.run(scenario())


def test_task_continuation_window_approval_denial_and_overlap(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            task_id = new_task_id()
            repo = SQLiteSessionRepository(connection)
            _seed_task(
                repo,
                tmp_path,
                session_id,
                task_id,
                [new_task_step_id()],
                new_task_verification_id(),
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                denied = await client.post(
                    f"/tasks/{task_id}/continuation-window",
                    json={
                        "decision": "denied",
                        "requested_minutes": 15,
                        "reason": "needs human review",
                    },
                )
                approved = await client.post(
                    f"/tasks/{task_id}/continuation-window",
                    json={
                        "decision": "approved",
                        "requested_minutes": 20,
                        "reason": "bounded continuation",
                    },
                )
                overlap = await client.post(
                    f"/tasks/{task_id}/continuation-window",
                    json={
                        "decision": "approved",
                        "requested_minutes": 5,
                        "reason": "overlap",
                    },
                )

            assert denied.status_code == 200
            denied_body = denied.json()
            assert denied_body["status"] == "denied"
            assert denied_body["job"] is None
            assert denied_body["continuation_window"]["decision"] == "denied"

            assert approved.status_code == 200
            approved_body = approved.json()
            assert approved_body["status"] == "approved"
            assert approved_body["job"]["state"] == "queued"
            assert approved_body["continuation_window"]["approved_until"] is not None

            assert overlap.status_code == 409
            jobs = repo.list_background_jobs()
            assert jobs[-1].payload["continuation_window_minutes"] == 20
            events = repo.read_session_events(session_id)
            request_events = [
                event.payload
                for event in events
                if isinstance(event.payload, ContinuationWindowRequested)
            ]
            resolved_events = [
                event.payload
                for event in events
                if isinstance(event.payload, ContinuationWindowResolved)
            ]
            assert [event.requested_minutes for event in request_events] == [15, 20]
            assert [event.decision for event in resolved_events] == [
                ApprovalDecision.DENIED,
                ApprovalDecision.APPROVED,
            ]
        finally:
            connection.close()

    asyncio.run(scenario())


def test_task_pause_window_schedule_and_manual_override(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            task_id = new_task_id()
            repo = SQLiteSessionRepository(connection)
            _seed_task(
                repo,
                tmp_path,
                session_id,
                task_id,
                [new_task_step_id()],
                new_task_verification_id(),
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                scheduled = await client.post(
                    f"/tasks/{task_id}/pause-window",
                    json={
                        "policy": "before_risky_action",
                        "reason": "review before mutation",
                    },
                )
                pause_window_id = scheduled.json()["pause_window_id"]
                cancelled = await client.post(
                    f"/tasks/{task_id}/pause-window/{pause_window_id}/cancel",
                    json={"reason": "manual override"},
                )

            assert scheduled.status_code == 200
            assert scheduled.json()["policy"] == "before_risky_action"
            assert cancelled.status_code == 200
            assert cancelled.json()["status"] == "cancelled"
            events = repo.read_session_events(session_id)
            assert any(
                isinstance(event.payload, PauseWindowScheduled) for event in events
            )
            assert any(
                isinstance(event.payload, PauseWindowCancelled) for event in events
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context)


def _seed_task(
    repository: SQLiteSessionRepository,
    tmp_path: Path,
    session_id,
    task_id,
    step_ids,
    verification_id,
    *,
    title: str = "Task route coverage",
    start_session: bool = True,
) -> None:
    events = []
    if start_session:
        events.append(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            )
        )
    events.extend(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskCreated(
                    task_id=task_id,
                    title=title,
                    goal="Expose task state through HTTP APIs",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskPlanProposed(
                    task_id=task_id,
                    plan=TaskPlanSnapshot(
                        task_id=task_id,
                        title=title,
                        goal="Expose task state through HTTP APIs",
                        steps=[
                            TaskStepProposal(
                                step_id=step_id,
                                title=f"Step {index}",
                                order=index,
                            )
                            for index, step_id in enumerate(step_ids)
                        ],
                    ),
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskVerificationStarted(
                    task_id=task_id,
                    verification_id=verification_id,
                    step_id=step_ids[0],
                    check_name="pytest",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskVerificationCompleted(
                    task_id=task_id,
                    verification_id=verification_id,
                    status=TaskVerificationStatus.PASSED,
                    summary="focused tests passed",
                ),
            ),
        ]
    )
    repository.append_events(events)
