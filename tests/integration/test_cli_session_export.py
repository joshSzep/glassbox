"""Integration tests for portable session handoff export."""

import json
from pathlib import Path
from uuid import UUID

import pytest

from glassbox.cli import main
from glassbox.core import AutonomyBudgetRemaining
from glassbox.core import AutonomyBudgetUsage
from glassbox.core import BranchCandidatePlanned
from glassbox.core import BranchCandidateSelected
from glassbox.core import BranchSearchStarted
from glassbox.core import BudgetDecisionRecorded
from glassbox.core import ContextCompactionCreated
from glassbox.core import ContextCompactionFreshness
from glassbox.core import ContextCompactionScope
from glassbox.core import LongRunPhase
from glassbox.core import TaskCheckpointCreated
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationPlanned
from glassbox.core import TaskVerificationResidualRiskAccepted
from glassbox.core import TaskVerificationStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import new_artifact_id
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.core import new_context_compaction_id
from glassbox.core import new_task_checkpoint_id
from glassbox.core import new_task_verification_id
from glassbox.core.events import EventEnvelope
from glassbox.core.ids import new_turn_id
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import AutonomyMode
from glassbox.runtime.autonomy import default_budget_for_autonomy_mode
from glassbox.runtime.session_export import SESSION_EXPORT_KIND
from glassbox.runtime.session_export import SESSION_EXPORT_VERSION
from glassbox.runtime.session_export import SessionExportPayload
from glassbox.runtime.task_plan_capture import capture_task_plan_proposal
from glassbox.store.repositories import SQLiteSessionRepository
from glassbox.store.sqlite import open_database
from tests.integration.cli_test_support import _completed_turn_ids
from tests.integration.cli_test_support import _run_baseline_session
from tests.integration.cli_test_support import _seed_pending_approval


