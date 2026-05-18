"""Shared parser helpers for handoff profile flags."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid
from glassbox.core import HandoffIntent

_HANDOFF_INTENT_CHOICES = tuple(intent.value for intent in HandoffIntent)


def add_handoff_profile_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_labels: bool,
    format_choices: tuple[str, ...],
    format_help: str,
) -> None:
    """Add recipient-oriented handoff export profile arguments."""

    parser.add_argument(
        "--intent",
        choices=_HANDOFF_INTENT_CHOICES,
        default=HandoffIntent.REVIEW_ONLY.value,
        help="recipient intent for the export profile",
    )
    if include_labels:
        parser.add_argument(
            "--recipient",
            default=None,
            help="optional recipient label to include in the package",
        )
        parser.add_argument(
            "--exported-by",
            default=None,
            help="optional acting-operator label to include in the package",
        )
        parser.add_argument(
            "--expected-custodian",
            default=None,
            help="optional operator label expected to take custody after export",
        )
        parser.add_argument(
            "--note",
            default=None,
            help="optional handoff note to include in the package",
        )
    parser.add_argument(
        "--format",
        choices=format_choices,
        default=format_choices[0],
        help=format_help,
    )


def _add_handoff_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    handoff_parser = subparsers.add_parser(
        "handoff",
        help="inspect and record local handoff custody decisions",
        description=(
            "Inspect imported handoff records and record local custody decisions "
            "without granting approval, publication, or runtime ownership."
        ),
    )
    handoff_subparsers = handoff_parser.add_subparsers(
        dest="handoff_command",
        required=True,
    )

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
    show_parser.add_argument("session_id", type=_parse_uuid)
    show_parser.add_argument("package_id")
    show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(show_parser)

    accept_parser = handoff_subparsers.add_parser(
        "accept",
        help="accept local custody or imported follow-up",
    )
    _add_handoff_decision_target_arguments(accept_parser)
    accept_parser.add_argument("--accepted-by", default="operator")
    accept_parser.add_argument("--reason", default=None)
    accept_parser.add_argument(
        "--follow-up-intent",
        choices=_HANDOFF_INTENT_CHOICES,
        default=None,
    )
    accept_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(accept_parser)

    reject_parser = handoff_subparsers.add_parser(
        "reject",
        help="reject local custody with a retained reason",
    )
    _add_handoff_decision_target_arguments(reject_parser)
    reject_parser.add_argument("--rejected-by", default="operator")
    reject_parser.add_argument("--reason", required=True)
    reject_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(reject_parser)

    archive_parser = handoff_subparsers.add_parser(
        "archive",
        help="archive a handoff as historical workflow evidence",
    )
    _add_handoff_decision_target_arguments(archive_parser)
    archive_parser.add_argument("--archived-by", default="operator")
    archive_parser.add_argument("--reason", required=True)
    archive_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(archive_parser)


def _add_handoff_decision_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("session_id", type=_parse_uuid)
    parser.add_argument("package_id")


__all__ = ["_add_handoff_parsers", "add_handoff_profile_arguments"]
