"""Characterization coverage for CLI status and replay formatters."""

from datetime import UTC
from datetime import datetime
from uuid import UUID

from glassbox.cli.replay_eval_formatters import _print_replay_report
from glassbox.cli.status_formatters import _format_budget_posture_line
from glassbox.cli.status_formatters import _format_next_action_line
from glassbox.cli.status_formatters import _print_session_status
from glassbox.core import AutonomyBudgetPostureRecord
from glassbox.core import AutonomyBudgetRemaining
from glassbox.core import AutonomyBudgetUsage
from glassbox.core import TurnRecoveryPosture
from glassbox.core.types import AutonomyEscalationReason
from glassbox.core.types import AutonomyMode
from glassbox.core.types import TurnRecoveryState
from glassbox.runtime.autonomy import default_budget_for_autonomy_mode
from glassbox.runtime.replay import ReplayFinalStateSnapshot
from glassbox.runtime.replay import ReplayNormalizedSession
from glassbox.runtime.replay import ReplayResult
from glassbox.runtime.replay import build_replay_triage
from glassbox.runtime.session_queries import SessionStatusView


def test_print_session_status_preserves_status_output_contract(
    capsys,
) -> None:
    status_view = SessionStatusView.model_validate(
        {
            "snapshot": {
                "session_id": "00000000-0000-0000-0000-000000000111",
                "status": "awaiting_user_input",
                "current_turn_id": "00000000-0000-0000-0000-000000000222",
                "model_name": "openai:gpt-5.4",
                "cwd": "/tmp/workspace",
                "approval_mode": "confirm",
                "parent_session_id": None,
                "forked_from_turn_id": None,
                "forked_from_sequence": None,
                "branch_label": None,
                "child_sessions": [],
                "branchable_turns": [],
                "can_fork": False,
                "latest_fork_point_turn_id": None,
                "latest_fork_point_sequence": None,
                "fork_blocked_reason": "Answer the pending question first.",
                "dashboard_url": "http://127.0.0.1:8765",
                "created_at": "2026-04-24T00:00:00Z",
                "updated_at": "2026-04-24T00:00:01Z",
                "last_sequence": 8,
                "pending_approval_id": None,
                "pending_question_id": "00000000-0000-0000-0000-000000000333",
                "pending_question_text": "Which branch should I inspect?",
                "session_failure_message": None,
                "session_failure_retryable": None,
                "long_run_status": {
                    "state": "paused",
                    "current_phase": None,
                    "last_event_type": "UserQuestionAsked",
                    "last_event_sequence": 8,
                    "last_event_at": "2026-04-24T00:00:01Z",
                    "current_attempt_id": None,
                    "current_attempt_tool_name": None,
                    "current_attempt_status": None,
                    "heartbeat_at": None,
                    "heartbeat_expires_at": None,
                    "heartbeat_age_seconds": None,
                    "elapsed_seconds": 1,
                    "stuck_reason": "session is awaiting_user_input",
                    "progress_summary": "session awaiting_user_input",
                },
                "transcript": [
                    {
                        "message_id": "00000000-0000-0000-0000-000000000444",
                        "role": "assistant",
                        "parts": [
                            {
                                "kind": "text",
                                "text": "Waiting for your answer.",
                            }
                        ],
                        "created_at": "2026-04-24T00:00:01Z",
                    }
                ],
                "active_tool_calls": [],
                "pending_approvals": [],
                "session_policy_summary": {
                    "total_decisions": 1,
                    "allow_count": 1,
                    "approve_count": 0,
                    "deny_count": 0,
                    "blocked_count": 0,
                    "read_only_count": 1,
                    "workspace_write_count": 0,
                    "command_count": 0,
                    "highest_risk_level": "read_only",
                },
                "current_turn_policy_summary": {
                    "total_decisions": 1,
                    "allow_count": 1,
                    "approve_count": 0,
                    "deny_count": 0,
                    "blocked_count": 0,
                    "read_only_count": 1,
                    "workspace_write_count": 0,
                    "command_count": 0,
                    "highest_risk_level": "read_only",
                },
                "turn_metrics": [
                    {
                        "turn_id": "00000000-0000-0000-0000-000000000222",
                        "started_at": "2026-04-24T00:00:00Z",
                        "completed_at": None,
                        "turn_duration_ms": None,
                        "model_call_count": 1,
                        "model_duration_ms_total": 600,
                        "model_input_tokens_total": 42,
                        "model_output_tokens_total": 13,
                        "tool_call_count": 1,
                        "tool_duration_ms_total": 25,
                        "succeeded_tool_call_count": 1,
                        "failed_tool_call_count": 0,
                    }
                ],
                "runtime_context": {
                    "repository_context": {
                        "workspace_name": "workspace",
                        "high_signal_paths": ["README.md", "src/"],
                        "top_level_directories": ["src/"],
                        "additional_directory_count": 0,
                        "top_level_files": ["README.md"],
                        "additional_file_count": 0,
                        "project_markers": ["src_layout"],
                    },
                    "runtime_notes": [
                        {
                            "category": "repo",
                            "message": "README is the operator entrypoint",
                            "inherited": False,
                            "source_session_id": "00000000-0000-0000-0000-000000000111",
                        }
                    ],
                    "additional_runtime_note_count": 0,
                    "working_set": {
                        "items": [
                            {
                                "subject_kind": "file",
                                "subject": "src/glassbox/runtime/session_queries.py",
                                "summary": "recently targeted workspace path",
                                "reasons": [
                                    "apply_patch targeted "
                                    "src/glassbox/runtime/session_queries.py"
                                ],
                                "signal_types": ["tool_request_path"],
                                "inherited": False,
                            }
                        ],
                        "additional_item_count": 0,
                    },
                    "artifact_context": {
                        "summaries": [],
                        "additional_summary_count": 0,
                    },
                    "context_compactions": {
                        "items": [
                            {
                                "compaction_id": (
                                    "00000000-0000-0000-0000-000000000777"
                                ),
                                "scope": "transcript",
                                "artifact_id": ("00000000-0000-0000-0000-000000000778"),
                                "source_start_sequence": 2,
                                "source_end_sequence": 7,
                                "summary": "Question and approval context compacted.",
                                "freshness": "fresh",
                                "limitations": [],
                            }
                        ],
                        "stale_items": [
                            {
                                "compaction_id": (
                                    "00000000-0000-0000-0000-000000000779"
                                ),
                                "scope": "transcript",
                                "artifact_id": ("00000000-0000-0000-0000-000000000780"),
                                "source_start_sequence": 1,
                                "source_end_sequence": 3,
                                "freshness": "stale",
                                "reason": "A newer checkpoint exists.",
                            }
                        ],
                        "additional_item_count": 0,
                        "stale_item_count": 1,
                    },
                },
                "projection_health": {
                    "state": "ok",
                    "canonical_last_sequence": 8,
                    "projected_last_sequence": 8,
                    "lag": 0,
                    "estimated_rebuild_event_count": 0,
                    "projected_progress_ratio": 1.0,
                    "degraded": False,
                    "detail": None,
                },
            },
            "effective_current_turn_id": "00000000-0000-0000-0000-000000000222",
            "current_turn_metrics": {
                "turn_id": "00000000-0000-0000-0000-000000000222",
                "started_at": "2026-04-24T00:00:00Z",
                "completed_at": None,
                "turn_duration_ms": None,
                "model_call_count": 1,
                "model_duration_ms_total": 600,
                "model_input_tokens_total": 42,
                "model_output_tokens_total": 13,
                "tool_call_count": 1,
                "tool_duration_ms_total": 25,
                "succeeded_tool_call_count": 1,
                "failed_tool_call_count": 0,
            },
            "latest_turn_metrics": {
                "turn_id": "00000000-0000-0000-0000-000000000222",
                "started_at": "2026-04-24T00:00:00Z",
                "completed_at": None,
                "turn_duration_ms": None,
                "model_call_count": 1,
                "model_duration_ms_total": 600,
                "model_input_tokens_total": 42,
                "model_output_tokens_total": 13,
                "tool_call_count": 1,
                "tool_duration_ms_total": 25,
                "succeeded_tool_call_count": 1,
                "failed_tool_call_count": 0,
            },
            "latest_turn_policy_summary": {
                "total_decisions": 1,
                "allow_count": 1,
                "approve_count": 0,
                "deny_count": 0,
                "blocked_count": 0,
                "read_only_count": 1,
                "workspace_write_count": 0,
                "command_count": 0,
                "highest_risk_level": "read_only",
            },
            "recent_tool_calls": [
                {
                    "tool_call_id": "00000000-0000-0000-0000-000000000555",
                    "turn_id": "00000000-0000-0000-0000-000000000222",
                    "tool_name": "read_file",
                    "status": "succeeded",
                    "started_at": "2026-04-24T00:00:00Z",
                    "completed_at": "2026-04-24T00:00:01Z",
                    "summary": "README.md",
                    "policy_outcome": "allow",
                    "policy_risk_level": "read_only",
                    "policy_source_kind": "default",
                    "policy_source_label": "read_only",
                    "policy_reason": "allowed: read-only tool within workspace scope",
                }
            ],
            "recent_tool_attempts": [
                {
                    "tool_attempt_id": "00000000-0000-0000-0000-000000000666",
                    "session_id": "00000000-0000-0000-0000-000000000111",
                    "turn_id": "00000000-0000-0000-0000-000000000222",
                    "tool_name": "run_command",
                    "status": "failed",
                    "tool_call_id": "00000000-0000-0000-0000-000000000555",
                    "task_id": None,
                    "message": "pytest failed",
                    "started_at": "2026-04-24T00:00:00Z",
                    "last_heartbeat_at": "2026-04-24T00:00:01Z",
                    "heartbeat_expires_at": None,
                    "completed_at": "2026-04-24T00:00:01Z",
                    "completed_units": None,
                    "total_units": None,
                    "output_artifact_id": None,
                    "safe_to_retry": True,
                    "retry_classification": "idempotent",
                    "retry_requires_approval": True,
                    "retry_reason": "verification command failed",
                    "retry_policy_reason": "approval required",
                    "last_sequence": 9,
                }
            ],
            "latest_message_summary": "assistant: Waiting for your answer.",
        }
    )

    _print_session_status(status_view)
    captured = capsys.readouterr()

    assert "Status: awaiting_user_input" in captured.out
    assert "Long-run status: paused" in captured.out
    assert (
        "Recent compactions: 1 fresh; 1 stale; latest "
        "00000000-0000-0000-0000-000000000777 events 2-7"
    ) in captured.out
    assert "Recovery guidance: inspect tool attempt" in captured.out
    assert "glassbox session tool-attempt inspect" in captured.out
    assert "Recovery guidance: inspect stale compactions" in captured.out
    assert "glassbox session compaction-refresh" in captured.out
    assert "Runtime context:" in captured.out
    assert "High-signal paths: README.md, src/" in captured.out
    assert "Pending question: 00000000-0000-0000-0000-000000000333" in captured.out
    assert "Which branch should I inspect?" in captured.out
    assert "answer question 00000000-0000-0000-0000-000000000333" in captured.out
    assert (
        "Session policy summary: 1 decision(s); allow 1, approve 0, deny 0, "
        "blocked 0;" in captured.out
    )
    assert (
        "Current turn policy summary: 1 decision(s); allow 1, approve 0, "
        "deny 0, blocked 0;" in captured.out
    )
    assert "Recent tool activity:" in captured.out
    assert (
        "read_file succeeded (turn 00000000-0000-0000-0000-000000000222) "
        "[allow read_only via default:read_only]" in captured.out
    )


