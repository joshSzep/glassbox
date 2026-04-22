"""CLI package for Glassbox."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from uuid import UUID

from glassbox.cli.renderer import CliEventRenderer
from glassbox.core import SessionConfig, TranscriptMessage
from glassbox.core.models import ApprovalRecord, ToolCallRecord, TurnMetricsRecord
from glassbox.core.types import ApprovalDecision
from glassbox.runtime import RuntimeContext, open_runtime_context


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Glassbox CLI."""

    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "run":
            return _run_command(args)
        if args.command == "resume":
            return _resume_command(args)
        if args.command == "status":
            return _status_command(args)
        if args.command == "approve":
            return _resolve_approval_command(args, ApprovalDecision.APPROVED)
        if args.command == "deny":
            return _resolve_approval_command(args, ApprovalDecision.DENIED)
        if args.command == "rebuild":
            return _rebuild_command(args)
        if args.command == "serve":
            return _serve_command(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glassbox")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="start a baseline session")
    run_parser.add_argument("prompt", nargs="?", help="initial user prompt")
    _add_runtime_location_arguments(run_parser)
    run_parser.add_argument(
        "--model-name",
        default="openai:gpt-5.4",
        help="model identifier recorded in the session metadata",
    )
    run_parser.add_argument(
        "--approval-mode",
        default="confirm",
        help="approval mode recorded in the session metadata",
    )

    resume_parser = subparsers.add_parser("resume", help="resume an existing session")
    resume_parser.add_argument("session_id", type=_parse_uuid)
    _add_runtime_location_arguments(resume_parser)

    status_parser = subparsers.add_parser("status", help="print session status")
    status_parser.add_argument("session_id", type=_parse_uuid)
    _add_runtime_location_arguments(status_parser)

    approve_parser = subparsers.add_parser(
        "approve",
        help="approve a pending action",
    )
    approve_parser.add_argument("session_id", type=_parse_uuid)
    approve_parser.add_argument("approval_id", type=_parse_uuid)
    _add_runtime_location_arguments(approve_parser)

    deny_parser = subparsers.add_parser("deny", help="deny a pending action")
    deny_parser.add_argument("session_id", type=_parse_uuid)
    deny_parser.add_argument("approval_id", type=_parse_uuid)
    _add_runtime_location_arguments(deny_parser)

    rebuild_parser = subparsers.add_parser(
        "rebuild",
        help="rebuild projection tables from canonical events",
    )
    rebuild_parser.add_argument("session_id", nargs="?", type=_parse_uuid)
    rebuild_parser.add_argument(
        "--all",
        action="store_true",
        help="rebuild projections for all sessions in the database",
    )
    _add_runtime_location_arguments(rebuild_parser)

    serve_parser = subparsers.add_parser("serve", help="start the web dashboard server")
    _add_runtime_location_arguments(serve_parser)
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="host address to bind the server to",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="port to bind the server to",
    )

    return parser


def _add_runtime_location_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cwd",
        default=".",
        help="workspace directory associated with the session database",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="override the SQLite database path",
    )


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID: {value}") from exc


def _resolve_runtime_location(args: argparse.Namespace) -> tuple[Path, Path | None]:
    cwd = Path(args.cwd).resolve()
    db_path = Path(args.db_path).resolve() if args.db_path is not None else None
    return cwd, db_path


def _run_command(args: argparse.Namespace) -> int:
    return asyncio.run(_run_command_async(args))


async def _run_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)
    config = SessionConfig(
        model_name=args.model_name,
        cwd=cwd,
        approval_mode=args.approval_mode,
    )

    async def action(runtime_context: RuntimeContext) -> None:
        session_state = await runtime_context.services.session_service.start_session(
            config
        )
        await asyncio.sleep(0)
        if args.prompt:
            await runtime_context.services.session_service.submit_user_message(
                session_state.session_id,
                args.prompt,
            )
            await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _resume_command(args: argparse.Namespace) -> int:
    return asyncio.run(_resume_command_async(args))


async def _resume_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(runtime_context: RuntimeContext) -> None:
        await runtime_context.services.session_service.resume_session(args.session_id)
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


