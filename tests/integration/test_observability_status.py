"""Integration coverage for workspace observability summaries."""

import json
from pathlib import Path

import pytest

from glassbox.cli import main
from glassbox.core import AutonomyBudget
from glassbox.core import AutonomyBudgetRemaining
from glassbox.core import AutonomyBudgetUsage
from glassbox.core import AutonomyMode
from glassbox.core import BranchCandidateNeedsReview
from glassbox.core import BranchCandidatePlanned
from glassbox.core import BranchCandidateVerified
from glassbox.core import BranchSearchStarted
from glassbox.core import BudgetDecisionRecorded
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import TaskBlockedReason
from glassbox.core import TaskCreated
from glassbox.core import TaskPaused
from glassbox.core import TaskPlanProposed
from glassbox.core import TaskPlanSnapshot
from glassbox.core import TaskStepProposal
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationStarted
from glassbox.core import WorkspaceMemoryCreated
from glassbox.core import WorkspaceMemoryInvalidated
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_step_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_workspace_memory_id
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import BranchCandidateVerificationStatus
from glassbox.core.types import TaskVerificationStatus
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.store.repositories import SQLiteSessionRepository
from tests.integration.fault_test_support import append_representative_completed_session
from tests.integration.fault_test_support import open_initialized_database


def test_observability_status_json_reports_health_lag_and_verification(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    connection = open_initialized_database(tmp_path)
    db_path = tmp_path / "glassbox.sqlite3"
    try:
        ids = append_representative_completed_session(connection, tmp_path)
        with connection:
            connection.execute(
                "delete from session_state where session_id = ?",
                (str(ids.session_id),),
            )
        _write_eval_summary(tmp_path, exit_code=13, failed_case_count=1)
    finally:
        connection.close()

    exit_code = main(
        [
            "observability",
            "status",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["runtime"]["state"] == "not_running"
    assert payload["runtime"]["event_transport"]["state"] == "healthy"
    assert payload["runtime"]["event_transport"]["dropped_events"] == 0
    assert payload["runtime"]["event_transport"]["queue_capacity"] == 64
    assert payload["runtime"]["event_transport"]["queue_pressure"] == 0.0
    assert payload["runtime"]["event_transport"]["last_published_sequence"] is None
    assert payload["runtime"]["event_transport"]["reconnect_mode"].startswith(
        "resume with"
    )
    assert (
        "last observed sequence"
        in payload["runtime"]["event_transport"]["reconnect_hint"]
    )
    assert payload["projections"]["session_count"] == 1
    assert payload["projections"]["degraded_count"] == 1
    assert payload["projections"]["max_lag"] > 0
    assert payload["projections"]["max_rebuild_event_count"] > 0
    assert payload["projections"]["total_rebuild_event_count"] > 0
    assert str(ids.session_id) in payload["projections"]["degraded_sessions"]
    assert payload["tasks"]["task_count"] == 0
    assert payload["tasks"]["budget_exhausted_count"] == 0
    assert payload["background_jobs"]["pending_count"] == 0
    assert payload["background_jobs"]["running_count"] == 0
    assert payload["background_jobs"]["stale_count"] == 0
    assert payload["background_jobs"]["failed_count"] == 0
    assert payload["background_jobs"]["retryable_count"] == 0
    assert payload["background_jobs"]["abandoned_count"] == 0
    assert payload["memory"]["active_count"] == 0
    assert payload["repository_index"]["status"] == "missing"
    assert payload["branch_searches"]["search_count"] == 0
    assert payload["artifacts"]["glassbox_size_bytes"] > 0
    assert payload["artifacts"]["protected_count"] >= 0
    assert payload["artifacts"]["candidate_count"] >= 0
    assert payload["verification"]["latest_suite_status"] == "failed"
    assert payload["verification"]["latest_exit_code"] == 13
    assert payload["verification"]["latest_failed_case_count"] == 1
    assert payload["knowledge_posture"]["overall_status"] in {
        "degraded",
        "missing",
        "stale",
    }
    assert any(
        cue["key"] == "repository-index" for cue in payload["knowledge_posture"]["cues"]
    )
    repository_cue = next(
        cue
        for cue in payload["knowledge_posture"]["cues"]
        if cue["key"] == "repository-index"
    )
    assert repository_cue["provenance"][0]["source_kind"] == "repository-index"
    assert repository_cue["provenance"][0]["path"].endswith("repository-index.json")
    assert "glassbox projection rebuild --all" in payload["next_actions"]


def test_observability_status_text_reports_next_actions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "glassbox.sqlite3"
    connection = open_initialized_database(tmp_path)
    connection.close()

    exit_code = main(
        [
            "observability",
            "status",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Runtime: not_running" in captured.out
    assert "Event transport: healthy" in captured.out
    assert "queue peak 0/64" in captured.out
    assert "Reconnect hint:" in captured.out
    assert "Projections:" in captured.out
    assert "Tasks:" in captured.out
    assert "Background jobs:" in captured.out
    assert "0 failed, 0 retryable, 0 abandoned" in captured.out
    assert "Workspace memory:" in captured.out
    assert "Repository index:" in captured.out
    assert "Branch searches:" in captured.out
    assert "Artifacts:" in captured.out
    assert "Verification: not run" in captured.out
    assert "Knowledge posture:" in captured.out
    assert "provenance:" in captured.out
    assert "Safe workflow summary:" in captured.out
    assert "Daemon: glassbox daemon status --cwd ." in captured.out
    assert "Projections: glassbox projection check --all --cwd ." in captured.out
    assert "Artifacts: glassbox artifacts inspect --cwd ." in captured.out
    assert "Provider: glassbox provider diagnostics --cwd ." in captured.out
    assert "Repository index: glassbox repo index status --cwd ." in captured.out
    assert "Backup before maintenance: glassbox backup create --cwd ." in captured.out
    assert "glassbox eval run" in captured.out


def test_observability_status_json_reports_v8_autonomy_recovery_posture(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    connection = open_initialized_database(tmp_path)
    db_path = tmp_path / "glassbox.sqlite3"
    try:
        ids = _seed_v8_autonomy_recovery_state(connection, tmp_path)
        (tmp_path / "README.md").write_text(
            "index before stale marker\n", encoding="utf-8"
        )
        build_and_write_repository_index(tmp_path)
        (tmp_path / "README.md").write_text(
            "stale after index build\n", encoding="utf-8"
        )
    finally:
        connection.close()

    exit_code = main(
        [
            "observability",
            "status",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["tasks"]["blocked_count"] == 1
    assert payload["tasks"]["budget_exhausted_count"] == 1
    assert payload["tasks"]["verification_failed_count"] == 1
    assert payload["tasks"]["latest_budget_exhausted_task_id"] == str(ids["task_id"])
    assert payload["memory"]["invalidated_count"] == 1
    assert payload["memory"]["last_invalidated_memory_id"] == str(ids["memory_id"])
    assert payload["repository_index"]["status"] == "stale"
    assert payload["repository_index"]["entry_count"] > 0
    assert payload["branch_searches"]["active_count"] == 1
    assert payload["branch_searches"]["needs_review_count"] == 1
    assert payload["branch_searches"]["failed_verification_count"] == 1
    assert f"glassbox task show {ids['task_id']}" in payload["tasks"]["next_actions"]
    assert "glassbox memory list --state invalidated" in payload["next_actions"]
    assert any(
        action.startswith("glassbox repo index build")
        for action in payload["next_actions"]
    )
    assert f"glassbox branch-search show {ids['search_id']}" in payload["next_actions"]


def _write_eval_summary(
    workspace_root: Path,
    *,
    exit_code: int,
    failed_case_count: int,
) -> None:
    output_dir = workspace_root / ".glassbox" / "evals" / "20260425T120000Z"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "profile_id": "push-smoke",
                "selected_case_count": 2,
                "passed_case_count": 1,
                "failed_case_count": failed_case_count,
                "exit_code": exit_code,
            }
        ),
        encoding="utf-8",
    )


def _seed_v8_autonomy_recovery_state(connection, tmp_path: Path) -> dict[str, object]:
    session_id = new_session_id()
    task_id = new_task_id()
    step_id = new_task_step_id()
    verification_id = new_task_verification_id()
    memory_id = new_workspace_memory_id()
    search_id = new_branch_search_id()
    candidate_id = new_branch_candidate_id()
    budget = AutonomyBudget(
        max_steps=1,
        max_tool_calls=1,
        max_write_operations=0,
        max_command_operations=0,
        max_wall_clock_seconds=60,
        max_verification_attempts=1,
        max_branch_attempts=0,
        max_artifact_bytes=1000,
        allowed_risk_buckets=["read_only"],
    )
    repository = SQLiteSessionRepository(connection)
    repository.append_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=SessionStarted(
                    cwd=str(tmp_path),
                    model_name="openai:gpt-5.4",
                    approval_mode="confirm",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskCreated(
                    task_id=task_id,
                    title="Recover blocked autonomy",
                    goal="Record recovery guidance for blocked v8 autonomy.",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskPlanProposed(
                    task_id=task_id,
                    plan=TaskPlanSnapshot(
                        task_id=task_id,
                        title="Recover blocked autonomy",
                        goal="Record recovery guidance for blocked v8 autonomy.",
                        steps=[
                            TaskStepProposal(
                                step_id=step_id,
                                title="Run focused check",
                                order=0,
                            )
                        ],
                    ),
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BudgetDecisionRecorded(
                    scope="task",
                    mode=AutonomyMode.TEST_DRIVEN,
                    budget=budget,
                    usage=AutonomyBudgetUsage(steps=1, verification_attempts=1),
                    remaining=AutonomyBudgetRemaining(
                        steps=0,
                        tool_calls=0,
                        write_operations=0,
                        command_operations=0,
                        wall_clock_seconds=50,
                        verification_attempts=0,
                        branch_attempts=0,
                        artifact_bytes=1000,
                    ),
                    decision="exhausted",
                    task_id=task_id,
                    reason=AutonomyEscalationReason.BUDGET_EXHAUSTED,
                    limit_name="steps",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskVerificationStarted(
                    task_id=task_id,
                    verification_id=verification_id,
                    step_id=step_id,
                    check_name="pytest",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskVerificationCompleted(
                    task_id=task_id,
                    verification_id=verification_id,
                    status=TaskVerificationStatus.FAILED,
                    summary="focused check failed",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskPaused(
                    task_id=task_id,
                    reason=TaskBlockedReason.BUDGET_EXHAUSTED,
                    detail="step budget exhausted",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=WorkspaceMemoryCreated(
                    memory_id=memory_id,
                    kind=WorkspaceMemoryKind.FACT,
                    content="Old fact that must be invalidated.",
                    provenance=WorkspaceMemoryProvenance(
                        source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                        session_id=session_id,
                        source_sequence=1,
                    ),
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=WorkspaceMemoryInvalidated(
                    memory_id=memory_id,
                    reason="superseded during recovery review",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BranchSearchStarted(
                    search_id=search_id,
                    parent_session_id=session_id,
                    objective="Compare recovery strategies",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BranchCandidatePlanned(
                    search_id=search_id,
                    candidate_id=candidate_id,
                    strategy_label="Try minimal recovery",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BranchCandidateVerified(
                    search_id=search_id,
                    candidate_id=candidate_id,
                    verification_status=BranchCandidateVerificationStatus.FAILED,
                    summary="candidate check failed",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BranchCandidateNeedsReview(
                    search_id=search_id,
                    candidate_id=candidate_id,
                    reason="candidate needs operator cleanup",
                ),
            ),
        ]
    )
    return {
        "task_id": task_id,
        "memory_id": memory_id,
        "search_id": search_id,
    }