def test_cli_session_export_writes_redacted_live_handoff_package(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = f"Inspect {tmp_path} with OPENAI_API_KEY=sk-secret-session-export"
    db_path, session_id = _run_baseline_session(tmp_path, prompt=prompt)
    output_path = tmp_path / "exports" / "live-session.json"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--exported-by",
            "alice",
            "--recipient",
            "carol",
            "--expected-custodian",
            "bob",
            "--intent",
            "future-self",
            "--format",
            "json",
            "--note",
            f"handoff from {tmp_path}",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    raw_package = output_path.read_text(encoding="utf-8")
    payload = SessionExportPayload.model_validate_json(raw_package)

    assert exit_code == 0
    assert f"Exported session handoff package for {session_id}" in captured.out
    assert payload.export_kind == SESSION_EXPORT_KIND
    assert payload.export_version == SESSION_EXPORT_VERSION
    assert payload.metadata.session_id == session_id
    assert payload.metadata.status == "running"
    assert payload.metadata.workspace.cwd == "<workspace-root>"
    assert payload.handoff.intent == "future-self"
    assert payload.handoff.recipient == "carol"
    assert payload.handoff.exported_by == "alice"
    assert payload.handoff.expected_custodian == "bob"
    assert payload.profile is not None
    assert payload.profile.profile_id == "future-self"
    assert "future_self_context" in payload.profile.required_sections
    assert payload.local_only_inventory is not None
    assert payload.local_only_inventory.intent == "future-self"
    assert payload.handoff.live_actionable is True
    assert payload.handoff.historical_only is False
    assert payload.artifact_references
    assert str(tmp_path) not in raw_package
    assert "sk-secret-session-export" not in raw_package
    assert "OPENAI_API_KEY=<redacted>" in raw_package


def test_cli_session_export_preview_reports_redaction_without_writing_package(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = f"Preview {tmp_path} with OPENAI_API_KEY=sk-preview-secret"
    db_path, session_id = _run_baseline_session(tmp_path, prompt=prompt)
    output_path = tmp_path / "exports" / "preview-session.json"
    _ = capsys.readouterr()

    preview_exit = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--note",
            f"preview from {tmp_path}",
            "--preview",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    preview = json.loads(capsys.readouterr().out)

    assert preview_exit == 0
    assert not output_path.exists()
    assert preview["source"]["kind"] == "session"
    assert "transcript" in preview["included_sections"]
    assert "artifact_references" in preview["included_sections"]
    assert preview["redaction"]["redacted_field_count"] > 0
    assert "workspace-path" in preview["redaction"]["redacted_categories"]
    assert "secret-like-token" in preview["redaction"]["redacted_categories"]
    assert "raw artifact contents" in preview["omitted_raw_categories"]
    assert preview["local_only_inventory"]["total_count"] >= 1
    assert "raw command logs" in preview["local_only_inventory"]["category_counts"]

    export_exit = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--note",
            f"preview from {tmp_path}",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    export_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert export_exit == 0
    assert set(preview["included_sections"]) == {
        key
        for key, value in export_payload.items()
        if value is not None and value != [] and value != {}
    }


def test_cli_session_export_captures_paused_approval_handoff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id, approval_id = _seed_pending_approval(tmp_path)
    output_path = tmp_path / "paused-session.json"
    _ = capsys.readouterr()

    exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--note",
            "approval handoff ANTHROPIC_API_KEY=secret-value",
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    command_payload = json.loads(captured.out)
    raw_package = output_path.read_text(encoding="utf-8")
    payload = SessionExportPayload.model_validate_json(raw_package)

    assert exit_code == 0
    assert command_payload == {
        "path": str(output_path.resolve()),
        "session_id": str(session_id),
    }
    assert payload.metadata.status == "awaiting_approval"
    assert payload.handoff.pending_approval_id == str(approval_id)
    assert payload.handoff.next_action_summary == "Resolve pending approval"
    assert payload.pending_approvals[0].approval_id == approval_id
    assert payload.pending_approvals[0].subject == "run shell command"
    assert len(payload.policy_decisions) == 1
    decision = payload.policy_decisions[0]
    assert decision.event_type == "ApprovalRequested"
    assert decision.approval_id == str(approval_id)
    assert decision.subject == "run shell command"
    assert decision.trace.outcome == "approve"
    assert decision.trace.risk_level == "command"
    assert decision.trace.source_kind == "default"
    assert decision.trace.source_label == "command"
    assert decision.trace.reason == "needs confirmation"
    assert "secret-value" not in raw_package
    assert "ANTHROPIC_API_KEY=<redacted>" in raw_package


def test_cli_session_export_includes_autonomy_budget_posture(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    budget = default_budget_for_autonomy_mode(AutonomyMode.EDIT_SAFE)
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=BudgetDecisionRecorded(
                    scope="session",
                    mode=AutonomyMode.EDIT_SAFE,
                    budget=budget,
                    usage=AutonomyBudgetUsage(
                        steps=2,
                        tool_calls=3,
                        write_operations=1,
                        command_operations=0,
                        wall_clock_seconds=12,
                        verification_attempts=0,
                        branch_attempts=0,
                        artifact_bytes=32,
                    ),
                    remaining=AutonomyBudgetRemaining(
                        steps=1,
                        tool_calls=2,
                        write_operations=0,
                        command_operations=0,
                        wall_clock_seconds=30,
                        verification_attempts=0,
                        branch_attempts=0,
                        artifact_bytes=256,
                    ),
                    decision="exhausted",
                    reason=AutonomyEscalationReason.BUDGET_EXHAUSTED,
                    limit_name="write_operations",
                ),
            )
        )
    finally:
        connection.close()

    output_path = tmp_path / "budget-session.json"
    _ = capsys.readouterr()
    exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    payload = SessionExportPayload.model_validate_json(
        output_path.read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert payload.autonomy_budget_posture is not None
    assert payload.autonomy_budget_posture.mode == AutonomyMode.EDIT_SAFE
    assert payload.autonomy_budget_posture.last_reason == "budget_exhausted"
    assert payload.autonomy_budget_posture.last_limit_name == "write_operations"
    assert payload.handoff.next_action_summary == (
        "Review budget exhaustion and choose a smaller next step or override"
    )


def test_cli_session_export_includes_branch_search_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    search_id = new_branch_search_id()
    candidate_id = new_branch_candidate_id()
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchSearchStarted(
                        search_id=search_id,
                        parent_session_id=session_id,
                        objective="Compare handoff branches",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchCandidatePlanned(
                        search_id=search_id,
                        candidate_id=candidate_id,
                        strategy_label="selected strategy",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=BranchCandidateSelected(
                        search_id=search_id,
                        candidate_id=candidate_id,
                        reason="best verification evidence",
                    ),
                ),
            ]
        )
    finally:
        connection.close()

    output_path = tmp_path / "branch-search-session.json"
    _ = capsys.readouterr()
    exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    payload = SessionExportPayload.model_validate_json(
        output_path.read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert payload.branch_search_summaries[0].search.search_id == search_id
    assert (
        payload.branch_search_summaries[0].search.selected_candidate_id == candidate_id
    )
    assert (
        payload.branch_search_summaries[0].candidates[0].selection_state == "selected"
    )


def test_cli_session_export_captures_branched_session_lineage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, parent_session_id = _run_baseline_session(
        tmp_path,
        prompt="Prepare a handoff branch",
    )
    fork_turn_id = _completed_turn_ids(db_path, parent_session_id)[0]
    _ = capsys.readouterr()

    fork_exit_code = main(
        [
            "session",
            "fork",
            str(parent_session_id),
            "--turn",
            str(fork_turn_id),
            "--branch-label",
            "handoff branch",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    _ = capsys.readouterr()
    child_session_id = _single_child_session_id(db_path, parent_session_id)
    output_path = tmp_path / "branched-session.json"

    export_exit_code = main(
        [
            "session",
            "export",
            str(child_session_id),
            str(output_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    payload = SessionExportPayload.model_validate_json(
        output_path.read_text(encoding="utf-8")
    )

    assert fork_exit_code == 0
    assert export_exit_code == 0
    assert payload.metadata.session_id == child_session_id
    assert payload.lineage.parent_session_id == parent_session_id
    assert payload.lineage.forked_from_turn_id == str(fork_turn_id)
    assert payload.lineage.branch_label == "handoff branch"
    assert payload.lineage.child_sessions == []
    assert payload.transcript
    assert payload.event_count >= len(payload.events)


def test_cli_session_export_import_preserves_task_plans_for_inspection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _seed_proposed_task(tmp_path)
    output_path = tmp_path / "task-session.json"
    _ = capsys.readouterr()

    export_exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    raw_package = output_path.read_text(encoding="utf-8")
    payload = SessionExportPayload.model_validate_json(raw_package)
    _ = capsys.readouterr()

    import_exit_code = main(
        [
            "session",
            "import",
            str(output_path),
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    captured = capsys.readouterr()
    import_payload = json.loads(captured.out)
    imported_session_id = UUID(import_payload["imported_session_id"])
    imported_tasks = _tasks_for_session(db_path, imported_session_id)
    imported_events = _read_task_events(db_path, imported_session_id)

    assert export_exit_code == 0
    assert import_exit_code == 0
    assert payload.task_summaries[0].title == "Inspect <workspace-root>"
    assert payload.task_summaries[0].blocked_reason is None
    assert payload.task_step_summaries[0].title == "Audit inputs"
    assert payload.task_verification_summaries == []
    assert [event.event_type for event in payload.task_event_references] == [
        "TaskCreated",
        "TaskPlanProposed",
    ]
    assert str(tmp_path) not in raw_package
    assert "secret-task-export" not in raw_package
    assert "OPENAI_API_KEY=<redacted>" in raw_package
    assert import_payload["import_mode"] == "inspect"
    assert import_payload["imported_status"] == "completed"
    assert import_payload["resumable"] is False
    assert import_payload["task_count"] == 1
    assert import_payload["task_event_count"] == 2
    assert len(imported_tasks) == 1
    assert imported_tasks[0].title == "Inspect <workspace-root>"
    assert imported_tasks[0].status == "proposed"
    assert [event.event_type for event in imported_events] == [
        "TaskCreated",
        "TaskPlanProposed",
    ]


def test_cli_session_export_import_preserves_checkpoints_for_inspection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _run_baseline_session(tmp_path)
    checkpoint_id = new_task_checkpoint_id()
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskCheckpointCreated(
                    checkpoint_id=checkpoint_id,
                    objective=f"Finish handoff for {tmp_path}",
                    current_phase=LongRunPhase.CHECKPOINTING,
                    completed_step="Captured checkpoint projection",
                    next_action="Import checkpoint package",
                    recovery_guidance=f"Resume after reviewing {tmp_path}",
                    touched_files=[str(tmp_path / "src" / "app.py")],
                    verification_status="pending",
                    budget_status="within budget",
                    source_start_sequence=1,
                    source_end_sequence=3,
                ),
            )
        )
    finally:
        connection.close()

    output_path = tmp_path / "checkpoint-session.json"
    _ = capsys.readouterr()
    export_exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    raw_package = output_path.read_text(encoding="utf-8")
    payload = SessionExportPayload.model_validate_json(raw_package)
    _ = capsys.readouterr()

    import_exit_code = main(
        [
            "session",
            "import",
            str(output_path),
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    import_payload = json.loads(capsys.readouterr().out)
    imported_session_id = UUID(import_payload["imported_session_id"])
    imported_checkpoints = _checkpoints_for_session(db_path, imported_session_id)

    assert export_exit_code == 0
    assert import_exit_code == 0
    assert payload.handoff.latest_checkpoint is not None
    assert payload.handoff.latest_checkpoint.checkpoint_id == checkpoint_id
    assert payload.checkpoint_history[0].objective == (
        "Finish handoff for <workspace-root>"
    )
    assert payload.checkpoint_history[0].touched_files == [
        "<workspace-root>/src/app.py"
    ]
    assert [event.event_type for event in payload.checkpoint_event_references] == [
        "TaskCheckpointCreated"
    ]
    assert str(tmp_path) not in raw_package
    assert import_payload["checkpoint_event_count"] == 1
    assert len(imported_checkpoints) == 1
    assert imported_checkpoints[0].checkpoint_id == checkpoint_id
    assert imported_checkpoints[0].objective == "Finish handoff for <workspace-root>"


def test_cli_session_export_includes_v11_handoff_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path, session_id = _seed_proposed_task(tmp_path)
    task_id = _tasks_for_session(db_path, session_id)[0].task_id
    checkpoint_id = new_task_checkpoint_id()
    verification_id = new_task_verification_id()
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskCheckpointCreated(
                        checkpoint_id=checkpoint_id,
                        objective=f"Finish handoff summary for {tmp_path}",
                        current_phase=LongRunPhase.CHECKPOINTING,
                        completed_step="Prepared reviewer context",
                        next_action="Review summary export",
                        recovery_guidance="Inspect exported handoff summary first",
                        touched_files=[str(tmp_path / "docs" / "handoff.md")],
                        verification_status="passed",
                        budget_status="within budget",
                        source_start_sequence=1,
                        source_end_sequence=4,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ContextCompactionCreated(
                        compaction_id=new_context_compaction_id(),
                        scope=ContextCompactionScope.TRANSCRIPT,
                        source_start_sequence=1,
                        source_end_sequence=4,
                        summary="Reviewer summary with accepted risk context",
                        artifact_id=new_artifact_id(),
                        freshness=ContextCompactionFreshness.FRESH,
                        task_id=task_id,
                        checkpoint_id=checkpoint_id,
                        accepted_risk_count=1,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=VerificationPlanEntry(
                            verification_id=verification_id,
                            check_name="pytest handoff",
                            kind=VerificationCheckKind.TEST,
                            command=[
                                "uv",
                                "run",
                                "pytest",
                                "tests/integration/test_cli_session_export.py",
                            ],
                            source=VerificationPlanSource.OPERATOR,
                            rationale="handoff summary coverage",
                        ),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationCompleted(
                        task_id=task_id,
                        verification_id=verification_id,
                        status=TaskVerificationStatus.PASSED,
                        summary="handoff summary test passed",
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationResidualRiskAccepted(
                        task_id=task_id,
                        verification_id=verification_id,
                        reason=f"accepted local evidence gap near {tmp_path}",
                        residual_risks=[f"manual reviewer still inspects {tmp_path}"],
                    ),
                ),
            ]
        )
    finally:
        connection.close()

    output_path = tmp_path / "summary-session.json"
    _ = capsys.readouterr()
    export_exit_code = main(
        [
            "session",
            "export",
            str(session_id),
            str(output_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    raw_package = output_path.read_text(encoding="utf-8")
    payload = SessionExportPayload.model_validate_json(raw_package)
    _ = capsys.readouterr()

    import_exit_code = main(
        [
            "session",
            "import",
            str(output_path),
            "--json",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    import_payload = json.loads(capsys.readouterr().out)
    imported_session_id = UUID(import_payload["imported_session_id"])
    imported_notes = _runtime_notes_for_session(db_path, imported_session_id)

    assert export_exit_code == 0
    assert import_exit_code == 0
    assert payload.handoff.summary is not None
    summary = payload.handoff.summary
    assert summary.latest_objective == "Finish handoff summary for <workspace-root>"
    assert "Latest checkpoint" in summary.checkpoint_posture
    assert "status passed" in summary.checkpoint_posture
    assert "1 retained context compaction(s)" in summary.compaction_posture
    assert "1 accepted risk(s)" in summary.compaction_posture
    assert "1 task plan(s), 1 verification check(s):" in (summary.verification_state)
    assert "1 accepted risk(s)" in summary.verification_state
    assert "posture accepted_with_risk" in summary.verification_state
    assert "manual reviewer still inspects <workspace-root>" in summary.accepted_risks
    assert "accepted local evidence gap near <workspace-root>" in summary.accepted_risks
    assert "Review summary export" in summary.pending_actions
    assert summary.branch_lineage.startswith("Root session")
    assert summary.knowledge_posture.startswith("Overall ")
    assert f"glassbox session status {session_id} --cwd ." in (
        summary.safe_inspection_commands
    )
    assert f"glassbox task show {task_id} --cwd ." in summary.safe_inspection_commands
    assert str(tmp_path) not in raw_package
    assert imported_notes
    assert "latest objective: Finish handoff summary for <workspace-root>" in (
        imported_notes[0].message
    )


def _single_child_session_id(db_path: Path, parent_session_id: UUID) -> UUID:
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        child_sessions = [
            session
            for session in repository.list_sessions()
            if session.parent_session_id == parent_session_id
        ]
    finally:
        connection.close()

    assert len(child_sessions) == 1
    return child_sessions[0].session_id


def _seed_proposed_task(tmp_path: Path) -> tuple[Path, UUID]:
    db_path, session_id = _run_baseline_session(tmp_path, prompt="Plan task handoff")
    capture = capture_task_plan_proposal(
        f"""
```glassbox-task-plan
{{
  "title": "Inspect {tmp_path}",
  "goal": "Check OPENAI_API_KEY=secret-task-export before handoff",
  "steps": [
    {{"title": "Audit inputs", "description": "Review {tmp_path}"}},
    {{"title": "Write handoff"}}
  ]
}}
```
""",
        source_turn_id=new_turn_id(),
    )
    assert capture is not None
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=capture.created,
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=capture.proposed,
                ),
            ]
        )
    finally:
        connection.close()
    return db_path, session_id


def _tasks_for_session(db_path: Path, session_id: UUID):
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        return repository.list_tasks(session_id=session_id)
    finally:
        connection.close()


def _checkpoints_for_session(db_path: Path, session_id: UUID):
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        return repository.list_task_checkpoints(session_id)
    finally:
        connection.close()


def _runtime_notes_for_session(db_path: Path, session_id: UUID):
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        return repository.list_runtime_notes(session_id)
    finally:
        connection.close()


def _read_task_events(db_path: Path, session_id: UUID):
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        return [
            event
            for event in repository.read_session_events(session_id)
            if event.task_id is not None
        ]
    finally:
        connection.close()
