"""Workspace-memory argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid

_MEMORY_KINDS = (
    "fact",
    "convention",
    "command",
    "failure_pattern",
    "architecture_note",
    "user_preference",
    "task_outcome",
)
_MEMORY_STATES = ("active", "stale", "invalidated", "imported", "pruned")


def _add_memory_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    memory_parser = subparsers.add_parser(
        "memory",
        help="inspect workspace memory",
        description="Inspect and manage projected workspace memory entries.",
    )
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command",
        required=True,
    )

    list_parser = memory_subparsers.add_parser(
        "list",
        help="list workspace memory entries",
        description="List projected workspace memory by recent update.",
    )
    list_parser.add_argument("--state", choices=_MEMORY_STATES, default=None)
    list_parser.add_argument("--kind", choices=_MEMORY_KINDS, default=None)
    list_parser.add_argument(
        "--query",
        default=None,
        help="filter by text in content, summary, or tags",
    )
    list_parser.add_argument(
        "--include-pruned",
        action="store_true",
        help="include pruned entries when no explicit state is selected",
    )
    list_parser.add_argument("--limit", type=int, default=None)
    list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(list_parser)

    show_parser = memory_subparsers.add_parser(
        "show",
        help="show one workspace memory entry",
        description="Show projected state for one workspace memory entry.",
    )
    show_parser.add_argument("memory_id", type=_parse_uuid)
    show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(show_parser)

    confirm_parser = memory_subparsers.add_parser(
        "confirm",
        help="confirm one workspace memory entry",
        description="Append a confirmation event for one workspace memory entry.",
    )
    confirm_parser.add_argument("memory_id", type=_parse_uuid)
    confirm_parser.add_argument("--confirmed-by", default="operator")
    confirm_parser.add_argument("--reason", default=None)
    confirm_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(confirm_parser)

    invalidate_parser = memory_subparsers.add_parser(
        "invalidate",
        help="invalidate one workspace memory entry",
        description="Append an invalidation event for one workspace memory entry.",
    )
    invalidate_parser.add_argument("memory_id", type=_parse_uuid)
    invalidate_parser.add_argument("--invalidated-by", default="operator")
    invalidate_parser.add_argument("--reason", required=True)
    invalidate_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(invalidate_parser)

    prune_parser = memory_subparsers.add_parser(
        "prune",
        help="prune one workspace memory entry",
        description="Append a prune event for one workspace memory entry.",
    )
    prune_parser.add_argument("memory_id", type=_parse_uuid)
    prune_parser.add_argument("--pruned-by", default="operator")
    prune_parser.add_argument("--reason", required=True)
    prune_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the entry that would be pruned without appending an event",
    )
    prune_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(prune_parser)


__all__ = ["_add_memory_parsers"]
