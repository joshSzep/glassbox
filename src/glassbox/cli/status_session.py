"""Session status and runtime-context formatting helpers for the CLI."""

from collections.abc import Sequence
from uuid import UUID

from glassbox.cli.next_action_output import print_next_action_records
from glassbox.cli.policy_formatters import format_policy_suffix
from glassbox.cli.policy_formatters import format_policy_summary
from glassbox.cli.status_session_next_actions import session_next_action_records
from glassbox.core.events import EventEnvelope
from glassbox.core.events import SessionFailed
from glassbox.core.events import SessionStarted
from glassbox.core.events import UserQuestionAsked
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import ToolAttemptRecord
from glassbox.core.models import ToolCallRecord
from glassbox.core.models import TurnMetricsRecord
from glassbox.core.models import TurnRecoveryPosture
from glassbox.core.types import TurnRecoveryState
from glassbox.runtime.context_formatting import format_runtime_context_budget_summary
from glassbox.runtime.session_queries import SessionStatusView


def _print_session_status(status_view: SessionStatusView) -> None:
    snapshot = status_view.snapshot
    current_turn_id = status_view.effective_current_turn_id

    print(f"Session {snapshot.session_id}")
    print(f"Status: {snapshot.status}")
    print(f"Last sequence: {snapshot.last_sequence}")
    print(_format_current_turn_line(current_turn_id, snapshot.status))
    print(_format_long_run_status_line(snapshot.long_run_status))
    if snapshot.latest_provider_recovery is not None:
        print(_format_provider_recovery_line(snapshot.latest_provider_recovery))
    if snapshot.turn_recovery_posture is not None:
        print(_format_turn_recovery_line(snapshot.turn_recovery_posture))
    if snapshot.latest_checkpoint is not None:
        print(_format_latest_checkpoint_line(snapshot.latest_checkpoint))
    elif snapshot.checkpoint_absence is not None:
        print(_format_checkpoint_absence_line(snapshot.checkpoint_absence))
    print(_format_compaction_summary_line(snapshot.runtime_context))
    print(f"Workspace: {snapshot.cwd}")
    print(f"Model: {snapshot.model_name}")
    print(f"Approval mode: {snapshot.approval_mode}")
    print(f"Approval behavior: {snapshot.approval_behavior}")
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
            snapshot.budget_posture,
            snapshot.turn_recovery_posture,
        )
    )
    print_next_action_records(session_next_action_records(status_view))
    for line in _format_recovery_guidance_lines(status_view):
        print(line)
    for line in _format_session_safe_workflow_lines(status_view):
        print(line)

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

    if status_view.recent_tool_attempts:
        print("Recent tool attempts:")
        for attempt in status_view.recent_tool_attempts:
            print(f"  - {_format_tool_attempt_summary(attempt)}")
    else:
        print("Recent tool attempts: none")


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

    if runtime_context.workspace_memory:
        print(f"  Workspace memory: {len(runtime_context.workspace_memory)} visible")
        for memory in runtime_context.workspace_memory:
            source = memory.provenance.source_type
            if memory.provenance.source_sequence is not None:
                source += f":{memory.provenance.source_sequence}"
            print(f"    - [{memory.kind}] {memory.summary} (source: {source})")
        if runtime_context.additional_workspace_memory_count:
            print(
                "    - "
                f"+{runtime_context.additional_workspace_memory_count} "
                "more workspace memory item(s)"
            )
    else:
        print("  Workspace memory: none")

    if runtime_context.repository_index is not None:
        repository_index = runtime_context.repository_index
        print(
            "  Repository index: "
            f"{repository_index.status}; {len(repository_index.items)} visible "
            f"of {repository_index.entry_count} entries"
        )
        if repository_index.detail is not None:
            print(f"    - {repository_index.detail}")
        for item in repository_index.items:
            location = item.path or "workspace"
            print(f"    - [{item.kind}] {item.name} ({location})")
        if repository_index.additional_item_count:
            print(
                "    - "
                f"+{repository_index.additional_item_count} more repository "
                "index item(s)"
            )
    else:
        print("  Repository index: none")


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
        time_parts: list[str] = []
        if budget_posture.unattended_remaining_seconds is not None:
            time_parts.append(
                f"unattended {budget_posture.unattended_remaining_seconds}s"
            )
        if budget_posture.next_checkpoint_due_in_seconds is not None:
            time_parts.append(
                f"checkpoint due in {budget_posture.next_checkpoint_due_in_seconds}s"
            )
        if budget_posture.retry_delay_remaining_seconds is not None:
            time_parts.append(
                f"retry delay {budget_posture.retry_delay_remaining_seconds}s"
            )
        if time_parts:
            detail += f"; remaining time {', '.join(time_parts)}"
    if budget_posture.checkpoint_approval_required:
        detail += "; checkpoint approval required"
    if budget_posture.quiet_window_policy != "allow":
        detail += f"; quiet window {budget_posture.quiet_window_policy}"
    return f"Autonomy budget: {mode}; {detail}"


