"""Operator queue argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.core import NextActionPriority
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueState

_QUEUE_VIEW_CHOICES = (
    "all",
    "action-needed",
    "verification",
    "review",
    "maintenance",
    "advisory",
    "historical",
)


def _add_queue_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    queue_parser = subparsers.add_parser(
        "queue",
        help="inspect the unified operator queue",
        description="Inspect the unified local operator queue.",
    )
    queue_subparsers = queue_parser.add_subparsers(
        dest="queue_command",
        required=True,
    )

    list_parser = queue_subparsers.add_parser(
        "list",
        help="list ranked operator attention items",
        description="List ranked operator attention items.",
    )
    list_parser.add_argument(
        "--view",
        choices=_QUEUE_VIEW_CHOICES,
        default="all",
        help="show a common queue slice",
    )
    list_parser.add_argument(
        "--family",
        choices=tuple(family.value for family in OperatorQueueFamily),
        default=None,
        help="only show items from this queue family",
    )
    list_parser.add_argument(
        "--state",
        choices=tuple(state.value for state in OperatorQueueState),
        default=None,
        help="only show items in this queue state",
    )
    list_parser.add_argument(
        "--priority",
        choices=tuple(priority.value for priority in NextActionPriority),
        default=None,
        help="only show items at this priority",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="maximum number of queue items to print",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="print the queue as stable JSON",
    )
    _add_runtime_location_arguments(list_parser)


__all__ = ["_add_queue_parsers"]
