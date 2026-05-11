"""Refresh command handlers for repository intelligence CLI."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.repository_command_formatters import _print_background_job
from glassbox.cli.repository_command_formatters import _print_index_snapshot
from glassbox.cli.repository_command_formatters import _print_topology_snapshot
from glassbox.cli.repository_command_formatters import _print_topology_status
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.repository_intelligence_refresh import refresh_repository_index
from glassbox.runtime.repository_intelligence_refresh import (
    refresh_repository_intelligence,
)
from glassbox.runtime.workspace_topology import build_and_write_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path


def _repo_refresh_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    if args.background:
        if args.session_id is None:
            raise ValueError("--session is required with --background")
        with open_runtime_context(cwd, db_path=db_path) as runtime_context:
            job = runtime_context.repositories.sessions.enqueue_background_job(
                args.session_id,
                kind=BackgroundJobKind.DERIVED_INDEX,
                job_type="repository-intelligence-refresh",
                title="Refresh repository intelligence",
                payload={
                    "index_path": str(repository_index_path(cwd)),
                    "topology_path": str(workspace_topology_path(cwd)),
                },
            )
        if args.json:
            print_json_output(job.model_dump(mode="json"))
        else:
            _print_background_job(job)
        return 0

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        memory_entries = runtime_context.repositories.sessions.list_workspace_memory(
            state=WorkspaceMemoryState.ACTIVE,
        )
    refresh_result = refresh_repository_intelligence(
        cwd,
        workspace_memory_entries=memory_entries,
    )
    payload = {
        "index": refresh_result.index_snapshot.model_dump(mode="json"),
        "topology": refresh_result.topology_snapshot.model_dump(mode="json"),
    }
    if args.json:
        print_json_output(payload)
    else:
        print("Repository intelligence refreshed.")
        _print_index_snapshot(refresh_result.index_snapshot, refresh_result.index_path)
        print("")
        _print_topology_status(
            refresh_result.topology_snapshot,
            refresh_result.topology_path,
        )
    return 0


def _repo_index_build_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    if args.background:
        if args.session_id is None:
            raise ValueError("--session is required with --background")
        with open_runtime_context(cwd, db_path=db_path) as runtime_context:
            job = runtime_context.repositories.sessions.enqueue_background_job(
                args.session_id,
                kind=BackgroundJobKind.DERIVED_INDEX,
                job_type="repository-index-refresh",
                title="Refresh repository intelligence index",
                payload={"index_path": str(repository_index_path(cwd))},
            )
        if args.json:
            print_json_output(job.model_dump(mode="json"))
        else:
            _print_background_job(job)
        return 0

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        memory_entries = runtime_context.repositories.sessions.list_workspace_memory(
            state=WorkspaceMemoryState.ACTIVE,
        )
    refresh_result = refresh_repository_index(
        cwd,
        workspace_memory_entries=memory_entries,
    )
    if args.json:
        print_json_output(refresh_result.snapshot.model_dump(mode="json"))
    else:
        _print_index_snapshot(refresh_result.snapshot, refresh_result.index_path)
    return 0


def _repo_topology_build_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    snapshot = build_and_write_workspace_topology(cwd)
    if args.json:
        print_json_output(snapshot.model_dump(mode="json"))
    else:
        _print_topology_snapshot(snapshot, workspace_topology_path(cwd))
    return 0


__all__ = [
    "_repo_index_build_command",
    "_repo_refresh_command",
    "_repo_topology_build_command",
]