def _format_latest_checkpoint_line(checkpoint) -> str:
    phase = checkpoint.current_phase.value if checkpoint.current_phase else "unknown"
    blockers = ""
    if checkpoint.blockers:
        blockers = f"; blockers: {', '.join(checkpoint.blockers[:2])}"
    return (
        "Latest checkpoint: "
        f"{checkpoint.objective}; phase {phase}; "
        f"last step: {checkpoint.completed_step or 'none'}; "
        f"next: {checkpoint.next_action}; "
        f"source events {checkpoint.source_start_sequence}-"
        f"{checkpoint.source_end_sequence}{blockers}"
    )


def _format_checkpoint_absence_line(absence) -> str:
    reason = (
        absence.reason.value if hasattr(absence.reason, "value") else absence.reason
    )
    return (
        "Checkpoint absence: "
        f"{reason}; "
        f"{absence.message} Next action: {absence.next_action}"
    )


def _format_compaction_summary_line(runtime_context) -> str:
    compactions = getattr(runtime_context, "context_compactions", None)
    if compactions is None:
        return "Recent compactions: none"
    fresh_count = len(getattr(compactions, "items", []) or [])
    stale_count = getattr(compactions, "stale_item_count", 0)
    if fresh_count == 0 and stale_count == 0:
        return "Recent compactions: none"
    parts = [f"{fresh_count} fresh", f"{stale_count} stale"]
    latest_items = list(getattr(compactions, "items", []) or [])
    latest_stale = list(getattr(compactions, "stale_items", []) or [])
    if latest_items:
        item = latest_items[0]
        parts.append(
            f"latest {item.compaction_id} events "
            f"{item.source_start_sequence}-{item.source_end_sequence}"
        )
    elif latest_stale:
        item = latest_stale[0]
        parts.append(
            f"stale {item.compaction_id} events "
            f"{item.source_start_sequence}-{item.source_end_sequence}"
        )
    return "Recent compactions: " + "; ".join(parts)


def _format_recovery_guidance_lines(status_view: SessionStatusView) -> list[str]:
    snapshot = status_view.snapshot
    lines: list[str] = []
    for attempt in status_view.recent_tool_attempts:
        if attempt.status.value not in {"failed", "stale", "cancelled"}:
            continue
        lines.append(
            "Recovery guidance: inspect tool attempt "
            f"{attempt.tool_attempt_id} with "
            f"'glassbox session tool-attempt inspect {snapshot.session_id} "
            f"{attempt.tool_attempt_id}' and output with "
            f"'glassbox session tool-attempt output {snapshot.session_id} "
            f"{attempt.tool_attempt_id}' before retry or abandon"
        )
        break

    compactions = getattr(snapshot.runtime_context, "context_compactions", None)
    stale_items = list(getattr(compactions, "stale_items", []) or [])
    if stale_items:
        compaction = stale_items[0]
        lines.append(
            "Recovery guidance: inspect stale compactions with "
            f"'glassbox session compactions {snapshot.session_id}' before "
            "running confirmation-gated refresh or invalidation"
        )
        lines.append(
            "Recovery guidance: refresh command requires confirmation: "
            f"'glassbox session compaction-refresh {snapshot.session_id} "
            f"{compaction.compaction_id} --yes'"
        )

    if (
        snapshot.turn_recovery_posture is not None
        and snapshot.turn_recovery_posture.state
        in {
            TurnRecoveryState.INCOMPLETE,
            TurnRecoveryState.RECOVERABLE,
            TurnRecoveryState.ABANDONED,
            TurnRecoveryState.NON_RESUMABLE,
        }
    ):
        lines.append(
            "Recovery guidance: inspect session status before resume; "
            f"resume with 'glassbox session resume {snapshot.session_id}' only "
            "after reviewing checkpoint and recovery posture"
        )
    return lines


def _format_session_safe_workflow_lines(status_view: SessionStatusView) -> list[str]:
    snapshot = status_view.snapshot
    session_id = snapshot.session_id
    status = (
        snapshot.status.value if hasattr(snapshot.status, "value") else snapshot.status
    )
    lines = [
        "Safe workflow summary:",
        f"  - Checkpoints: glassbox session status {session_id} --cwd .",
        f"  - Compactions: glassbox session compactions {session_id} --cwd .",
        f"  - Tool attempts: glassbox session tool-attempts {session_id} --cwd .",
        "  - Verification: glassbox eval recommend PATH --cwd .",
        "  - Provider: glassbox provider diagnostics --cwd .",
        "  - Provider evidence: glassbox provider canary evidence --cwd .",
        "  - Projections: glassbox projection check --all --cwd .",
    ]
    if snapshot.dashboard_url is not None:
        lines.append(f"  - Dashboard: open {snapshot.dashboard_url}")
    else:
        lines.append("  - Dashboard: glassbox dashboard serve --cwd .")
    if status in {
        "running",
        "awaiting_user_input",
        "awaiting_approval",
        "failed",
        "cancelled",
    }:
        lines.append(
            f"  - Mutating recovery after inspection: "
            f"glassbox session resume {session_id} --cwd ."
        )
    return lines


