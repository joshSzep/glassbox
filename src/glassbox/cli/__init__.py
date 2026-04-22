"""CLI package for Glassbox."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from glassbox.cli.renderer import CliEventRenderer
from glassbox.core import SessionConfig, TranscriptMessage
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
        record = runtime_context.repositories.sessions.get_session(args.session_id)
        state = runtime_context.repositories.sessions.get_session_state(args.session_id)
        if record is None or state is None:
            raise ValueError(f"unknown session_id: {args.session_id}")

        transcript_messages = (
            runtime_context.repositories.sessions.list_transcript_messages(
                args.session_id,
            )
        )

    print(f"Session {record.session_id}")
    print(f"Status: {state.status}")
    print(f"Last sequence: {state.last_sequence}")
    print(f"Current turn: {state.current_turn_id or 'none'}")
    print(f"Pending approval: {state.pending_approval_id or 'none'}")
    print(f"Workspace: {record.cwd}")
    print(f"Model: {record.model_name}")
    print(f"Approval mode: {record.approval_mode}")
    print(f"Transcript messages: {len(transcript_messages)}")

    latest_summary = _latest_message_summary(transcript_messages)
    if latest_summary is not None:
        print(f"Latest message: {latest_summary}")

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