def _status_command(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        record = repository.get_session(args.session_id)
        state = repository.get_session_state(args.session_id)
        if record is None or state is None:
            raise ValueError(f"unknown session_id: {args.session_id}")

        transcript_messages = repository.list_transcript_messages(args.session_id)
        pending_approvals = repository.list_approvals(args.session_id)
        tool_calls = repository.list_tool_calls(args.session_id)
        turn_metrics = repository.list_turn_metrics(args.session_id, limit=5)

    current_turn_id = _current_turn_id(state, pending_approvals)
    current_turn_metrics = _find_turn_metrics(turn_metrics, current_turn_id)
    latest_turn_metrics = current_turn_metrics or (
        turn_metrics[0] if turn_metrics else None
    )
    recent_tool_calls = _recent_tool_calls(tool_calls)

    print(f"Session {record.session_id}")
    print(f"Status: {state.status}")
    print(f"Last sequence: {state.last_sequence}")
    print(_format_current_turn_line(current_turn_id, state.status))
    print(f"Workspace: {record.cwd}")
    print(f"Model: {record.model_name}")
    print(f"Approval mode: {record.approval_mode}")
    print(f"Transcript messages: {len(transcript_messages)}")

    latest_summary = _latest_message_summary(transcript_messages)
    if latest_summary is not None:
        print(f"Latest message: {latest_summary}")

    if latest_turn_metrics is not None:
        label = (
            "Current turn metrics"
            if current_turn_metrics is not None
            else "Latest turn metrics"
        )
        print(f"{label}: {_format_turn_metrics(latest_turn_metrics)}")
    else:
        print("Latest turn metrics: none")

    if pending_approvals:
        print(f"Pending approvals: {len(pending_approvals)}")
        for approval in pending_approvals:
            print(f"  - {_format_approval_summary(approval)}")
    else:
        print("Pending approvals: none")

    if recent_tool_calls:
        print("Recent tool activity:")
        for tool_call in recent_tool_calls:
            print(f"  - {_format_tool_call_summary(tool_call)}")
    else:
        print("Recent tool activity: none")

    return 0


def _rebuild_command(args: argparse.Namespace) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    if args.all == (args.session_id is not None):
        raise ValueError("specify exactly one of session_id or --all")

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions

        if args.all:
            sessions = repository.list_sessions()
            if not sessions:
                print("No sessions found to rebuild")
                return 0

            for session in sessions:
                repository.rebuild_session_projections(session.session_id)
                print(f"Rebuilt projections for session {session.session_id}")
            print(f"Rebuilt projections for {len(sessions)} session(s)")
            return 0

        session_id = args.session_id
        assert session_id is not None
        if repository.get_session(session_id) is None:
            raise ValueError(f"unknown session_id: {session_id}")

        repository.rebuild_session_projections(session_id)
        print(f"Rebuilt projections for session {session_id}")
        return 0


def _latest_message_summary(
    transcript_messages: Sequence[TranscriptMessage],
) -> str | None:
    if not transcript_messages:
        return None

    latest_message = transcript_messages[-1]
    text = " ".join(
        part.text.strip().replace("\n", " ")
        for part in latest_message.parts
        if part.text.strip()
    ).strip()
    if not text:
        return latest_message.role
    return f"{latest_message.role}: {text}"


def _current_turn_id(
    state,
    approvals: Sequence[ApprovalRecord],
) -> UUID | None:
    if state.current_turn_id is not None:
        return state.current_turn_id
    if state.status == "awaiting_approval" and approvals:
        return approvals[-1].turn_id
    return None


def _find_turn_metrics(
    turn_metrics: Sequence[TurnMetricsRecord],
    turn_id: UUID | None,
) -> TurnMetricsRecord | None:
    if turn_id is None:
        return None
    for metrics in turn_metrics:
        if metrics.turn_id == turn_id:
            return metrics
    return None


def _recent_tool_calls(
    tool_calls: Sequence[ToolCallRecord],
    *,
    limit: int = 3,
) -> list[ToolCallRecord]:
    def sort_key(tool_call: ToolCallRecord) -> datetime:
        return tool_call.completed_at or tool_call.started_at or datetime.min

    return sorted(tool_calls, key=sort_key, reverse=True)[:limit]


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


def _format_tool_call_summary(tool_call: ToolCallRecord) -> str:
    summary_suffix = f": {tool_call.summary}" if tool_call.summary else ""
    return (
        f"{tool_call.tool_name} {tool_call.status} "
        f"(turn {tool_call.turn_id}){summary_suffix}"
    )


def _resolve_approval_command(
    args: argparse.Namespace,
    decision: ApprovalDecision,
) -> int:
    return asyncio.run(_resolve_approval_command_async(args, decision))


async def _resolve_approval_command_async(
    args: argparse.Namespace,
    decision: ApprovalDecision,
) -> int:
    cwd, db_path = _resolve_runtime_location(args)

    async def action(runtime_context: RuntimeContext) -> None:
        await runtime_context.services.session_service.resolve_approval(
            args.session_id,
            args.approval_id,
            decision,
        )
        await asyncio.sleep(0)

    return await _run_with_renderer(cwd, db_path, action)


async def _run_with_renderer(
    cwd: Path,
    db_path: Path | None,
    action: Callable[[RuntimeContext], Awaitable[None]],
) -> int:
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        renderer = CliEventRenderer(sys.stdout)
        async with runtime_context.infrastructure.event_bus.subscribe() as subscription:
            render_task = asyncio.create_task(
                renderer.render_subscription(subscription)
            )
            try:
                await action(runtime_context)
            finally:
                render_task.cancel()
                with suppress(asyncio.CancelledError):
                    await render_task

    return 0


def _serve_command(args: argparse.Namespace) -> int:
    from glassbox.web import run_server

    cwd, db_path = _resolve_runtime_location(args)
    run_server(cwd, host=args.host, port=args.port, db_path=db_path)
    return 0