def _format_projection_sequence(projection_health) -> str:
    if projection_health.projected_last_sequence is None:
        return "none"
    return str(projection_health.projected_last_sequence)


def _format_current_turn_line(turn_id: UUID | None, status: str) -> str:
    if turn_id is None:
        return "Current turn: none"
    return f"Current turn: {turn_id} ({status})"


def _format_long_run_status_line(long_run_status) -> str:
    parts = [
        f"Long-run status: {long_run_status.state}",
        f"elapsed {long_run_status.elapsed_seconds}s",
    ]
    if long_run_status.current_phase is not None:
        parts.append(f"phase {long_run_status.current_phase}")
    if long_run_status.current_attempt_id is not None:
        parts.append(
            "attempt "
            f"{str(long_run_status.current_attempt_id)[:8]} "
            f"{long_run_status.current_attempt_tool_name or 'tool'} "
            f"{long_run_status.current_attempt_status or 'unknown'}"
        )
    if long_run_status.heartbeat_age_seconds is not None:
        parts.append(f"heartbeat {long_run_status.heartbeat_age_seconds}s ago")
    if long_run_status.stuck_reason is not None:
        parts.append(long_run_status.stuck_reason)
    if long_run_status.last_event_type is not None:
        parts.append(
            f"last event {long_run_status.last_event_type}"
            f"#{long_run_status.last_event_sequence}"
        )
    parts.append(long_run_status.progress_summary)
    return "; ".join(parts)


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


def _format_tool_attempt_summary(attempt: ToolAttemptRecord) -> str:
    message_suffix = f": {attempt.message}" if attempt.message else ""
    retry_suffix = ""
    if attempt.retry_classification is not None:
        retry_suffix = f" (retry={attempt.retry_classification.value}"
        if attempt.retry_requires_approval is not None:
            retry_suffix += f", approval={str(attempt.retry_requires_approval).lower()}"
        retry_suffix += ")"
    elif attempt.safe_to_retry is not None:
        retry_suffix = f" (safe_to_retry={str(attempt.safe_to_retry).lower()})"
    purpose_suffix = ""
    if attempt.command_purpose is not None:
        purpose_suffix = f" [{attempt.command_purpose.value}"
        if attempt.command_supports_verification is True:
            purpose_suffix += ", verification"
        purpose_suffix += "]"
    return (
        f"{attempt.tool_name} attempt {str(attempt.tool_attempt_id)[:8]} "
        f"{attempt.status.value}{message_suffix}{retry_suffix}{purpose_suffix}"
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


def _format_turn_recovery_line(posture: TurnRecoveryPosture) -> str:
    safe_suffix = ""
    if posture.safe_to_resume is True:
        safe_suffix = "; exact resume safe"
    elif posture.safe_to_resume is False:
        safe_suffix = "; exact resume unsafe"
    reason_suffix = f"; {posture.reason}" if posture.reason else ""
    return (
        "Turn recovery: "
        f"{posture.state} for {posture.turn_id}{safe_suffix}{reason_suffix}"
    )


def _format_provider_recovery_line(recovery) -> str:
    retry_detail = ""
    if recovery.retryable:
        if recovery.backoff_seconds is not None:
            retry_detail = f"; retry in {recovery.backoff_seconds}s"
        else:
            retry_detail = "; retryable"
    return (
        "Provider recovery: "
        f"{recovery.provider}/{recovery.model_name} "
        f"{recovery.failure_kind.value} -> {recovery.action.value}"
        f"{retry_detail}; next: {recovery.operator_next_action}"
    )


def _format_next_action_line(
    session_id,
    status: str,
    current_turn_id,
    pending_approval_id,
    pending_question_id,
    latest_session_failure: SessionFailed | None,
    projection_health=None,
    budget_posture=None,
    turn_recovery_posture: TurnRecoveryPosture | None = None,
) -> str:
    if projection_health is not None and projection_health.degraded:
        return (
            "Next action: rebuild derived projections with "
            f"'glassbox projection rebuild {session_id}'"
        )

    budget_action = _format_budget_next_action(budget_posture)
    if budget_action is not None:
        return f"Next action: {budget_action}"

    if turn_recovery_posture is not None and turn_recovery_posture.state in {
        TurnRecoveryState.INCOMPLETE,
        TurnRecoveryState.RECOVERABLE,
        TurnRecoveryState.ABANDONED,
        TurnRecoveryState.NON_RESUMABLE,
    }:
        return f"Next action: {turn_recovery_posture.next_action}"

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


def _format_budget_next_action(budget_posture) -> str | None:
    if budget_posture is None or budget_posture.last_reason is None:
        return None
    if budget_posture.last_reason == "budget_exhausted":
        return "review budget exhaustion and choose a smaller next step or override"
    if budget_posture.last_reason == "policy_blocked":
        return "review policy block before continuing"
    if budget_posture.last_reason == "verification_failed":
        return "review failed verification before continuing"
    if budget_posture.last_reason == "approval_required":
        return "resolve the pending approval before continuing"
    return None
