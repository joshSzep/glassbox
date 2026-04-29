"""Task-plan argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_task_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    task_parser = subparsers.add_parser(
        "task",
        help="inspect durable task plans",
        description="Inspect durable task plans and task-plan event history.",
    )
    task_subparsers = task_parser.add_subparsers(
        dest="task_command",
        required=True,
    )

    list_parser = task_subparsers.add_parser(
        "list",
        help="list task plans",
        description="List durable task plans by recent activity.",
    )
    list_parser.add_argument(
        "--session",
        dest="session_id",
        type=_parse_uuid,
        default=None,
        help="only list tasks for this session",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="maximum number of recent tasks to list",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="print task summaries as JSON",
    )
    _add_runtime_location_arguments(list_parser)

    show_parser = task_subparsers.add_parser(
        "show",
        help="show task details",
        description="Show task plan steps and verification summaries.",
    )
    show_parser.add_argument("task_id", type=_parse_uuid)
    show_parser.add_argument(
        "--json",
        action="store_true",
        help="print task detail as JSON",
    )
    _add_runtime_location_arguments(show_parser)

    events_parser = task_subparsers.add_parser(
        "events",
        help="list task events",
        description="List canonical events associated with one task plan.",
    )
    events_parser.add_argument("task_id", type=_parse_uuid)
    events_parser.add_argument(
        "--after",
        dest="after_sequence",
        type=int,
        default=0,
        help="only show events after this sequence",
    )
    events_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="maximum number of task events to list",
    )
    events_parser.add_argument(
        "--json",
        action="store_true",
        help="print task events as JSON",
    )
    _add_runtime_location_arguments(events_parser)

    continue_parser = task_subparsers.add_parser(
        "continue",
        help="enqueue a background task continuation job",
        description="Opt in to one bounded daemon task continuation step.",
    )
    continue_parser.add_argument("task_id", type=_parse_uuid)
    continue_parser.add_argument(
        "--requested-by",
        default="operator",
        help="actor requesting the continuation job",
    )
    continue_parser.add_argument(
        "--json",
        action="store_true",
        help="print the queued background job as JSON",
    )
    _add_runtime_location_arguments(continue_parser)


__all__ = ["_add_task_parsers"]
