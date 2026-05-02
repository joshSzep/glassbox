"""Argument parser construction for the Glassbox CLI."""

import argparse

from glassbox import __version__
from glassbox.cli.parser_branch_search import _add_branch_search_parsers
from glassbox.cli.parser_changesets import _add_changeset_parsers
from glassbox.cli.parser_memory import _add_memory_parsers
from glassbox.cli.parser_operations import _add_operations_parsers
from glassbox.cli.parser_replay_eval import _add_eval_parsers
from glassbox.cli.parser_replay_eval import _add_replay_parsers
from glassbox.cli.parser_repository import _add_repository_parsers
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
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    _add_command_parsers(subparsers)
    _add_autonomy_parsers(subparsers)
    _add_session_workflow_parsers(subparsers)
    _add_task_parsers(subparsers)
    _add_changeset_parsers(subparsers)
    _add_branch_search_parsers(subparsers)
    _add_memory_parsers(subparsers)
    _add_repository_parsers(subparsers)
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
    guide_parser = command_subparsers.add_parser(
        "guide",
        help="print workflow-oriented command discovery",
        description="Print workflow-oriented command discovery.",
    )
    guide_parser.add_argument(
        "--json",
        action="store_true",
        help="print the command guide as stable JSON",
    )
