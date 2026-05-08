"""CLI command handlers for local repository intelligence."""

import argparse
from pathlib import Path

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.types import BackgroundJobKind
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import get_repository_index_entry
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.repository_index import search_repository_index
from glassbox.runtime.repository_index_status import RepositoryIndexSourceDiff
from glassbox.runtime.repository_index_status import RepositoryIndexStatusSummary
from glassbox.runtime.repository_index_status import (
    build_repository_index_status_summary,
)
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot
from glassbox.runtime.workspace_topology import build_and_write_workspace_topology
from glassbox.runtime.workspace_topology import load_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path


def _repo_command(args: argparse.Namespace) -> int:
    repo_command = getattr(args, "repo_command", None)
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

    snapshot = build_and_write_repository_index(cwd)
    if args.json:
        print_json_output(snapshot.model_dump(mode="json"))
    else:
        _print_index_snapshot(snapshot, repository_index_path(cwd))
    return 0


def _repo_index_status_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    summary = build_repository_index_status_summary(cwd)
    if args.json:
        print_json_output(summary.model_dump(mode="json"))
    else:
        _print_status_summary(summary)
    return 0


def _repo_index_search_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, _ = resolve_runtime_location(args)
    entries = search_repository_index(cwd, args.query, limit=args.limit)
    if args.json:
        print_json_output([entry.model_dump(mode="json") for entry in entries])
    else:
        _print_index_entries(entries)
    return 0


def _repo_index_show_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    entry = get_repository_index_entry(cwd, args.entry_id)
    if args.json:
        print_json_output(entry.model_dump(mode="json"))
    else:
        _print_index_entry(entry)
    return 0


def _repo_index_inspect_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    snapshot = load_repository_index(cwd)
    if args.json:
        print_json_output(snapshot.model_dump(mode="json"))
    else:
        _print_index_snapshot(snapshot, repository_index_path(cwd))
    return 0


def _repo_topology_build_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    snapshot = build_and_write_workspace_topology(cwd)
    if args.json:
        print_json_output(snapshot.model_dump(mode="json"))
    else:
        _print_topology_snapshot(snapshot, workspace_topology_path(cwd))
    return 0


def _repo_topology_status_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    path = workspace_topology_path(cwd)
    try:
        snapshot = load_workspace_topology(cwd)
    except WorkspaceTopologyNotFoundError:
        if args.json:
            print_json_output(
                {
                    "freshness": "missing",
                    "path": str(path),
                    "component_count": 0,
                    "dependency_count": 0,
                    "recommendation_posture": "unavailable",
                    "detail": "workspace topology has not been built",
                    "next_actions": [
                        f"glassbox repo topology build --cwd {cwd.resolve()}"
                    ],
                }
            )
        else:
            print("Workspace topology: missing")
            print(f"Path: {path}")
            print(f"Next action: glassbox repo topology build --cwd {cwd.resolve()}")
        return 0
    payload = _topology_status_payload(snapshot, path)
    if args.json:
        print_json_output(payload)
    else:
        _print_topology_status(snapshot, path)
    return 0


def _repo_topology_show_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    snapshot = load_workspace_topology(cwd)
    if args.json:
        print_json_output(snapshot.model_dump(mode="json"))
    else:
        _print_topology_snapshot(snapshot, workspace_topology_path(cwd))
    return 0


def _print_status_summary(summary: RepositoryIndexStatusSummary) -> None:
    print(f"Repository index: {summary.status}")
    print(f"Path: {summary.path}")
    print(f"Entries: {summary.entry_count}")
    if summary.built_at is not None:
        print(f"Built: {summary.built_at}")
    print(f"Detail: {summary.detail}")
    if summary.stale_reason is not None:
        print(f"Reason: {summary.stale_reason}")
    if summary.failure_reason is not None:
        print(f"Failure: {summary.failure_reason}")
    if summary.current_source_digest is not None:
        print(f"Current source digest: {summary.current_source_digest}")
    if summary.source_digest is not None:
        print(f"Indexed source digest: {summary.source_digest}")
    if summary.source_file_count or summary.current_source_file_count:
        print(
            "Source files: "
            f"{summary.source_file_count} indexed, "
            f"{summary.current_source_file_count} current"
        )
    _print_repository_intelligence_counts(
        source_manifest_count=summary.source_manifest_count,
        source_root_count=summary.source_root_count,
        test_root_count=summary.test_root_count,
        doc_root_count=summary.doc_root_count,
        generated_path_count=summary.generated_path_count,
        policy_sensitive_path_count=summary.policy_sensitive_path_count,
        package_boundary_count=summary.package_boundary_count,
        command_recipe_count=summary.command_recipe_count,
        ownership_hint_count=summary.ownership_hint_count,
        subsystem_count=summary.subsystem_count,
        release_surface_count=summary.release_surface_count,
    )
    for limitation in summary.limitations:
        print(f"Limitation: {limitation}")
    if summary.source_diff is not None:
        _print_source_diff(summary.source_diff)
    if summary.next_actions:
        print("Next actions:")
        for action in summary.next_actions:
            print(f"- {action}")


def _print_source_diff(source_diff: RepositoryIndexSourceDiff) -> None:
    if not source_diff.available:
        if source_diff.detail is not None:
            print(f"Source diff: {source_diff.detail}")
        return
    print(
        "Source diff: "
        f"{source_diff.added_count} added, "
        f"{source_diff.removed_count} removed, "
        f"{source_diff.changed_count} changed"
    )
    for label, paths in (
        ("Added", source_diff.added_paths),
        ("Removed", source_diff.removed_paths),
        ("Changed", source_diff.changed_paths),
    ):
        if paths:
            print(f"{label} sample: {', '.join(paths)}")


