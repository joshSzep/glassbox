"""Session status and runtime-context formatting helpers for the CLI."""

from collections.abc import Sequence
from uuid import UUID

from glassbox.cli.policy_formatters import format_policy_suffix
from glassbox.cli.policy_formatters import format_policy_summary
from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionStarted
from glassbox.core.events import UserQuestionAsked
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TurnMetricsRecord
from glassbox.runtime.context_formatting import format_runtime_context_budget_summary
from glassbox.runtime.session_queries import SessionStatusView


def _print_session_status(status_view: SessionStatusView) -> None:
    snapshot = status_view.snapshot
    current_turn_id = status_view.effective_current_turn_id

    print(f"Session {snapshot.session_id}")
    print(f"Status: {snapshot.status}")
    print(f"Last sequence: {snapshot.last_sequence}")
    print(_format_current_turn_line(current_turn_id, snapshot.status))
    print(f"Workspace: {snapshot.cwd}")
    print(f"Model: {snapshot.model_name}")
    print(f"Approval mode: {snapshot.approval_mode}")
    print(_format_budget_posture_line(snapshot.budget_posture))
    print(_format_projection_health_line(snapshot.projection_health))
    if snapshot.dashboard_url is not None:
        print(f"Dashboard URL: {snapshot.dashboard_url}")
    print(f"Transcript messages: {len(snapshot.transcript)}")
    _print_runtime_context_summary(snapshot.runtime_context)

    if snapshot.session_failure_message is not None:
        print(
            _format_session_failure(
                snapshot.session_failure_message,
                snapshot.session_failure_retryable,
            )
        )

    if status_view.latest_message_summary is not None:
        print(f"Latest message: {status_view.latest_message_summary}")
    if snapshot.pending_question_id is not None:
        print(
            _format_pending_question_line(
                snapshot.pending_question_id,
                snapshot.pending_question_text,
            )
        )
    print(
        _format_next_action_line(
            snapshot.session_id,
            snapshot.status,
            current_turn_id,
            snapshot.pending_approval_id,
            snapshot.pending_question_id,
            _session_failure_from_status_view(status_view),
            snapshot.projection_health,
        )
    )

    if status_view.latest_turn_metrics is not None:
        label = (
            "Current turn metrics"
            if status_view.current_turn_metrics is not None
            else "Latest turn metrics"
        )
        print(f"{label}: {_format_turn_metrics(status_view.latest_turn_metrics)}")
    else:
        print("Latest turn metrics: none")

    print(
        "Session policy summary: "
        + format_policy_summary(snapshot.session_policy_summary)
    )
    if status_view.latest_turn_policy_summary is not None:
        label = (
            "Current turn policy summary"
            if status_view.current_turn_metrics is not None
            else "Latest turn policy summary"
        )
        print(
            f"{label}: {format_policy_summary(status_view.latest_turn_policy_summary)}"
        )
    else:
        print("Latest turn policy summary: none")

    if snapshot.pending_approvals:
        print(f"Pending approvals: {len(snapshot.pending_approvals)}")
        for approval in snapshot.pending_approvals:
            print(f"  - {_format_approval_summary(approval)}")
    else:
        print("Pending approvals: none")

    if status_view.recent_tool_calls:
        print("Recent tool activity:")
        for tool_call in status_view.recent_tool_calls:
            print(f"  - {_format_tool_call_summary(tool_call)}")
    else:
        print("Recent tool activity: none")


