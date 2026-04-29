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

    start_parser = branch_subparsers.add_parser(
        "start",
        help="record a bounded branch-search plan",
        description=(
            "Record a bounded branch-search objective and candidate strategy labels."
        ),
    )
    start_parser.add_argument("parent_session_id", type=_parse_uuid)
    start_parser.add_argument("--objective", required=True)
    start_parser.add_argument(
        "--strategy",
        dest="strategies",
        action="append",
        required=True,
        help="candidate strategy label; repeat for multiple candidates",
    )
    start_parser.add_argument("--max-candidates", type=int, default=2)
    start_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(start_parser)

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

    for command_name, help_text in (
        ("select", "mark a candidate as selected"),
        ("reject", "mark a candidate as rejected"),
        ("needs-review", "mark a candidate as needing review"),
    ):
        action_parser = branch_subparsers.add_parser(
            command_name,
            help=help_text,
            description=help_text,
        )
        action_parser.add_argument("search_id", type=_parse_uuid)
        action_parser.add_argument("candidate_id", type=_parse_uuid)
        action_parser.add_argument("--reason", required=True)
        action_parser.add_argument("--actor", default="operator")
        action_parser.add_argument("--json", action="store_true")
        _add_runtime_location_arguments(action_parser)


__all__ = ["_add_branch_search_parsers"]
