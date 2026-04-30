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
        "--verify-repair",
        action="store_true",
        help="allow the queued continuation job to use verify-repair behavior",
    )
    continue_parser.add_argument(
        "--for-minutes",
        dest="continue_for_minutes",
        type=int,
        default=None,
        help="approve a bounded continuation window for this many minutes",
    )
    continue_parser.add_argument(
        "--checkpoint",
        dest="checkpoint_id",
        type=_parse_uuid,
        default=None,
        help="checkpoint this continuation window is tied to",
    )
    continue_parser.add_argument(
        "--json",
        action="store_true",
        help="print the queued background job as JSON",
    )
    _add_runtime_location_arguments(continue_parser)

    pause_window_parser = task_subparsers.add_parser(
        "pause-window",
        help="schedule a local task pause window",
        description="Schedule a local pause boundary for one durable task.",
    )
    pause_window_parser.add_argument("task_id", type=_parse_uuid)
    pause_window_group = pause_window_parser.add_mutually_exclusive_group(
        required=True,
    )
    pause_window_group.add_argument(
        "--before-time",
        dest="pause_before",
        default=None,
        help="pause before continuing after this ISO timestamp",
    )
    pause_window_group.add_argument(
        "--after-checkpoint",
        dest="checkpoint_id",
        type=_parse_uuid,
        default=None,
        help="pause after this checkpoint boundary",
    )
    pause_window_group.add_argument(
        "--before-risky-action",
        action="store_true",
        help="pause before the next mutating continuation action",
    )
    pause_window_parser.add_argument(
        "--reason",
        default="operator scheduled pause",
        help="operator-visible reason for the pause window",
    )
    pause_window_parser.add_argument(
        "--scheduled-by",
        default="operator",
        help="actor scheduling the pause window",
    )
    pause_window_parser.add_argument(
        "--json",
        action="store_true",
        help="print the scheduled pause-window event as JSON",
    )
    _add_runtime_location_arguments(pause_window_parser)

    pause_window_cancel_parser = task_subparsers.add_parser(
        "pause-window-cancel",
        help="cancel a local task pause window",
        description="Cancel a scheduled local pause window for one durable task.",
    )
    pause_window_cancel_parser.add_argument("task_id", type=_parse_uuid)
    pause_window_cancel_parser.add_argument("pause_window_id", type=_parse_uuid)
    pause_window_cancel_parser.add_argument(
        "--reason",
        default="operator override",
        help="operator-visible reason for cancelling the pause window",
    )
    pause_window_cancel_parser.add_argument(
        "--cancelled-by",
        default="operator",
        help="actor cancelling the pause window",
    )
    pause_window_cancel_parser.add_argument(
        "--json",
        action="store_true",
        help="print the cancellation event as JSON",
    )
    _add_runtime_location_arguments(pause_window_cancel_parser)


__all__ = ["_add_task_parsers"]
