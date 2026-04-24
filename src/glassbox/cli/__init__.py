"""CLI package for Glassbox."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from glassbox.cli.renderer import CliEventRenderer, InteractivePromptState
from glassbox.core.events import (
    EventEnvelope,
    SessionFailed,
    SessionStarted,
    UserQuestionAsked,
)
from glassbox.core.models import (
    ApprovalRecord,
    SessionState,
    ToolCallRecord,
    TurnMetricsRecord,
)
from glassbox.core.types import ApprovalDecision, SessionStatus
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.eval_baselines import format_eval_baseline_update_report
from glassbox.runtime.eval_coverage import (
    build_eval_coverage_summary_lines,
)
from glassbox.runtime.eval_runner import EvalSuiteResult
from glassbox.runtime.replay import ReplayResult
from glassbox.runtime.session_queries import SessionQueryService, SessionStatusView
from glassbox.web import GlassboxWebServer, WebServerConfig, build_web_server

_REPLAY_EXIT_CODES = {
    "exact_match": 0,
    "behavioral_drift": 10,
    "manifest_drift": 11,
    "unsupported_session": 12,
    "replay_failure": 13,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Compatibility wrapper for the package entrypoint."""

    from glassbox.cli.entry import run_main

    return run_main(argv)


def _run_command(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _run_command as impl

    return impl(args)


async def _run_command_async(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _run_command_async as impl

    return await impl(args)


def _chat_command(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _chat_command as impl

    return impl(args)


async def _chat_command_async(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _chat_command_async as impl

    return await impl(args)


def _attach_command(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _attach_command as impl

    return impl(args)


async def _attach_command_async(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _attach_command_async as impl

    return await impl(args)


def _resume_command(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _resume_command as impl

    return impl(args)


async def _resume_command_async(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _resume_command_async as impl

    return await impl(args)


def _message_command(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _message_command as impl

    return impl(args)


async def _message_command_async(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _message_command_async as impl

    return await impl(args)


def _fork_command(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _fork_command as impl

    return impl(args)


async def _fork_command_async(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _fork_command_async as impl

    return await impl(args)


def _answer_command(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _answer_command as impl

    return impl(args)


async def _answer_command_async(args: argparse.Namespace) -> int:
    from glassbox.cli.interactive_commands import _answer_command_async as impl

    return await impl(args)


def _status_command(args: argparse.Namespace) -> int:
    from glassbox.cli.session_state_commands import _status_command as impl

    return impl(args)


def _replay_command(args: argparse.Namespace) -> int:
    from glassbox.cli.replay_eval_commands import _replay_command as impl

    return impl(args)


async def _replay_command_async(args: argparse.Namespace) -> int:
    from glassbox.cli.replay_eval_commands import _replay_command_async as impl

    return await impl(args)


def _replay_export_command(args: argparse.Namespace) -> int:
    from glassbox.cli.replay_eval_commands import _replay_export_command as impl

    return impl(args)


def _eval_command(args: argparse.Namespace) -> int:
    from glassbox.cli.replay_eval_commands import _eval_command as impl

    return impl(args)


async def _eval_command_async(args: argparse.Namespace) -> int:
    from glassbox.cli.replay_eval_commands import _eval_command_async as impl

    return await impl(args)


async def _interactive_session_loop(
    runtime_context: RuntimeContext,
    session_id: UUID,
    prompt_state: InteractivePromptState,
) -> None:
    repository = runtime_context.repositories.sessions
    prompt_state.clear()

    while True:
        state = repository.get_session_state(session_id)
        if state is None:
            raise ValueError(f"unknown session_id: {session_id}")

        mode = _interactive_mode(state)
        prompt_context_lines = _interactive_prompt_context_lines(
            repository,
            session_id,
            state,
            mode,
        )
        _render_interactive_prompt_context(prompt_context_lines)

        if mode == "paused":
            prompt_state.clear()
            return

        prompt_label = _interactive_prompt_label(mode)
        prompt_state.activate(prompt_label, prompt_context_lines)
        try:
            user_input = await _read_interactive_input_async(prompt_label)
        except EOFError, KeyboardInterrupt:
            prompt_state.clear()
            print()
            print(f"Leaving interactive session {session_id}")
            return
        finally:
            prompt_state.clear()

        state = repository.get_session_state(session_id)
        if state is None:
            raise ValueError(f"unknown session_id: {session_id}")
        mode = _interactive_mode(state)

        action_kind, action_value = _parse_interactive_input(user_input)
        if action_kind == "continue":
            continue
        if action_kind == "exit":
            print(f"Leaving interactive session {session_id}")
            return
        if action_kind == "help":
            print(_interactive_help_text(mode))
            continue
        if action_kind == "status":
            query_service = SessionQueryService(
                repository,
                runtime_context.repositories.artifacts,
            )
            _print_session_status(
                query_service.get_session_status_view(session_id),
            )
            continue
        if action_kind == "approve":
            if state.status != SessionStatus.AWAITING_APPROVAL:
                print(_interactive_blocked_input_message(state, session_id))
                continue
            approval_id = state.pending_approval_id
            if approval_id is None:
                print(_interactive_blocked_input_message(state, session_id))
                continue
            await runtime_context.services.session_service.resolve_approval(
                session_id,
                approval_id,
                ApprovalDecision.APPROVED,
            )
            await asyncio.sleep(0)
            continue
        if action_kind == "deny":
            if state.status != SessionStatus.AWAITING_APPROVAL:
                print(_interactive_blocked_input_message(state, session_id))
                continue
            approval_id = state.pending_approval_id
            if approval_id is None:
                print(_interactive_blocked_input_message(state, session_id))
                continue
            await runtime_context.services.session_service.resolve_approval(
                session_id,
                approval_id,
                ApprovalDecision.DENIED,
            )
            await asyncio.sleep(0)
            continue
        if action_kind == "submit":
            if mode == "prompt":
                await runtime_context.services.session_service.submit_user_message(
                    session_id,
                    action_value,
                )
                await asyncio.sleep(0)
                continue
            if mode == "answer":
                question_id = state.pending_question_id
                if question_id is None:
                    print(_interactive_blocked_input_message(state, session_id))
                    continue
                await runtime_context.services.session_service.provide_user_answer(
                    session_id,
                    question_id,
                    action_value,
                )
                await asyncio.sleep(0)
                continue
            print(_interactive_blocked_input_message(state, session_id))
            continue


def _rebuild_command(args: argparse.Namespace) -> int:
    from glassbox.cli.session_state_commands import _rebuild_command as impl

    return impl(args)


def _current_turn_id(
    state,
    approvals: Sequence[ApprovalRecord],
) -> UUID | None:
    if state.current_turn_id is not None:
        return state.current_turn_id
    if state.status == "awaiting_approval" and approvals:
        return approvals[-1].turn_id
    return None


def _can_accept_interactive_chat_prompt(state: SessionState) -> bool:
    return state.status == SessionStatus.RUNNING and state.current_turn_id is None


def _can_accept_interactive_answer(state: SessionState) -> bool:
    return (
        state.status == SessionStatus.AWAITING_USER_INPUT
        and state.pending_question_id is not None
    )


def _interactive_mode(state: SessionState) -> str:
    if _can_accept_interactive_chat_prompt(state):
        return "prompt"
    if _can_accept_interactive_answer(state):
        return "answer"
    if state.status == SessionStatus.AWAITING_APPROVAL:
        return "approval"
    return "paused"


def _read_interactive_input(prompt: str) -> str:
    return input(prompt)


async def _read_interactive_input_async(prompt: str) -> str:
    return await asyncio.to_thread(_read_interactive_input, prompt)


def _parse_interactive_input(user_input: str) -> tuple[str, str]:
    trimmed = user_input.strip()
    if not trimmed:
        return "continue", ""
    if trimmed == "/exit":
        return "exit", ""
    if trimmed == "/help":
        return "help", ""
    if trimmed == "/status":
        return "status", ""
    if trimmed == "/approve":
        return "approve", ""
    if trimmed == "/deny":
        return "deny", ""
    if trimmed.startswith("/"):
        print("Unknown interactive command. Use /help for available commands.")
        return "continue", ""
    return "submit", user_input


def _ensure_session_can_attach(session_id: UUID, state: SessionState) -> None:
    if state.status in {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.CANCELLED,
    }:
        raise ValueError(f"cannot attach session {session_id} in status {state.status}")

    if state.status == SessionStatus.RUNNING and state.current_turn_id is not None:
        raise ValueError(
            f"cannot attach session {session_id} while turn "
            f"{state.current_turn_id} is still active"
        )


def _format_interactive_chat_pause_line(
    repository,
    session_id: UUID,
    state: SessionState,
) -> str:
    session_events = repository.read_session_events(session_id)
    pending_approvals = repository.list_approvals(session_id)
    latest_session_failure = _latest_session_failure(session_events)
    current_turn_id = _current_turn_id(state, pending_approvals)
    next_action = _format_next_action_line(
        session_id,
        state.status,
        current_turn_id,
        state.pending_approval_id,
        state.pending_question_id,
        latest_session_failure,
    )
    return f"Interactive chat paused. {next_action}"


def _interactive_prompt_label(mode: str) -> str:
    if mode == "prompt":
        return "prompt> "
    if mode == "answer":
        return "answer> "
    if mode == "approval":
        return "approval> "
    return "session> "


def _interactive_prompt_context_lines(
    repository,
    session_id: UUID,
    state: SessionState,
    mode: str,
) -> list[str]:
    if mode == "answer":
        session_events = repository.read_session_events(session_id)
        question_text = _pending_question_text_from_events(
            session_events,
            state.pending_question_id,
        )
        return [
            _format_pending_question_line(
                state.pending_question_id,
                question_text,
            ),
            "Interactive mode: answer the pending question, or use /status, "
            "/help, or /exit.",
        ]
    if mode == "approval":
        return [
            _interactive_blocked_input_message(state, session_id),
            "Interactive mode: use /approve, /deny, /status, /help, or /exit.",
        ]
    if mode == "prompt":
        return [
            "Interactive mode: type the next prompt, or use /status, /help, or /exit."
        ]
    return [_format_interactive_chat_pause_line(repository, session_id, state)]


def _render_interactive_prompt_context(context_lines: Sequence[str]) -> None:
    for context_line in context_lines:
        print(context_line)


def _interactive_blocked_input_message(state: SessionState, session_id: UUID) -> str:
    if state.status == SessionStatus.AWAITING_APPROVAL:
        approval_id = state.pending_approval_id
        if approval_id is None:
            return (
                "This session is awaiting approval resolution. Use /status or "
                "/help for more detail."
            )
        return (
            "This session is awaiting approval resolution for "
            f"{approval_id}. Freeform text is disabled until you use /approve "
            "or /deny."
        )

    next_action = _format_next_action_line(
        session_id,
        state.status,
        state.current_turn_id,
        state.pending_approval_id,
        state.pending_question_id,
        None,
    )
    return (
        "This session cannot accept freeform interactive input right now. "
        f"{next_action}"
    )


def _interactive_help_text(mode: str) -> str:
    lines = [
        "Interactive commands:",
        "  /status  show the full session status",
        "  /help    show interactive command help",
        "  /exit    leave the interactive session",
        "  /approve approve the pending action when awaiting approval",
        "  /deny    deny the pending action when awaiting approval",
    ]
    if mode == "prompt":
        lines.append("Freeform input sends the next user prompt.")
    elif mode == "answer":
        lines.append("Freeform input answers the pending ask_user question.")
    elif mode == "approval":
        lines.append("Freeform input is disabled while the session awaits approval.")
    return "\n".join(lines)


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


def _print_replay_report(result: ReplayResult) -> None:
    session_id = result.source_session_id
    if session_id is not None:
        print(f"Replay session {session_id}")
    print(f"Outcome: {_format_replay_outcome(result.outcome)}")

    if result.message:
        print(f"Summary: {result.message}")

    if result.triage is not None:
        if result.triage.classification != result.outcome:
            print(
                "Classification: "
                + _format_replay_outcome(result.triage.classification)
            )
        if result.triage.headline not in {"", result.message, None}:
            print(f"Triage: {result.triage.headline}")
        if result.triage.first_relevant_change not in {None, result.triage.headline}:
            print(f"First change: {result.triage.first_relevant_change}")
        if result.triage.drift_sources:
            print("Drift sources: " + ", ".join(result.triage.drift_sources))
        if result.triage.recommended_inspection_path:
            print(f"Next inspect: {result.triage.recommended_inspection_path}")

    if result.outcome == "exact_match":
        print(
            "Matched: transcript, tool calls, approval flow, question flow, "
            "event families, and final state"
        )
        return

    if result.mismatches:
        print("Mismatches:")
        for mismatch in result.mismatches:
            print(f"  - {mismatch}")

    for detail_line in _replay_detail_lines(result):
        print(detail_line)


def _print_eval_suite_report(result: EvalSuiteResult) -> None:
    print(f"Eval workspace {result.workspace_root}")
    if result.profile_id is not None:
        print(f"Profile: {result.profile_id} ({result.profile_verification_stage})")
    if result.profile_budget is not None:
        print(
            f"Budget: {result.profile_budget.status} "
            f"({result.profile_budget.enforcement})"
        )
    print(f"Selected cases: {result.selected_case_count}")
    print(f"Passed: {result.passed_case_count}")
    print(f"Failed: {result.failed_case_count}")
    print("Outcomes:")
    for outcome, count in result.outcome_counts.items():
        print(f"  - {_format_replay_outcome(outcome)}: {count}")
    print(f"Artifacts: {result.output_dir}")
    if result.coverage_audit is not None:
        for line in build_eval_coverage_summary_lines(result.coverage_audit):
            print(line)
    if result.profile_budget is not None:
        profile_budget = result.profile_budget
        print("Profile budget:")
        print(
            "  Selected cases: "
            f"{profile_budget.selected_case_count}"
            + _format_budget_limit(profile_budget.max_selected_case_count)
        )
        print(
            "  Selected-invariant cases: "
            f"{profile_budget.selected_invariant_case_count}"
            + _format_budget_limit(profile_budget.max_selected_invariant_case_count)
        )
        print(
            "  Recorded model calls: "
            f"{profile_budget.recorded_model_call_count}"
            + _format_budget_limit(profile_budget.max_recorded_model_call_count)
        )
        print(
            "  Case artifact bytes: "
            f"{profile_budget.case_artifact_bytes}"
            + _format_budget_limit(profile_budget.max_case_artifact_bytes)
        )
        print(
            "  Unsupported cases: "
            f"{profile_budget.unsupported_case_count}"
            + (" (allowed)" if profile_budget.allow_unsupported_cases else "")
        )
        print(
            "  Advisory cases: "
            f"{profile_budget.advisory_case_count}"
            + (" (allowed)" if profile_budget.allow_advisory_cases else "")
        )
        if profile_budget.promotion_policy:
            print("  Promotion policy: " + profile_budget.promotion_policy)
        if profile_budget.demotion_policy:
            print("  Demotion policy: " + profile_budget.demotion_policy)
        if profile_budget.violations:
            print("  Budget violations:")
            for violation in profile_budget.violations:
                print("    - " + violation.message)
    print("Cases:")
    for case_result in result.cases:
        status = "passed" if case_result.passed else "failed"
        print(
            f"  - {case_result.case_id}: "
            f"{_format_replay_outcome(case_result.replay_outcome)} ({status})"
        )
        if (
            case_result.triage_classification is not None
            and case_result.triage_classification != case_result.replay_outcome
        ):
            print(
                "    Classification: "
                + _format_replay_outcome(case_result.triage_classification)
            )
        if case_result.triage_headline:
            print(f"    Triage: {case_result.triage_headline}")
        if case_result.message:
            print(f"    Summary: {case_result.message}")
        if case_result.first_relevant_mismatch:
            print("    First relevant mismatch: " + case_result.first_relevant_mismatch)
        elif case_result.triage_first_relevant_change:
            print(
                "    First reported change: " + case_result.triage_first_relevant_change
            )
        if case_result.relevant_mismatches:
            print(
                "    Relevant mismatches: " + ", ".join(case_result.relevant_mismatches)
            )
        if case_result.ignored_mismatches:
            print(
                "    Ignored mismatches: " + ", ".join(case_result.ignored_mismatches)
            )
        if case_result.selected_invariant_interpretation:
            print(
                "    Selected invariants: "
                + case_result.selected_invariant_interpretation
            )
        if case_result.triage_drift_sources:
            print("    Drift sources: " + ", ".join(case_result.triage_drift_sources))
        if case_result.triage_recommended_inspection_path:
            print("    Next inspect: " + case_result.triage_recommended_inspection_path)
        print(f"    Artifact: {case_result.artifact_path}")


def _print_eval_coverage_audit(*, workspace_root: Path, result) -> None:
    print(f"Eval workspace {workspace_root.resolve()}")
    if result.profile_id is not None:
        print(f"Profile: {result.profile_id} ({result.verification_stage})")
    for line in build_eval_coverage_summary_lines(result):
        print(line)
    if result.uncovered_release_critical_capability_ids:
        print("Uncovered release-critical capability details:")
        for capability_id in result.uncovered_release_critical_capability_ids:
            print(f"  - {capability_id}")
    if result.unmapped_case_ids:
        print("Unmapped case details:")
        for case_id in result.unmapped_case_ids:
            print(f"  - {case_id}")


def _print_eval_baseline_update(report) -> None:
    for line in format_eval_baseline_update_report(report):
        print(line)


def _print_eval_profiles(*, workspace_root: Path, profiles) -> None:
    print(f"Eval workspace {workspace_root.resolve()}")
    if not profiles:
        print("No eval profiles matched the requested filter")
        return
    print("Profiles:")
    for profile in profiles:
        print(
            f"  - {profile.profile_id}: {profile.track}, "
            f"{profile.verification_stage}, "
            f"{'blocking' if profile.blocking else 'non-blocking'}"
        )
        if profile.tags:
            print("    Tags: " + ", ".join(profile.tags))
        if profile.case_ids:
            print("    Case IDs: " + ", ".join(profile.case_ids))
        if profile.description:
            print("    Description: " + profile.description)


def _format_budget_limit(limit: int | None) -> str:
    if limit is None:
        return " (no configured limit)"
    return f" / {limit}"


def _replay_detail_lines(result: ReplayResult) -> list[str]:
    if result.baseline is None or result.replay is None:
        return []

    detail_lines: list[str] = []
    mismatch_set = set(result.mismatches)
    if "transcript drift" in mismatch_set:
        detail_lines.append(
            "Transcript: baseline "
            f"{len(result.baseline.transcript)} message(s), replay "
            f"{len(result.replay.transcript)} message(s)"
        )
    if "tool_calls drift" in mismatch_set:
        detail_lines.append(
            "Tool calls: baseline "
            f"{len(result.baseline.tool_calls)} call(s), replay "
            f"{len(result.replay.tool_calls)} call(s)"
        )
    if "approvals drift" in mismatch_set:
        detail_lines.append(
            "Approvals: baseline "
            f"{len(result.baseline.approvals)} item(s), replay "
            f"{len(result.replay.approvals)} item(s)"
        )
    if "questions drift" in mismatch_set:
        detail_lines.append(
            "Questions: baseline "
            f"{len(result.baseline.questions)} item(s), replay "
            f"{len(result.replay.questions)} item(s)"
        )
    if "event_families drift" in mismatch_set:
        detail_lines.append(
            "Event families: baseline "
            f"{len(result.baseline.event_families)} event(s), replay "
            f"{len(result.replay.event_families)} event(s)"
        )
    if "final_state drift" in mismatch_set:
        detail_lines.append(
            "Final state: baseline "
            f"{result.baseline.final_state.status}, replay "
            f"{result.replay.final_state.status}"
        )
    return detail_lines


def _replay_result_payload(result: ReplayResult) -> dict[str, object]:
    payload = result.model_dump(mode="json")
    payload["exit_code"] = _replay_exit_code(result)
    return payload


def _replay_exit_code(result: ReplayResult) -> int:
    return _REPLAY_EXIT_CODES[result.outcome]


def _format_replay_outcome(outcome: str) -> str:
    return outcome.replace("_", " ")


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
    return (
        f"{approval.approval_id} for turn {approval.turn_id}: "
        f"{approval.subject} ({approval.reason})"
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
    return (
        f"{tool_call.tool_name} {tool_call.status} "
        f"(turn {tool_call.turn_id}){summary_suffix}"
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
) -> str:
    if status == "awaiting_approval" and pending_approval_id is not None:
        return (
            "Next action: resolve approval "
            f"{pending_approval_id} with 'glassbox approve {session_id} "
            f"{pending_approval_id}' or 'glassbox deny {session_id} "
            f"{pending_approval_id}', or use the dashboard approvals pane"
        )

    if status == "awaiting_user_input" and pending_question_id is not None:
        return (
            "Next action: answer question "
            f"{pending_question_id} with 'glassbox answer {session_id} "
            f"{pending_question_id} ANSWER', or use the dashboard Next Action "
            "pane"
        )

    if status == "running" and current_turn_id is None:
        return (
            "Next action: submit a new prompt with 'glassbox message "
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
            "'glassbox run PROMPT'"
        )

    if status == "failed":
        failure_guidance = "inspect the failure details above"
        if latest_session_failure is not None and latest_session_failure.retryable:
            failure_guidance = "inspect the retryable failure details above"
        return (
            "Next action: "
            f"{failure_guidance}, or start a new session with 'glassbox run PROMPT'"
        )

    return "Next action: inspect the session details above before taking another step"


def _resolve_approval_command(
    args: argparse.Namespace,
    decision: ApprovalDecision,
) -> int:
    from glassbox.cli.interactive_commands import _resolve_approval_command as impl

    return impl(args, decision)


async def _resolve_approval_command_async(
    args: argparse.Namespace,
    decision: ApprovalDecision,
) -> int:
    from glassbox.cli.interactive_commands import (
        _resolve_approval_command_async as impl,
    )

    return await impl(args, decision)


async def _run_with_renderer(
    cwd: Path,
    db_path: Path | None,
    action: Callable[[RuntimeContext, InteractivePromptState], Awaitable[None]],
) -> int:
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        prompt_state = InteractivePromptState()
        renderer = CliEventRenderer(sys.stdout, prompt_state=prompt_state)
        async with runtime_context.infrastructure.event_bus.subscribe() as subscription:
            render_task = asyncio.create_task(
                renderer.render_subscription(subscription)
            )
            try:
                await action(runtime_context, prompt_state)
            except Exception:
                await asyncio.sleep(0)
                raise
            finally:
                prompt_state.clear()
                render_task.cancel()
                with suppress(asyncio.CancelledError):
                    await render_task

    return 0


def _serve_command(args: argparse.Namespace) -> int:
    from glassbox.cli.server_commands import _serve_command as impl

    return impl(args)


def _dashboard_session_url(dashboard_url: str, session_id: UUID) -> str:
    return f"{dashboard_url}?session={session_id}"


def _chat_dashboard_config(
    args: argparse.Namespace,
) -> tuple[WebServerConfig | None, bool]:
    dashboard_host = getattr(args, "dashboard_host", None)
    dashboard_port = getattr(args, "dashboard_port", None)

    if args.no_dashboard:
        if dashboard_host is not None or dashboard_port is not None:
            raise ValueError(
                "cannot combine --no-dashboard with --dashboard-host "
                "or --dashboard-port"
            )
        return None, False

    explicit_dashboard_request = (
        dashboard_host is not None or dashboard_port is not None
    )
    return (
        WebServerConfig(
            host=dashboard_host or "127.0.0.1",
            port=dashboard_port or 8765,
        ),
        explicit_dashboard_request,
    )


async def _start_chat_dashboard(
    runtime_context: RuntimeContext,
    args: argparse.Namespace,
) -> tuple[GlassboxWebServer | None, str | None]:
    dashboard_config, explicit_dashboard_request = _chat_dashboard_config(args)
    if dashboard_config is None:
        return None, None

    dashboard_server = build_web_server(
        runtime_context,
        host=dashboard_config.host,
        port=dashboard_config.port,
    )
    try:
        await dashboard_server.start()
    except RuntimeError as exc:
        if explicit_dashboard_request:
            raise RuntimeError(
                f"dashboard startup failed at {dashboard_config.dashboard_url}: {exc}"
            ) from exc
        print(
            "Warning: dashboard unavailable at "
            f"{dashboard_config.dashboard_url}: {exc}",
            file=sys.stderr,
        )
        return None, None

    return dashboard_server, dashboard_server.config.dashboard_url