def _print_runtime_context_summary(runtime_context) -> None:
    repository_context = runtime_context.repository_context

    print("Runtime context:")
    print(f"  Budget: {format_runtime_context_budget_summary(runtime_context)}")
    print(f"  Workspace summary: {repository_context.workspace_name}")
    if repository_context.high_signal_paths:
        print("  High-signal paths: " + ", ".join(repository_context.high_signal_paths))
    if repository_context.top_level_directories:
        directory_line = ", ".join(repository_context.top_level_directories)
        if repository_context.additional_directory_count:
            directory_line += (
                f" (+{repository_context.additional_directory_count} more)"
            )
        print(f"  Top-level directories: {directory_line}")
    if repository_context.top_level_files:
        file_line = ", ".join(repository_context.top_level_files)
        if repository_context.additional_file_count:
            file_line += f" (+{repository_context.additional_file_count} more)"
        print(f"  Top-level files: {file_line}")
    if repository_context.project_markers:
        print("  Project markers: " + ", ".join(repository_context.project_markers))

    if runtime_context.runtime_notes:
        print(f"  Runtime notes: {len(runtime_context.runtime_notes)} visible")
        for note in runtime_context.runtime_notes:
            inherited_suffix = ""
            if note.inherited and note.source_session_id is not None:
                inherited_suffix = (
                    f" (inherited from {str(note.source_session_id)[:8]})"
                )
            elif note.inherited:
                inherited_suffix = " (inherited)"
            print(f"    - [{note.category}] {note.message}{inherited_suffix}")
        if runtime_context.additional_runtime_note_count:
            print(
                "    - "
                f"+{runtime_context.additional_runtime_note_count} more active note(s)"
            )
    else:
        print("  Runtime notes: none")

    if runtime_context.working_set.items:
        print(f"  Working set: {len(runtime_context.working_set.items)} visible")
        for item in runtime_context.working_set.items:
            reason_text = "; ".join(item.reasons[:2])
            inherited_suffix = " (inherited)" if item.inherited else ""
            detail_suffix = f": {reason_text}" if reason_text else ""
            print(
                f"    - [{item.subject_kind}] {item.subject}"
                f"{inherited_suffix}"
                f" - {item.summary}{detail_suffix}"
            )
        if runtime_context.working_set.additional_item_count:
            print(
                "    - "
                f"+{runtime_context.working_set.additional_item_count} "
                "more working-set item(s)"
            )
    else:
        print("  Working set: none")

    if runtime_context.artifact_context.summaries:
        print(
            "  Artifact-backed context: "
            f"{len(runtime_context.artifact_context.summaries)} visible"
        )
        for summary in runtime_context.artifact_context.summaries:
            freshness_suffix = f" ({summary.freshness})"
            inherited_suffix = " (inherited)" if summary.inherited else ""
            failing_tests_suffix = ""
            if summary.failing_tests:
                failing_tests_suffix = ": failing tests: " + ", ".join(
                    summary.failing_tests[:2]
                )
            print(
                f"    - [{summary.summary_kind}] {summary.summary}"
                f"{freshness_suffix}{inherited_suffix}{failing_tests_suffix}"
            )
        if runtime_context.artifact_context.additional_summary_count:
            print(
                "    - "
                f"+{runtime_context.artifact_context.additional_summary_count} "
                "more artifact-backed summary item(s)"
            )
    else:
        print("  Artifact-backed context: none")


def _format_projection_health_line(projection_health) -> str:
    line = (
        "Projection health: "
        f"{projection_health.state}; "
        f"canonical sequence {projection_health.canonical_last_sequence}; "
        f"projected sequence {_format_projection_sequence(projection_health)}; "
        f"lag {projection_health.lag}"
    )
    if projection_health.detail is not None:
        line += f" ({projection_health.detail})"
    return line


def _format_budget_posture_line(budget_posture) -> str:
    if budget_posture is None:
        return "Autonomy budget: none"
    mode = budget_posture.mode.value if budget_posture.mode is not None else "unknown"
    detail = budget_posture.last_decision
    if budget_posture.last_reason is not None:
        detail += f"; {budget_posture.last_reason.value}"
    if budget_posture.last_limit_name is not None:
        detail += f"; limit {budget_posture.last_limit_name}"
    remaining = budget_posture.remaining
    if remaining is not None:
        detail += (
            f"; remaining steps {remaining.steps}, tools {remaining.tool_calls}, "
            f"writes {remaining.write_operations}, "
            f"commands {remaining.command_operations}"
        )
    return f"Autonomy budget: {mode}; {detail}"


def _format_projection_sequence(projection_health) -> str:
    if projection_health.projected_last_sequence is None:
        return "none"
    return str(projection_health.projected_last_sequence)


def _format_current_turn_line(turn_id: UUID | None, status: str) -> str:
    if turn_id is None:
        return "Current turn: none"
    return f"Current turn: {turn_id} ({status})"


def _format_turn_metrics(metrics: TurnMetricsRecord) -> str:
    return (
        f"turn {metrics.turn_id}; "
        f"model {metrics.model_call_count} call(s), "
        f"{metrics.model_input_tokens_total} input / "
        f"{metrics.model_output_tokens_total} output tokens, "
        f"{metrics.model_duration_ms_total} ms; "
        f"tools {metrics.tool_call_count} call(s), "
        f"{metrics.tool_duration_ms_total} ms, "
        f"{metrics.succeeded_tool_call_count} succeeded / "
        f"{metrics.failed_tool_call_count} failed; "
        f"turn duration {_format_duration(metrics.turn_duration_ms)}"
    )


def _format_duration(duration_ms: int | None) -> str:
    if duration_ms is None:
        return "n/a"
    return f"{duration_ms} ms"


