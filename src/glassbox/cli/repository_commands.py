"""CLI command dispatcher for local repository intelligence."""

import argparse

from glassbox.cli.repository_command_inspection import _repo_index_inspect_command
from glassbox.cli.repository_command_inspection import _repo_index_search_command
from glassbox.cli.repository_command_inspection import _repo_index_show_command
from glassbox.cli.repository_command_inspection import _repo_path_command
from glassbox.cli.repository_command_inspection import _repo_recipes_command
from glassbox.cli.repository_command_inspection import _repo_recommend_command
from glassbox.cli.repository_command_inspection import _repo_subsystem_command
from glassbox.cli.repository_command_inspection import _repo_topology_show_command
from glassbox.cli.repository_command_memory import _repo_memory_candidates_command
from glassbox.cli.repository_command_refresh import _repo_index_build_command
from glassbox.cli.repository_command_refresh import _repo_refresh_command
from glassbox.cli.repository_command_refresh import _repo_topology_build_command
from glassbox.cli.repository_command_status import _repo_index_status_command
from glassbox.cli.repository_command_status import _repo_stale_command
from glassbox.cli.repository_command_status import _repo_status_command
from glassbox.cli.repository_command_status import _repo_topology_status_command


def _repo_command(args: argparse.Namespace) -> int:
    repo_command = getattr(args, "repo_command", None)
    if repo_command == "status":
        return _repo_status_command(args)
    if repo_command == "stale":
        return _repo_stale_command(args)
    if repo_command == "refresh":
        return _repo_refresh_command(args)
    if repo_command == "path":
        return _repo_path_command(args)
    if repo_command == "recommend":
        return _repo_recommend_command(args)
    if repo_command == "recipes":
        return _repo_recipes_command(args)
    if repo_command == "subsystem":
        return _repo_subsystem_command(args)
    if repo_command == "memory-candidates":
        return _repo_memory_candidates_command(args)
    if repo_command == "index":
        return _repo_index_command(args)
    if repo_command == "topology":
        return _repo_topology_command(args)
    raise ValueError(f"unsupported repo subcommand: {repo_command}")


def _repo_index_command(args: argparse.Namespace) -> int:
    index_command = getattr(args, "repo_index_command", None)
    if index_command == "build":
        return _repo_index_build_command(args)
    if index_command == "status":
        return _repo_index_status_command(args)
    if index_command == "search":
        return _repo_index_search_command(args)
    if index_command == "show":
        return _repo_index_show_command(args)
    if index_command == "inspect":
        return _repo_index_inspect_command(args)
    raise ValueError(f"unsupported repo index subcommand: {index_command}")


def _repo_topology_command(args: argparse.Namespace) -> int:
    topology_command = getattr(args, "repo_topology_command", None)
    if topology_command == "build":
        return _repo_topology_build_command(args)
    if topology_command == "status":
        return _repo_topology_status_command(args)
    if topology_command == "show":
        return _repo_topology_show_command(args)
    raise ValueError(f"unsupported repo topology subcommand: {topology_command}")


__all__ = ["_repo_command"]
