"""Changeset argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_changeset_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "changeset",
        aliases=["changesets"],
        help="create and inspect reviewable local changesets",
        description="Create and inspect explicit local changeset evidence.",
    )
    changeset_subparsers = parser.add_subparsers(
        dest="changeset_command",
        required=True,
    )

    create_parser = changeset_subparsers.add_parser(
        "create",
        help="create a changeset from retained local evidence",
        description=(
            "Create one local changeset from a session, task, candidate, "
            "or workspace diff."
        ),
    )
    create_parser.add_argument(
        "--from",
        dest="source_kind",
        choices=("session", "task", "branch-candidate", "workspace-diff"),
        required=True,
        help="source evidence used for the changeset",
    )
    create_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    create_parser.add_argument("--task", dest="task_id", type=_parse_uuid)
    create_parser.add_argument(
        "--branch-search", dest="branch_search_id", type=_parse_uuid
    )
    create_parser.add_argument("--candidate", dest="candidate_id", type=_parse_uuid)
    create_parser.add_argument("--objective")
    create_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(create_parser)

    list_parser = changeset_subparsers.add_parser(
        "list",
        help="list changesets",
        description="List recent local changesets.",
    )
    list_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    list_parser.add_argument("--include-archived", action="store_true")
    list_parser.add_argument("--limit", type=int, default=None)
    list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(list_parser)

    show_parser = changeset_subparsers.add_parser(
        "show",
        help="show changeset details",
        description="Show changeset source references and basic review evidence.",
    )
    show_parser.add_argument("changeset_id", type=_parse_uuid)
    show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(show_parser)

    refresh_parser = changeset_subparsers.add_parser(
        "refresh",
        help="refresh structured change inventory for a changeset",
        description=(
            "Refresh structured workspace-diff inventory evidence without staging "
            "files or making review-readiness claims."
        ),
    )
    refresh_parser.add_argument("changeset_id", type=_parse_uuid)
    refresh_parser.add_argument("--actor", default="operator")
    refresh_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(refresh_parser)

    archive_parser = changeset_subparsers.add_parser(
        "archive",
        help="archive a changeset",
        description="Archive a changeset after explicit operator intent.",
    )
    archive_parser.add_argument("changeset_id", type=_parse_uuid)
    archive_parser.add_argument("--reason", required=True)
    archive_parser.add_argument("--actor", default="operator")
    archive_parser.add_argument(
        "--replacement", dest="replacement_changeset_id", type=_parse_uuid
    )
    archive_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(archive_parser)


__all__ = ["_add_changeset_parsers"]
