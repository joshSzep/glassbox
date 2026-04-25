"""Characterization coverage for CLI status and replay formatters."""

from uuid import UUID

from glassbox.cli.replay_eval_formatters import _print_replay_report
from glassbox.cli.status_formatters import _print_session_status
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
                },
                "projection_health": {
                    "state": "ok",
                    "canonical_last_sequence": 8,
                    "projected_last_sequence": 8,
                    "lag": 0,
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
            "latest_message_summary": "assistant: Waiting for your answer.",
        }
    )

    _print_session_status(status_view)
    captured = capsys.readouterr()

    assert "Status: awaiting_user_input" in captured.out
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
