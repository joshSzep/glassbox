"""CLI entrypoint and command dispatch for Glassbox."""

import argparse
import os
import sqlite3
import sys
from collections.abc import Callable
from collections.abc import Sequence
from typing import TextIO

from glassbox.cli.parser import CommandTreeColorTheme
from glassbox.cli.parser import build_parser
from glassbox.cli.parser import format_command_tree

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
    from glassbox.cli.observability_commands import _observability_command
    from glassbox.cli.replay_eval_commands import _eval_command
    from glassbox.cli.replay_eval_commands import _replay_command
    from glassbox.cli.server_commands import _dashboard_command
    from glassbox.cli.session_state_commands import _projection_command
    from glassbox.cli.session_state_commands import _session_command

    command_handlers: dict[str, CommandHandler] = {
        "command": _command_command,
        "session": _session_command,
        "replay": _replay_command,
        "eval": _eval_command,
        "artifacts": _artifacts_command,
        "backup": _backup_command,
        "observability": _observability_command,
        "performance": _performance_command,
        "projection": _projection_command,
        "dashboard": _dashboard_command,
        "daemon": _daemon_command,
    }
    command = getattr(args, "command", None)
    if not isinstance(command, str):
        return None
    return command_handlers.get(command)


def _command_command(args: argparse.Namespace) -> int:
    command_command = getattr(args, "command_command", None)
    if command_command == "tree":
        print(format_command_tree(build_parser(), color_theme=_argparse_color_theme()))
        return 0
    raise ValueError(f"unsupported command subcommand: {command_command}")


def _performance_command(args: argparse.Namespace) -> int:
    from glassbox.runtime.performance_budgets import format_performance_budgets

    performance_command = getattr(args, "performance_command", None)
    if performance_command == "budgets":
        print(format_performance_budgets())
        return 0
    raise ValueError(f"unsupported performance subcommand: {performance_command}")


def _argparse_color_theme() -> CommandTreeColorTheme | None:
    if not _can_colorize(sys.stdout):
        return None
    return CommandTreeColorTheme(
        prog="\x1b[1;35m",
        action="\x1b[1;32m",
        reset="\x1b[0m",
    )


def _can_colorize(file: TextIO) -> bool:
    python_colors = os.environ.get("PYTHON_COLORS")
    if python_colors == "0":
        return False
    if python_colors == "1":
        return True
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("TERM") == "dumb":
        return False
    return file.isatty()
