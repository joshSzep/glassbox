"""CLI entrypoint and command dispatch for Glassbox."""

import argparse
import sqlite3
import sys
from collections.abc import Callable
from collections.abc import Sequence

from glassbox.cli.parser import build_parser

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
    from glassbox.cli.artifact_commands import _artifacts_command
    from glassbox.cli.backup_commands import _backup_command
    from glassbox.cli.daemon_commands import _daemon_command
    from glassbox.cli.interactive_commands import _chat_command
    from glassbox.cli.interactive_commands import _run_command
    from glassbox.cli.replay_eval_commands import _eval_command
    from glassbox.cli.replay_eval_commands import _replay_command
    from glassbox.cli.server_commands import _dashboard_command
    from glassbox.cli.session_state_commands import _projection_command
    from glassbox.cli.session_state_commands import _session_command

    command_handlers: dict[str, CommandHandler] = {
        "run": _run_command,
        "chat": _chat_command,
        "session": _session_command,
        "replay": _replay_command,
        "eval": _eval_command,
        "artifacts": _artifacts_command,
        "backup": _backup_command,
        "projection": _projection_command,
        "dashboard": _dashboard_command,
        "daemon": _daemon_command,
    }
    command = getattr(args, "command", None)
    if not isinstance(command, str):
        return None
    return command_handlers.get(command)