def test_status_budget_lines_explain_budget_exhaustion_next_action() -> None:
    budget = default_budget_for_autonomy_mode(AutonomyMode.TEST_DRIVEN)
    posture = AutonomyBudgetPostureRecord(
        session_id=UUID("00000000-0000-0000-0000-000000000111"),
        task_id=None,
        mode=AutonomyMode.TEST_DRIVEN,
        budget=budget,
        usage=AutonomyBudgetUsage(
            steps=budget.max_steps,
            tool_calls=4,
            write_operations=2,
            command_operations=1,
            wall_clock_seconds=30,
            verification_attempts=1,
            branch_attempts=0,
            artifact_bytes=64,
        ),
        remaining=AutonomyBudgetRemaining(
            steps=0,
            tool_calls=1,
            write_operations=1,
            command_operations=0,
            wall_clock_seconds=10,
            verification_attempts=0,
            branch_attempts=0,
            artifact_bytes=512,
        ),
        last_decision="exhausted",
        last_reason=AutonomyEscalationReason.BUDGET_EXHAUSTED,
        last_limit_name="steps",
        last_detail="step budget exhausted",
        last_sequence=7,
        updated_at=datetime(2026, 4, 24, 0, 0, 1, tzinfo=UTC),
    )

    assert _format_budget_posture_line(posture) == (
        "Autonomy budget: test-driven; exhausted; budget_exhausted; "
        "limit steps; remaining steps 0, tools 1, writes 1, commands 0"
    )
    next_action = _format_next_action_line(
        UUID("00000000-0000-0000-0000-000000000111"),
        "running",
        None,
        None,
        None,
        None,
        budget_posture=posture,
    )
    assert next_action == (
        "Next action: review budget exhaustion and choose a smaller next step "
        "or override"
    )


