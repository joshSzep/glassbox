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

    status_parser = repo_subparsers.add_parser(
        "status",
        help="show repository intelligence status",
        description="Show index and topology freshness with safe next actions.",
    )
    status_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(status_parser)

    stale_parser = repo_subparsers.add_parser(
        "stale",
        help="show stale or missing repository intelligence",
        description="Show stale, missing, degraded, or conflicting intelligence cues.",
    )
    stale_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(stale_parser)

    refresh_parser = repo_subparsers.add_parser(
        "refresh",
        help="refresh derived repository intelligence",
        description=(
            "Refresh the local repository intelligence index and workspace topology."
        ),
    )
    refresh_parser.add_argument(
        "--background",
        action="store_true",
        help="enqueue a safe daemon refresh job instead of rebuilding now",
    )
    refresh_parser.add_argument(
        "--session",
        dest="session_id",
        type=_parse_uuid,
        default=None,
        help="session used to anchor a background refresh job",
    )
    refresh_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(refresh_parser)

    path_parser = repo_subparsers.add_parser(
        "path",
        help="inspect repository intelligence for a path",
        description="Explain packages, subsystems, recipes, and hints for one path.",
    )
    path_parser.add_argument("path")
    path_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(path_parser)

    recommend_parser = repo_subparsers.add_parser(
        "recommend",
        help="recommend verification for changed paths",
        description="Recommend evals, profiles, recipes, and test targets for paths.",
    )
    recommend_parser.add_argument("paths", nargs="+")
    recommend_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(recommend_parser)

    recipes_parser = repo_subparsers.add_parser(
        "recipes",
        help="list or show repository command recipes",
        description="Inspect advisory command recipes from repository intelligence.",
    )
    recipes_subparsers = recipes_parser.add_subparsers(
        dest="repo_recipes_command",
        required=True,
    )
    recipes_list_parser = recipes_subparsers.add_parser("list", help="list recipes")
    recipes_list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(recipes_list_parser)
    recipes_show_parser = recipes_subparsers.add_parser("show", help="show a recipe")
    recipes_show_parser.add_argument("recipe_id")
    recipes_show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(recipes_show_parser)

    subsystem_parser = repo_subparsers.add_parser(
        "subsystem",
        help="list or show repository subsystems",
        description="Inspect advisory subsystem scopes from repository intelligence.",
    )
    subsystem_subparsers = subsystem_parser.add_subparsers(
        dest="repo_subsystem_command",
        required=True,
    )
    subsystem_list_parser = subsystem_subparsers.add_parser(
        "list",
        help="list subsystems",
    )
    subsystem_list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(subsystem_list_parser)
    subsystem_show_parser = subsystem_subparsers.add_parser(
        "show",
        help="show a subsystem",
    )
    subsystem_show_parser.add_argument("subsystem_id")
    subsystem_show_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(subsystem_show_parser)

    memory_parser = repo_subparsers.add_parser(
        "memory-candidates",
        help="list repository intelligence memory candidates",
        description="List review-gated memory candidates for one session.",
    )
    memory_parser.add_argument(
        "--session",
        dest="session_id",
        type=_parse_uuid,
        default=None,
        metavar="SESSION_ID",
        help=(
            "session used to anchor review-gated memory candidates; find one "
            "with `glassbox session list --json --cwd .`"
        ),
    )
    memory_parser.add_argument("--limit", type=int, default=25)
    memory_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(memory_parser)

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

    inspect_parser = index_subparsers.add_parser(
        "inspect",
        help="inspect the retained repository intelligence snapshot",
        description=(
            "Inspect repository intelligence freshness, roots, packages, "
            "command recipes, owner hints, subsystems, release surfaces, and "
            "limitations."
        ),
    )
    inspect_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(inspect_parser)

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
