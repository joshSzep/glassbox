"""Branch-search argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_branch_search_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "branch-search",
        help="inspect bounded branch-search attempts",
        description="Inspect branch-search workflows and candidate comparisons.",
    )
    branch_subparsers = parser.add_subparsers(
        dest="branch_search_command",
        required=True,
    )

    list_parser = branch_subparsers.add_parser(
        "list",
        help="list branch searches",
        description="List recent branch-search workflows.",
    )
    list_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    list_parser.add_argument("--limit", type=int, default=None)
    list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(list_parser)

    show_parser = branch_subparsers.add_parser(
        "show",
        help="show branch-search candidates",
        description="Show branch-search candidate comparison evidence.",
    )
    show_parser.add_argument("search_id", type=_parse_uuid)
    show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(show_parser)


__all__ = ["_add_branch_search_parsers"]