def _print_index_snapshot(snapshot: RepositoryIndexSnapshot, path: Path) -> None:
    print(f"Repository index: {snapshot.status.value}")
    print(f"Path: {path}")
    print(f"Entries: {len(snapshot.entries)}")
    if snapshot.built_at is not None:
        print(f"Built: {snapshot.built_at.isoformat()}")
    _print_repository_intelligence_counts(
        source_manifest_count=len(snapshot.source_manifests),
        source_root_count=len(snapshot.source_roots),
        test_root_count=len(snapshot.test_roots),
        doc_root_count=len(snapshot.doc_roots),
        generated_path_count=len(snapshot.generated_paths),
        policy_sensitive_path_count=len(snapshot.policy_sensitive_paths),
        package_boundary_count=len(snapshot.package_boundaries),
        command_recipe_count=len(snapshot.command_recipes),
        ownership_hint_count=len(snapshot.ownership_hints),
        subsystem_count=len(snapshot.subsystems),
        release_surface_count=len(snapshot.release_sensitive_surfaces),
    )
    for limitation in snapshot.limitations:
        print(f"Limitation: {limitation}")


def _print_repository_intelligence_counts(
    *,
    source_manifest_count: int,
    source_root_count: int,
    test_root_count: int,
    doc_root_count: int,
    generated_path_count: int,
    policy_sensitive_path_count: int,
    package_boundary_count: int,
    command_recipe_count: int,
    ownership_hint_count: int,
    subsystem_count: int,
    release_surface_count: int,
) -> None:
    if not any(
        (
            source_manifest_count,
            source_root_count,
            test_root_count,
            doc_root_count,
            generated_path_count,
            policy_sensitive_path_count,
            package_boundary_count,
            command_recipe_count,
            ownership_hint_count,
            subsystem_count,
            release_surface_count,
        )
    ):
        return
    print(
        "Intelligence: "
        f"{source_manifest_count} manifests, "
        f"{package_boundary_count} packages, "
        f"{source_root_count} source roots, "
        f"{test_root_count} test roots, "
        f"{doc_root_count} doc roots"
    )
    print(
        "Hints: "
        f"{generated_path_count} generated paths, "
        f"{policy_sensitive_path_count} policy-sensitive paths, "
        f"{command_recipe_count} command recipes, "
        f"{ownership_hint_count} owners, "
        f"{subsystem_count} subsystems, "
        f"{release_surface_count} release surfaces"
    )


def _print_index_entries(entries: list[RepositoryIndexEntry]) -> None:
    if not entries:
        print("No repository index entries found.")
        return
    print(f"Repository index entries: {len(entries)}")
    for entry in entries:
        path = entry.path.as_posix() if entry.path else ""
        print(f"{entry.entry_id}  {entry.kind.value:<16}  {entry.name}  {path}")


def _print_index_entry(entry: RepositoryIndexEntry) -> None:
    print(f"Entry: {entry.entry_id}")
    print(f"Kind: {entry.kind.value}")
    print(f"Name: {entry.name}")
    if entry.path is not None:
        print(f"Path: {entry.path.as_posix()}")
    if entry.symbol is not None:
        print(f"Symbol: {entry.symbol}")
    if entry.summary is not None:
        print(f"Summary: {entry.summary}")
    for provenance in entry.provenance:
        source_path = provenance.path.as_posix() if provenance.path else "operator hint"
        print(f"Source: {provenance.source_type.value} {source_path}")


def _topology_status_payload(
    snapshot: WorkspaceTopologySnapshot,
    path: Path,
) -> dict[str, object]:
    return {
        "freshness": snapshot.freshness,
        "path": str(path),
        "component_count": len(snapshot.components),
        "dependency_count": len(snapshot.dependencies),
        "recommendation_posture": snapshot.recommendation_posture,
        "built_at": snapshot.built_at.isoformat() if snapshot.built_at else None,
        "builder_version": snapshot.builder_version,
        "source_digest": snapshot.source_digest,
        "limitations": snapshot.limitations,
        "failure_reason": snapshot.failure_reason,
        "next_actions": (
            [f"glassbox repo topology build --cwd {path.parent.parent.resolve()}"]
            if snapshot.freshness != "fresh"
            else []
        ),
    }


def _print_topology_status(snapshot: WorkspaceTopologySnapshot, path: Path) -> None:
    print(f"Workspace topology: {snapshot.freshness}")
    print(f"Path: {path}")
    print(f"Components: {len(snapshot.components)}")
    print(f"Dependencies: {len(snapshot.dependencies)}")
    print(f"Recommendation posture: {snapshot.recommendation_posture}")
    if snapshot.built_at is not None:
        print(f"Built: {snapshot.built_at.isoformat()}")
    for limitation in snapshot.limitations:
        print(f"Limitation: {limitation}")


def _print_topology_snapshot(snapshot: WorkspaceTopologySnapshot, path: Path) -> None:
    _print_topology_status(snapshot, path)
    for component in snapshot.components:
        print(
            f"{component.component_id}  {component.kind:<9}  "
            f"{component.name}  {component.root_path.as_posix()}"
        )
    if snapshot.dependencies:
        print("Dependencies:")
        for dependency in snapshot.dependencies[:20]:
            target = dependency.target_component_id or dependency.external_name
            print(f"- {dependency.source_component_id} -> {target} ({dependency.kind})")


def _print_background_job(job: BackgroundJobRecord) -> None:
    print(f"Queued repository index refresh job {job.job_id}: {job.state.value}")


__all__ = ["_repo_command"]