def test_status_budget_line_includes_time_window_posture() -> None:
    budget = default_budget_for_autonomy_mode(AutonomyMode.RELEASE_CANDIDATE)
    posture = AutonomyBudgetPostureRecord(
        session_id=UUID("00000000-0000-0000-0000-000000000111"),
        task_id=None,
        mode=AutonomyMode.RELEASE_CANDIDATE,
        budget=budget,
        usage=AutonomyBudgetUsage(
            wall_clock_seconds=120,
            unattended_seconds=300,
            seconds_since_checkpoint=200,
            retry_delay_seconds=10,
        ),
        remaining=AutonomyBudgetRemaining(
            steps=1,
            tool_calls=2,
            write_operations=0,
            command_operations=1,
            wall_clock_seconds=60,
            unattended_seconds=600,
            seconds_since_checkpoint=100,
            retry_delay_seconds=110,
            verification_attempts=2,
            branch_attempts=0,
            artifact_bytes=512,
        ),
        last_decision="allowed",
        unattended_remaining_seconds=600,
        next_checkpoint_due_in_seconds=100,
        retry_delay_remaining_seconds=110,
        quiet_window_policy="checkpoint_before_quiet_window",
        checkpoint_approval_required=True,
        last_sequence=8,
        updated_at=datetime(2026, 4, 24, 0, 0, 1, tzinfo=UTC),
    )

    assert _format_budget_posture_line(posture) == (
        "Autonomy budget: release-candidate; allowed; remaining steps 1, "
        "tools 2, writes 0, commands 1; remaining time unattended 600s, "
        "checkpoint due in 100s, retry delay 110s; checkpoint approval "
        "required; quiet window checkpoint_before_quiet_window"
    )


