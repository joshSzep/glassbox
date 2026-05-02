"""Worktree isolation argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_worktree_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "worktree",
        aliases=["worktrees"],
        help="manage temporary local worktrees",
        description=(
            "Create, inspect, and clean up temporary local git worktrees without "
            "merging, committing, pushing, or opening a PR."
        ),
    )
    worktree_subparsers = parser.add_subparsers(
        dest="worktree_command",
        required=True,
    )

    create_parser = worktree_subparsers.add_parser(
        "create",
        help="create a temporary local worktree",
        description=(
            "Create a Glassbox-managed local git worktree and record custody "
            "evidence. This does not merge, commit, push, or open a PR."
        ),
    )
    create_parser.add_argument(
        "--session", dest="session_id", type=_parse_uuid, required=True
    )
    create_parser.add_argument(
        "--source",
        dest="source_kind",
        choices=("branch-search-candidate", "changeset", "task", "session", "manual"),
        default="manual",
    )
    create_parser.add_argument("--source-id")
    create_parser.add_argument("--changeset", dest="changeset_id", type=_parse_uuid)
    create_parser.add_argument(
        "--branch-search",
        dest="branch_search_id",
        type=_parse_uuid,
    )
    create_parser.add_argument(
        "--candidate", dest="branch_candidate_id", type=_parse_uuid
    )
    create_parser.add_argument("--base", dest="base_revision", default="HEAD")
    create_parser.add_argument("--branch", dest="branch_name")
    create_parser.add_argument("--path", dest="path")
    create_parser.add_argument("--actor", default="operator")
    create_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(create_parser)

    list_parser = worktree_subparsers.add_parser(
        "list",
        help="list temporary local worktrees",
        description="List Glassbox worktree custody records with live status.",
    )
    list_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    list_parser.add_argument("--include-cleaned", action="store_true")
    list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(list_parser)

    status_parser = worktree_subparsers.add_parser(
        "status",
        help="inspect a temporary local worktree",
        description="Inspect a worktree and record status evidence.",
    )
    status_parser.add_argument("worktree_id", type=_parse_uuid)
    status_parser.add_argument("--actor", default="operator")
    status_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(status_parser)

    cleanup_parser = worktree_subparsers.add_parser(
        "cleanup",
        help="clean up a temporary local worktree",
        description=(
            "Remove a Glassbox-managed worktree only after explicit confirmation. "
            "Dirty worktrees are blocked unless --discard-user-changes is also "
            "provided."
        ),
    )
    cleanup_parser.add_argument("worktree_id", type=_parse_uuid)
    cleanup_parser.add_argument(
        "--confirm",
        action="store_true",
        help="confirm the cleanup after inspecting the risk summary",
    )
    cleanup_parser.add_argument(
        "--discard-user-changes",
        action="store_true",
        help="explicitly allow removal of a dirty worktree",
    )
    cleanup_parser.add_argument("--actor", default="operator")
    cleanup_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(cleanup_parser)


__all__ = ["_add_worktree_parsers"]
