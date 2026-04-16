"""CLI package for Glassbox."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path

from glassbox.core import SessionConfig
from glassbox.runtime import default_database_path, open_runtime_context


def main(argv: Sequence[str] | None = None) -> int:
    """Run the minimal Glassbox CLI."""

    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "run":
        return _run_command(args)

    parser.print_help()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glassbox")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="start a baseline session")
    run_parser.add_argument("prompt", nargs="?", help="initial user prompt")
    run_parser.add_argument(
        "--cwd",
        default=".",
        help="workspace directory to associate with the session",
    )
    run_parser.add_argument(
        "--db-path",
        default=None,
        help="override the SQLite database path",
    )
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

    return parser


def _run_command(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    db_path = Path(args.db_path).resolve() if args.db_path is not None else None
    config = SessionConfig(
        model_name=args.model_name,
        cwd=cwd,
        approval_mode=args.approval_mode,
    )

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        session_state = asyncio.run(
            runtime_context.services.session_service.start_session(config)
        )
        if args.prompt:
            asyncio.run(
                runtime_context.services.session_service.submit_user_message(
                    session_state.session_id,
                    args.prompt,
                )
            )
            session_state = (
                runtime_context.repositories.sessions.get_session_state(
                    session_state.session_id,
                )
                or session_state
            )

        resolved_db_path = db_path or default_database_path(cwd)
        print(
            f"Started session {session_state.session_id} "
            f"in {cwd} using {resolved_db_path}"
        )
        if args.prompt:
            print(f"Queued initial prompt: {args.prompt}")

    return 0