def _format_approval_summary(approval: ApprovalRecord) -> str:
    policy_suffix = format_policy_suffix(
        outcome=approval.policy_outcome,
        risk_level=approval.policy_risk_level,
        source_kind=approval.policy_source_kind,
        source_label=approval.policy_source_label,
    )
    return (
        f"{approval.approval_id} for turn {approval.turn_id}: "
        f"{approval.subject}{policy_suffix} ({approval.reason})"
    )


def _dashboard_url_from_events(events: Sequence[EventEnvelope]) -> str | None:
    for event in events:
        if isinstance(event.payload, SessionStarted):
            return event.payload.dashboard_url
    return None


def _latest_session_failure(
    events: Sequence[EventEnvelope],
) -> SessionFailed | None:
    for event in reversed(events):
        if isinstance(event.payload, SessionFailed):
            return event.payload
    return None


def _format_session_failure(
    error_message: str,
    retryable: bool | None,
) -> str:
    retryable_suffix = " (retryable)" if retryable else ""
    return f"Session failure: {error_message}{retryable_suffix}"


def _session_failure_from_status_view(
    status_view: SessionStatusView,
) -> SessionFailed | None:
    snapshot = status_view.snapshot
    if snapshot.session_failure_message is None:
        return None
    return SessionFailed(
        error_message=snapshot.session_failure_message,
        retryable=bool(snapshot.session_failure_retryable),
    )


def _format_tool_call_summary(tool_call: ToolCallRecord) -> str:
    summary_suffix = f": {tool_call.summary}" if tool_call.summary else ""
    exit_suffix = (
        f" (exit code {tool_call.exit_code})" if tool_call.exit_code is not None else ""
    )
    policy_suffix = format_policy_suffix(
        outcome=tool_call.policy_outcome,
        risk_level=tool_call.policy_risk_level,
        source_kind=tool_call.policy_source_kind,
        source_label=tool_call.policy_source_label,
    )
    reason_suffix = ""
    if tool_call.policy_reason and tool_call.policy_reason != tool_call.summary:
        reason_suffix = f" [{tool_call.policy_reason}]"
    return (
        f"{tool_call.tool_name} {tool_call.status} "
        f"(turn {tool_call.turn_id}){policy_suffix}{summary_suffix}{exit_suffix}"
        f"{reason_suffix}"
    )


def _pending_question_text_from_events(
    events: Sequence[EventEnvelope],
    pending_question_id,
) -> str | None:
    if pending_question_id is None:
        return None

    pending_question_id_text = str(pending_question_id)
    for event in reversed(events):
        if not isinstance(event.payload, UserQuestionAsked):
            continue
        if str(event.payload.question_id) != pending_question_id_text:
            continue
        return event.payload.question
    return None


def _format_pending_question_line(question_id, question_text: str | None) -> str:
    if question_text:
        return f"Pending question: {question_id}: {question_text}"
    return f"Pending question: {question_id}"


def _format_next_action_line(
    session_id,
    status: str,
    current_turn_id,
    pending_approval_id,
    pending_question_id,
    latest_session_failure: SessionFailed | None,
    projection_health=None,
) -> str:
    if projection_health is not None and projection_health.degraded:
        return (
            "Next action: rebuild derived projections with "
            f"'glassbox projection rebuild {session_id}'"
        )

    if status == "awaiting_approval" and pending_approval_id is not None:
        return (
            "Next action: resolve approval "
            f"{pending_approval_id} with 'glassbox session approve {session_id} "
            f"{pending_approval_id}' or 'glassbox session deny {session_id} "
            f"{pending_approval_id}', or use the dashboard approvals pane"
        )

    if status == "awaiting_user_input" and pending_question_id is not None:
        return (
            "Next action: answer question "
            f"{pending_question_id} with 'glassbox session answer {session_id} "
            f"{pending_question_id} ANSWER', or use the dashboard Next Action "
            "pane"
        )

    if status == "running" and current_turn_id is None:
        return (
            "Next action: submit a new prompt with 'glassbox session message "
            f"{session_id} PROMPT', or use the dashboard Next Action pane"
        )

    if status == "running":
        return (
            "Next action: wait for the active turn to finish before sending "
            "another prompt"
        )

    if status == "completed":
        return (
            "Next action: this session is complete; start a new session with "
            "'glassbox session run PROMPT'"
        )

    if status == "failed":
        failure_guidance = "inspect the failure details above"
        if latest_session_failure is not None and latest_session_failure.retryable:
            failure_guidance = "inspect the retryable failure details above"
        return (
            "Next action: "
            f"{failure_guidance}, or start a new session with "
            "'glassbox session run PROMPT'"
        )

    return "Next action: inspect the session details above before taking another step"
