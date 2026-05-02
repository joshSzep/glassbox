"""Repository intelligence argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_repository_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    repo_parser = subparsers.add_parser(
        "repo",
        help="inspect local repository intelligence",
        description="Build and query the local repository intelligence index.",
    )
    repo_subparsers = repo_parser.add_subparsers(
        dest="repo_command",
        required=True,
    )

    index_parser = repo_subparsers.add_parser(
        "index",
        help="build and query the repository index",
        description="Build and query the deterministic local repository index.",
    )
    index_subparsers = index_parser.add_subparsers(
        dest="repo_index_command",
        required=True,
    )

    build_parser = index_subparsers.add_parser(
        "build",
        help="build the repository index",
        description="Build and persist the deterministic local repository index.",
    )
    build_parser.add_argument(
        "--background",
        action="store_true",
        help="enqueue a read-only background refresh job instead of building now",
    )
    build_parser.add_argument(
        "--session",
        dest="session_id",
        type=_parse_uuid,
        default=None,
        help="session used to anchor a background refresh job",
    )
    build_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(build_parser)

    status_parser = index_subparsers.add_parser(
        "status",
        help="show repository index status",
        description="Show repository index freshness and entry counts.",
    )
    status_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(status_parser)

    search_parser = index_subparsers.add_parser(
        "search",
        help="search repository index entries",
        description="Search repository index entries by text.",
    )
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=None)
    search_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(search_parser)

    show_parser = index_subparsers.add_parser(
        "show",
        help="show one repository index entry",
        description="Show one repository index entry by stable ID.",
    )
    show_parser.add_argument("entry_id")
    show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(show_parser)

    topology_parser = repo_subparsers.add_parser(
        "topology",
        help="build and inspect workspace topology",
        description="Build and inspect deterministic local workspace topology.",
    )
    topology_subparsers = topology_parser.add_subparsers(
        dest="repo_topology_command",
        required=True,
    )

    topology_build_parser = topology_subparsers.add_parser(
        "build",
        help="build workspace topology",
        description="Build and persist deterministic local workspace topology.",
    )
    topology_build_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(topology_build_parser)

    topology_status_parser = topology_subparsers.add_parser(
        "status",
        help="show workspace topology status",
        description="Show workspace topology freshness and component counts.",
    )
    topology_status_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(topology_status_parser)

    topology_show_parser = topology_subparsers.add_parser(
        "show",
        help="show workspace topology",
        description="Show the retained workspace topology snapshot.",
    )
    topology_show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(topology_show_parser)


__all__ = ["_add_repository_parsers"]