def test_status_next_action_prefers_non_resumable_turn_recovery() -> None:
    turn_id = UUID("00000000-0000-0000-0000-000000000222")

    next_action = _format_next_action_line(
        UUID("00000000-0000-0000-0000-000000000111"),
        "running",
        turn_id,
        None,
        None,
        None,
        turn_recovery_posture=TurnRecoveryPosture(
            turn_id=turn_id,
            state=TurnRecoveryState.NON_RESUMABLE,
            safe_to_resume=False,
            reason="provider stream was interrupted",
            next_action="Retry with a new prompt or fork",
        ),
    )

    assert next_action == "Next action: Retry with a new prompt or fork"


def test_print_replay_report_preserves_triage_guidance_contract(capsys) -> None:
    baseline = ReplayNormalizedSession(
        transcript=[],
        tool_calls=[],
        approvals=[],
        questions=[],
        event_families=["SessionStarted", "TurnCompleted"],
        final_state=ReplayFinalStateSnapshot(status="completed"),
    )
    replay = ReplayNormalizedSession(
        transcript=[],
        tool_calls=[],
        approvals=[],
        questions=[],
        event_families=["SessionStarted"],
        final_state=ReplayFinalStateSnapshot(status="failed"),
    )
    result = ReplayResult(
        outcome="behavioral_drift",
        source_session_id=UUID("00000000-0000-0000-0000-000000000111"),
        message="normalized replay drift detected",
        mismatches=["event_families drift", "final_state drift"],
        baseline=baseline,
        replay=replay,
        triage=build_replay_triage(
            ReplayResult(
                outcome="behavioral_drift",
                mismatches=["event_families drift", "final_state drift"],
            )
        ),
    )

    _print_replay_report(result)
    captured = capsys.readouterr()

    assert "Outcome: behavioral drift" in captured.out
    assert "Summary: normalized replay drift detected" in captured.out
    assert "First change: event_families drift" in captured.out
    assert "Next inspect:" in captured.out
    assert "Mismatches:" in captured.out
    assert "Event families: baseline 2 event(s), replay 1 event(s)" in captured.out
    assert "Final state: baseline completed, replay failed" in captured.out
