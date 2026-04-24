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
)
from glassbox.core.models import (
    ApprovalRecord,
    SessionState,
    ToolCallRecord,
    TurnMetricsRecord,
)
from glassbox.core.types import ApprovalDecision
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.context import RuntimeContext
from glassbox.runtime.eval_runner import EvalSuiteResult
from glassbox.runtime.replay import ReplayResult
from glassbox.runtime.session_queries import SessionStatusView
from glassbox.web import GlassboxWebServer, WebServerConfig, build_web_server


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
    from glassbox.cli.interactive_session import _interactive_session_loop as impl

    return await impl(runtime_context, session_id, prompt_state)


def _rebuild_command(args: argparse.Namespace) -> int:
    from glassbox.cli.session_state_commands import _rebuild_command as impl

    return impl(args)


def _current_turn_id(
    state,
    approvals: Sequence[ApprovalRecord],
) -> UUID | None:
    from glassbox.cli.interactive_session import _current_turn_id as impl

    return impl(state, approvals)


def _can_accept_interactive_chat_prompt(state: SessionState) -> bool:
    from glassbox.cli.interactive_session import (
        _can_accept_interactive_chat_prompt as impl,
    )

    return impl(state)


def _can_accept_interactive_answer(state: SessionState) -> bool:
    from glassbox.cli.interactive_session import (
        _can_accept_interactive_answer as impl,
    )

    return impl(state)


def _interactive_mode(state: SessionState) -> str:
    from glassbox.cli.interactive_session import _interactive_mode as impl

    return impl(state)


def _read_interactive_input(prompt: str) -> str:
    from glassbox.cli.interactive_session import _read_interactive_input as impl

    return impl(prompt)


async def _read_interactive_input_async(prompt: str) -> str:
    from glassbox.cli.interactive_session import _read_interactive_input_async as impl

    return await impl(prompt)


def _parse_interactive_input(user_input: str) -> tuple[str, str]:
    from glassbox.cli.interactive_session import _parse_interactive_input as impl

    return impl(user_input)


def _ensure_session_can_attach(session_id: UUID, state: SessionState) -> None:
    from glassbox.cli.interactive_session import _ensure_session_can_attach as impl

    return impl(session_id, state)


def _format_interactive_chat_pause_line(
    repository,
    session_id: UUID,
    state: SessionState,
) -> str:
    from glassbox.cli.interactive_session import (
        _format_interactive_chat_pause_line as impl,
    )

    return impl(repository, session_id, state)


def _interactive_prompt_label(mode: str) -> str:
    from glassbox.cli.interactive_session import _interactive_prompt_label as impl

    return impl(mode)


def _interactive_prompt_context_lines(
    repository,
    session_id: UUID,
    state: SessionState,
    mode: str,
) -> list[str]:
    from glassbox.cli.interactive_session import (
        _interactive_prompt_context_lines as impl,
    )

    return impl(repository, session_id, state, mode)


def _render_interactive_prompt_context(context_lines: Sequence[str]) -> None:
    from glassbox.cli.interactive_session import (
        _render_interactive_prompt_context as impl,
    )

    return impl(context_lines)


def _interactive_blocked_input_message(state: SessionState, session_id: UUID) -> str:
    from glassbox.cli.interactive_session import (
        _interactive_blocked_input_message as impl,
    )

    return impl(state, session_id)


def _interactive_help_text(mode: str) -> str:
    from glassbox.cli.interactive_session import _interactive_help_text as impl

    return impl(mode)


def _print_session_status(status_view: SessionStatusView) -> None:
    from glassbox.cli.status_formatters import _print_session_status as impl

    return impl(status_view)


def _print_runtime_context_summary(runtime_context) -> None:
    from glassbox.cli.status_formatters import _print_runtime_context_summary as impl

    return impl(runtime_context)


def _print_replay_report(result: ReplayResult) -> None:
    from glassbox.cli.replay_eval_formatters import _print_replay_report as impl

    return impl(result)


