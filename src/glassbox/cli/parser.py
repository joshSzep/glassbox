"""Argument parser construction for the Glassbox CLI."""

import argparse

from glassbox.cli.parser_memory import _add_memory_parsers
from glassbox.cli.parser_operations import _add_operations_parsers
from glassbox.cli.parser_replay_eval import _add_eval_parsers
from glassbox.cli.parser_replay_eval import _add_replay_parsers
from glassbox.cli.parser_sessions import _add_autonomy_parsers
from glassbox.cli.parser_sessions import _add_session_workflow_parsers
from glassbox.cli.parser_storage import _add_artifact_parsers
from glassbox.cli.parser_storage import _add_backup_parsers
from glassbox.cli.parser_tasks import _add_task_parsers
from glassbox.cli.parser_tree import CommandTreeColorTheme
from glassbox.cli.parser_tree import format_command_tree

__all__ = ["CommandTreeColorTheme", "build_parser", "format_command_tree"]


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level Glassbox CLI parser."""

    parser = argparse.ArgumentParser(
        prog="glassbox",
        description="Run the Glassbox local-first CLI agent and dashboard runtime.",
    )
    subparsers = parser.add_subparsers(dest="command")

    _add_command_parsers(subparsers)
    _add_autonomy_parsers(subparsers)
    _add_session_workflow_parsers(subparsers)
    _add_task_parsers(subparsers)
    _add_memory_parsers(subparsers)
    _add_replay_parsers(subparsers)
    _add_eval_parsers(subparsers)
    _add_artifact_parsers(subparsers)
    _add_backup_parsers(subparsers)
    _add_operations_parsers(subparsers)

    return parser


def _add_command_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    command_parser = subparsers.add_parser(
        "command",
        help="inspect the Glassbox command surface",
        description="Inspect the available Glassbox command surface.",
    )
    command_subparsers = command_parser.add_subparsers(
        dest="command_command",
        required=True,
    )

    command_subparsers.add_parser(
        "tree",
        help="print the command tree",
        description="Print the Glassbox command tree.",
    )
