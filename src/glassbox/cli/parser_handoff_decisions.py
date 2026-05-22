"""Projected record and custody decision parser helpers for handoff commands."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def add_handoff_decision_parsers(
    handoff_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    *,
    intent_choices: tuple[str, ...],
) -> None:
    list_parser = handoff_subparsers.add_parser(
        "list",
        help="list projected handoff records",
    )
    list_parser.add_argument("--session-id", type=_parse_uuid, default=None)
    list_parser.add_argument("--include-archived", action="store_true")
    list_parser.add_argument("--limit", type=int, default=None)
    list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(list_parser)

    show_parser = handoff_subparsers.add_parser(
        "show",
        help="show one projected handoff record",
    )
    add_handoff_decision_target_arguments(show_parser)
    show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(show_parser)

    guidance_parser = handoff_subparsers.add_parser(
        "guidance",
        help="preview fork-or-continue guidance for an imported handoff",
    )
    add_handoff_decision_target_arguments(guidance_parser)
    guidance_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(guidance_parser)

    accept_parser = handoff_subparsers.add_parser(
        "accept",
        help="accept local custody or imported follow-up",
    )
    add_handoff_decision_target_arguments(accept_parser)
    accept_parser.add_argument("--accepted-by", default="operator")
    accept_parser.add_argument("--reason", default=None)
    accept_parser.add_argument(
        "--follow-up-intent",
        choices=intent_choices,
        default=None,
    )
    accept_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(accept_parser)

    reject_parser = handoff_subparsers.add_parser(
        "reject",
        help="reject local custody with a retained reason",
    )
    add_handoff_decision_target_arguments(reject_parser)
    reject_parser.add_argument("--rejected-by", default="operator")
    reject_parser.add_argument("--reason", required=True)
    reject_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(reject_parser)

    archive_parser = handoff_subparsers.add_parser(
        "archive",
        help="archive a handoff as historical workflow evidence",
    )
    add_handoff_decision_target_arguments(archive_parser)
    archive_parser.add_argument("--archived-by", default="operator")
    archive_parser.add_argument("--reason", required=True)
    archive_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(archive_parser)


def add_handoff_decision_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("session_id", type=_parse_uuid)
    parser.add_argument("package_id")


__all__ = [
    "add_handoff_decision_parsers",
    "add_handoff_decision_target_arguments",
]