def _print_eval_suite_report(result: EvalSuiteResult) -> None:
    from glassbox.cli.replay_eval_formatters import _print_eval_suite_report as impl

    return impl(result)


def _print_eval_coverage_audit(*, workspace_root: Path, result) -> None:
    from glassbox.cli.replay_eval_formatters import _print_eval_coverage_audit as impl

    return impl(workspace_root=workspace_root, result=result)


def _print_eval_baseline_update(report) -> None:
    from glassbox.cli.replay_eval_formatters import _print_eval_baseline_update as impl

    return impl(report)


def _print_eval_profiles(*, workspace_root: Path, profiles) -> None:
    from glassbox.cli.replay_eval_formatters import _print_eval_profiles as impl

    return impl(workspace_root=workspace_root, profiles=profiles)


def _format_budget_limit(limit: int | None) -> str:
    from glassbox.cli.replay_eval_formatters import _format_budget_limit as impl

    return impl(limit)


def _replay_detail_lines(result: ReplayResult) -> list[str]:
    from glassbox.cli.replay_eval_formatters import _replay_detail_lines as impl

    return impl(result)


def _replay_result_payload(result: ReplayResult) -> dict[str, object]:
    from glassbox.cli.replay_eval_formatters import _replay_result_payload as impl

    return impl(result)


def _replay_exit_code(result: ReplayResult) -> int:
    from glassbox.cli.replay_eval_formatters import _replay_exit_code as impl

    return impl(result)


def _format_replay_outcome(outcome: str) -> str:
    from glassbox.cli.replay_eval_formatters import _format_replay_outcome as impl

    return impl(outcome)


def _format_current_turn_line(turn_id: UUID | None, status: str) -> str:
    from glassbox.cli.status_formatters import _format_current_turn_line as impl

    return impl(turn_id, status)


def _format_turn_metrics(metrics: TurnMetricsRecord) -> str:
    from glassbox.cli.status_formatters import _format_turn_metrics as impl

    return impl(metrics)


def _format_duration(duration_ms: int | None) -> str:
    from glassbox.cli.status_formatters import _format_duration as impl

    return impl(duration_ms)


def _format_approval_summary(approval: ApprovalRecord) -> str:
    from glassbox.cli.status_formatters import _format_approval_summary as impl

    return impl(approval)


def _dashboard_url_from_events(events: Sequence[EventEnvelope]) -> str | None:
    from glassbox.cli.status_formatters import _dashboard_url_from_events as impl

    return impl(events)


def _latest_session_failure(
    events: Sequence[EventEnvelope],
) -> SessionFailed | None:
    from glassbox.cli.status_formatters import _latest_session_failure as impl

    return impl(events)


def _format_session_failure(
    error_message: str,
    retryable: bool | None,
) -> str:
    from glassbox.cli.status_formatters import _format_session_failure as impl

    return impl(error_message, retryable)


def _session_failure_from_status_view(
    status_view: SessionStatusView,
) -> SessionFailed | None:
    from glassbox.cli.status_formatters import _session_failure_from_status_view as impl

    return impl(status_view)


def _format_tool_call_summary(tool_call: ToolCallRecord) -> str:
    from glassbox.cli.status_formatters import _format_tool_call_summary as impl

    return impl(tool_call)


def _pending_question_text_from_events(
    events: Sequence[EventEnvelope],
    pending_question_id,
) -> str | None:
    from glassbox.cli.status_formatters import (
        _pending_question_text_from_events as impl,
    )

    return impl(events, pending_question_id)


def _format_pending_question_line(question_id, question_text: str | None) -> str:
    from glassbox.cli.status_formatters import _format_pending_question_line as impl

    return impl(question_id, question_text)


def _format_next_action_line(
    session_id,
    status: str,
    current_turn_id,
    pending_approval_id,
    pending_question_id,
    latest_session_failure: SessionFailed | None,
) -> str:
    from glassbox.cli.status_formatters import _format_next_action_line as impl

    return impl(
        session_id,
        status,
        current_turn_id,
        pending_approval_id,
        pending_question_id,
        latest_session_failure,
    )


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
