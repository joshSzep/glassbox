"""CLI entrypoint and command dispatch for Glassbox."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Callable
from collections.abc import Sequence

from glassbox.cli.parser import build_parser
from glassbox.core.types import ApprovalDecision

CommandHandler = Callable[[argparse.Namespace], int]


def run_main(argv: Sequence[str] | None = None) -> int:
    """Parse argv, dispatch the selected command, and map top-level failures."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        return dispatch_command(args, parser)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"database operation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


def dispatch_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int:
    """Dispatch one parsed CLI command to its handler."""

    handler = _resolve_command_handler(args)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


def _resolve_command_handler(args: argparse.Namespace) -> CommandHandler | None:
    from glassbox.cli.interactive_commands import _answer_command
    from glassbox.cli.interactive_commands import _attach_command
    from glassbox.cli.interactive_commands import _chat_command
    from glassbox.cli.interactive_commands import _fork_command
    from glassbox.cli.interactive_commands import _message_command
    from glassbox.cli.interactive_commands import _resolve_approval_command
    from glassbox.cli.interactive_commands import _resume_command
    from glassbox.cli.interactive_commands import _run_command
    from glassbox.cli.replay_eval_commands import _eval_command
    from glassbox.cli.replay_eval_commands import _replay_command
    from glassbox.cli.replay_eval_commands import _replay_export_command
    from glassbox.cli.server_commands import _serve_command
    from glassbox.cli.session_state_commands import _rebuild_command
    from glassbox.cli.session_state_commands import _status_command

    command_handlers: dict[str, CommandHandler] = {
        "run": _run_command,
        "chat": _chat_command,
        "attach": _attach_command,
        "message": _message_command,
        "resume": _resume_command,
        "fork": _fork_command,
        "status": _status_command,
        "replay": _replay_command,
        "replay-export": _replay_export_command,
        "eval": _eval_command,
        "answer": _answer_command,
        "approve": lambda namespace: _resolve_approval_command(
            namespace,
            ApprovalDecision.APPROVED,
        ),
        "deny": lambda namespace: _resolve_approval_command(
            namespace,
            ApprovalDecision.DENIED,
        ),
        "rebuild": _rebuild_command,
        "serve": _serve_command,
    }
    command = getattr(args, "command", None)
    if not isinstance(command, str):
        return None
    return command_handlers.get(command)
