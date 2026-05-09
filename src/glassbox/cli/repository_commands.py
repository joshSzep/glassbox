"""CLI command handlers for local repository intelligence."""

import argparse
from pathlib import Path
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.replay_eval_formatters import _print_eval_recommendations
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
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
from glassbox.runtime.repository_intelligence_freshness import (
    workspace_topology_freshness_cues,
)
from glassbox.runtime.workspace_memory_capture import MemoryExtractionPolicy
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureRepository
from glassbox.runtime.workspace_memory_capture import WorkspaceMemoryCaptureService
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot
from glassbox.runtime.workspace_topology import build_and_write_workspace_topology
from glassbox.runtime.workspace_topology import build_workspace_topology
from glassbox.runtime.workspace_topology import load_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path
from glassbox.runtime.workspace_topology import write_workspace_topology


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


def _repo_status_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    index_summary = build_repository_index_status_summary(cwd)
    topology_payload = _load_topology_status_payload(cwd)
    payload = {
        "index": index_summary.model_dump(mode="json"),
        "topology": topology_payload,
        "next_actions": _repo_status_next_actions(
            index_summary.next_actions,
            topology_payload.get("next_actions", []),
            cwd,
        ),
    }
    if args.json:
        print_json_output(payload)
    else:
        print("Repository intelligence status")
        _print_status_summary(index_summary)
        print("")
        _print_topology_status_payload(topology_payload)
        _print_next_actions(payload["next_actions"])
    return 0


def _repo_stale_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    index_summary = build_repository_index_status_summary(cwd)
    topology_payload = _load_topology_status_payload(cwd)
    cues = [
        cue.model_dump(mode="json")
        for cue in index_summary.freshness_cues
        if cue.state != "fresh"
    ]
    topology_cues = topology_payload.get("freshness_cues", [])
    if isinstance(topology_cues, list):
        cues.extend(
            cue
            for cue in topology_cues
            if isinstance(cue, dict)
            and cast(dict[str, object], cue).get("state") != "fresh"
        )
    payload = {
        "cues": cues,
        "next_actions": _repo_status_next_actions(
            index_summary.next_actions,
            topology_payload.get("next_actions", []),
            cwd,
        ),
    }
    if args.json:
        print_json_output(payload)
    else:
        if not cues:
            print("Repository intelligence has no stale or missing cues.")
        else:
            print("Repository intelligence cues:")
            for cue in cues:
                print(
                    f"- {cue['source']}: {cue['state']} "
                    f"({cue['reason']}) - {cue['detail']}"
                )
        _print_next_actions(payload["next_actions"])
    return 0


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
    index_snapshot = build_and_write_repository_index(
        cwd,
        workspace_memory_entries=memory_entries,
    )
    topology_snapshot = build_workspace_topology(
        cwd,
        repository_index=index_snapshot,
    )
    write_workspace_topology(cwd, topology_snapshot)
    payload = {
        "index": index_snapshot.model_dump(mode="json"),
        "topology": topology_snapshot.model_dump(mode="json"),
    }
    if args.json:
        print_json_output(payload)
    else:
        print("Repository intelligence refreshed.")
        _print_index_snapshot(index_snapshot, repository_index_path(cwd))
        print("")
        _print_topology_status(topology_snapshot, workspace_topology_path(cwd))
    return 0


def _repo_path_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    snapshot = load_repository_index(cwd)
    path = _workspace_relative_path(cwd, args.path)
    payload = _path_intelligence_payload(snapshot, path)
    if args.json:
        print_json_output(payload)
    else:
        _print_path_intelligence(payload)
    return 0


def _repo_recommend_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    try:
        recommendation = recommend_eval_change_impact(
            cwd,
            touched_paths=list(args.paths),
        )
    except ValueError as exc:
        payload = {
            "status": "unavailable",
            "paths": list(args.paths),
            "detail": str(exc),
            "next_actions": [
                "inspect repository intelligence with `glassbox repo status --cwd .`",
                "run `glassbox eval audit --cwd .` after eval metadata exists",
            ],
        }
        if args.json:
            print_json_output(payload)
        else:
            print("Repository verification recommendations unavailable.")
            print(f"Detail: {exc}")
            _print_next_actions(payload["next_actions"])
        return 0
    if args.json:
        print_json_output(recommendation.model_dump(mode="json"))
    else:
        _print_eval_recommendations(recommendation)
        print("Next action: glassbox eval recommend " + " ".join(args.paths))
    return 0


def _repo_recipes_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    snapshot = load_repository_index(cwd)
    command = getattr(args, "repo_recipes_command", None)
    if command == "list":
        recipes = snapshot.command_recipes
        if args.json:
            print_json_output([recipe.model_dump(mode="json") for recipe in recipes])
        else:
            _print_command_recipes(recipes)
        return 0
    if command == "show":
        recipe = next(
            (
                candidate
                for candidate in snapshot.command_recipes
                if candidate.recipe_id == args.recipe_id
            ),
            None,
        )
        if recipe is None:
            raise ValueError(f"unknown command recipe: {args.recipe_id}")
        if args.json:
            print_json_output(recipe.model_dump(mode="json"))
        else:
            _print_command_recipe(recipe)
        return 0
    raise ValueError(f"unsupported repo recipes subcommand: {command}")


def _repo_subsystem_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    snapshot = load_repository_index(cwd)
    command = getattr(args, "repo_subsystem_command", None)
    if command == "list":
        if args.json:
            print_json_output(
                [subsystem.model_dump(mode="json") for subsystem in snapshot.subsystems]
            )
        else:
            _print_subsystems(snapshot.subsystems)
        return 0
    if command == "show":
        subsystem = next(
            (
                candidate
                for candidate in snapshot.subsystems
                if candidate.subsystem_id == args.subsystem_id
            ),
            None,
        )
        if subsystem is None:
            raise ValueError(f"unknown subsystem: {args.subsystem_id}")
        if args.json:
            print_json_output(subsystem.model_dump(mode="json"))
        else:
            _print_subsystem(subsystem)
        return 0
    raise ValueError(f"unsupported repo subsystem subcommand: {command}")


def _repo_memory_candidates_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        candidates = WorkspaceMemoryCaptureService(
            cast(
                WorkspaceMemoryCaptureRepository,
                runtime_context.repositories.sessions,
            )
        ).list_candidates(
            args.session_id,
            policy=MemoryExtractionPolicy(max_candidates=args.limit),
        )
    if args.json:
        print_json_output(
            [candidate.model_dump(mode="json") for candidate in candidates]
        )
    else:
        if not candidates:
            print("No repository memory candidates found.")
        else:
            print(f"Repository memory candidates: {len(candidates)}")
            for candidate in candidates:
                print(f"- {candidate.candidate_id}: {candidate.kind.value}")
                print(f"  {candidate.summary}")
                print(
                    "  Review: glassbox memory confirm-candidate "
                    f"{candidate.session_id} {candidate.candidate_id}"
                )
    return 0


def _load_topology_status_payload(cwd: Path) -> dict[str, object]:
    path = workspace_topology_path(cwd)
    try:
        snapshot = load_workspace_topology(cwd)
    except WorkspaceTopologyNotFoundError:
        return {
            "freshness": "missing",
            "path": str(path),
            "component_count": 0,
            "dependency_count": 0,
            "recommendation_posture": "unavailable",
            "detail": "workspace topology has not been built",
            "freshness_cues": [
                cue.model_dump(mode="json")
                for cue in workspace_topology_freshness_cues(cwd, None)
            ],
            "next_actions": [f"glassbox repo topology build --cwd {cwd.resolve()}"],
        }
    return _topology_status_payload(snapshot, path)


def _repo_status_next_actions(
    index_actions: list[str],
    topology_actions: object,
    cwd: Path,
) -> list[str]:
    actions = [*index_actions]
    if isinstance(topology_actions, list):
        actions.extend(str(action) for action in topology_actions)
    actions.append(f"glassbox repo refresh --cwd {cwd.resolve()}")
    return list(dict.fromkeys(actions))


def _workspace_relative_path(cwd: Path, value: str) -> Path:
    raw_path = Path(value)
    if raw_path.is_absolute():
        return raw_path.resolve().relative_to(cwd.resolve())
    if ".." in raw_path.parts:
        raise ValueError("repository path must stay inside the workspace")
    return raw_path


def _path_intelligence_payload(
    snapshot: RepositoryIndexSnapshot,
    path: Path,
) -> dict[str, object]:
    packages = [
        package
        for package in snapshot.package_boundaries
        if _scope_contains(package.root, path)
        or any(_scope_contains(scope, path) for scope in package.source_roots)
        or any(_scope_contains(scope, path) for scope in package.test_roots)
        or any(_scope_contains(scope, path) for scope in package.doc_roots)
    ]
    path_hints = [
        hint for hint in _all_path_hints(snapshot) if _scope_contains(hint.path, path)
    ]
    subsystems = [
        subsystem
        for subsystem in snapshot.subsystems
        if any(_scope_contains(scope, path) for scope in subsystem.scope_paths)
    ]
    recipes = [
        recipe
        for recipe in snapshot.command_recipes
        if not recipe.scope_paths
        or any(_scope_contains(scope, path) for scope in recipe.scope_paths)
    ]
    owner_scope_ids = {
        owner.hint_id
        for owner in snapshot.ownership_hints
        if any(_scope_contains(scope, path) for scope in owner.scope_paths)
    }
    owner_scope_ids.update(
        owner_id for subsystem in subsystems for owner_id in subsystem.owner_hint_ids
    )
    owners = [
        owner for owner in snapshot.ownership_hints if owner.hint_id in owner_scope_ids
    ]
    release_surface_ids = {
        surface_id
        for subsystem in subsystems
        for surface_id in subsystem.release_surface_ids
    }
    release_surfaces = [
        surface
        for surface in snapshot.release_sensitive_surfaces
        if surface.surface_id in release_surface_ids
        or any(_scope_contains(scope, path) for scope in surface.scope_paths)
    ]
    return {
        "path": path.as_posix(),
        "snapshot_status": snapshot.status.value,
        "packages": [package.model_dump(mode="json") for package in packages],
        "path_hints": [hint.model_dump(mode="json") for hint in path_hints],
        "subsystems": [subsystem.model_dump(mode="json") for subsystem in subsystems],
        "command_recipes": [recipe.model_dump(mode="json") for recipe in recipes],
        "ownership_hints": [owner.model_dump(mode="json") for owner in owners],
        "release_surfaces": [
            surface.model_dump(mode="json") for surface in release_surfaces
        ],
        "next_actions": [
            f"glassbox repo recommend {path.as_posix()}",
            f"glassbox eval recommend {path.as_posix()}",
        ],
    }


def _all_path_hints(snapshot: RepositoryIndexSnapshot):
    return [
        *snapshot.source_roots,
        *snapshot.test_roots,
        *snapshot.doc_roots,
        *snapshot.generated_paths,
        *snapshot.policy_sensitive_paths,
    ]


def _scope_contains(scope: Path, path: Path) -> bool:
    scope_value = Path(".") if scope.as_posix() in {"", "."} else scope
    path_value = Path(".") if path.as_posix() in {"", "."} else path
    return path_value == scope_value or path_value.is_relative_to(scope_value)


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
    snapshot = build_and_write_repository_index(
        cwd,
        workspace_memory_entries=memory_entries,
    )
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
                    "freshness_cues": [
                        cue.model_dump(mode="json")
                        for cue in workspace_topology_freshness_cues(cwd, None)
                    ],
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
        memory_reference_count=summary.memory_reference_count,
    )
    for limitation in summary.limitations:
        print(f"Limitation: {limitation}")
    if summary.source_diff is not None:
        _print_source_diff(summary.source_diff)
    if summary.freshness_cues:
        print("Freshness cues:")
        for cue in summary.freshness_cues:
            print(f"- {cue.source}: {cue.state} ({cue.reason}) - {cue.detail}")
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
        memory_reference_count=len(snapshot.memory_references),
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
    memory_reference_count: int = 0,
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
            memory_reference_count,
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
        f"{release_surface_count} release surfaces, "
        f"{memory_reference_count} memory references"
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
        "freshness_cues": [
            cue.model_dump(mode="json")
            for cue in workspace_topology_freshness_cues(
                snapshot.workspace_root,
                snapshot,
            )
        ],
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
    for cue in workspace_topology_freshness_cues(snapshot.workspace_root, snapshot):
        print(f"Freshness: {cue.source} {cue.state} ({cue.reason}) - {cue.detail}")


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


def _print_topology_status_payload(payload: dict[str, object]) -> None:
    print(f"Workspace topology: {payload['freshness']}")
    print(f"Path: {payload['path']}")
    print(f"Components: {payload['component_count']}")
    print(f"Dependencies: {payload['dependency_count']}")
    print(f"Recommendation posture: {payload['recommendation_posture']}")
    detail = payload.get("detail")
    if isinstance(detail, str):
        print(f"Detail: {detail}")


def _print_next_actions(actions: object) -> None:
    if not isinstance(actions, list) or not actions:
        return
    print("Next actions:")
    for action in actions:
        print(f"- {action}")


def _print_path_intelligence(payload: dict[str, object]) -> None:
    print(f"Repository path: {payload['path']}")
    print(f"Snapshot status: {payload['snapshot_status']}")
    for label, key in (
        ("Packages", "packages"),
        ("Path hints", "path_hints"),
        ("Subsystems", "subsystems"),
        ("Command recipes", "command_recipes"),
        ("Owners", "ownership_hints"),
        ("Release surfaces", "release_surfaces"),
    ):
        values = payload[key]
        if isinstance(values, list):
            print(f"{label}: {len(values)}")
            for value in values[:8]:
                if isinstance(value, dict):
                    identifier = (
                        value.get("package_id")
                        or value.get("hint_id")
                        or value.get("subsystem_id")
                        or value.get("recipe_id")
                        or value.get("surface_id")
                        or value.get("owner_label")
                    )
                    name = value.get("name")
                    print(f"  - {identifier}" + (f": {name}" if name else ""))
    _print_next_actions(payload.get("next_actions"))


def _print_command_recipes(recipes) -> None:
    if not recipes:
        print("No command recipes found.")
        return
    print(f"Command recipes: {len(recipes)}")
    for recipe in recipes:
        print(f"- {recipe.recipe_id}: {recipe.name}")
        print(f"  Command: {recipe.command}")
        print(f"  Purpose: {recipe.purpose.value}, risk {recipe.risk.value}")


def _print_command_recipe(recipe) -> None:
    print(f"Recipe: {recipe.recipe_id}")
    print(f"Name: {recipe.name}")
    print(f"Command: {recipe.command}")
    print(f"Purpose: {recipe.purpose.value}")
    print(f"Review relevance: {recipe.review_relevance.value}")
    print(f"Risk: {recipe.risk.value}")
    print(f"Confidence: {recipe.confidence.value}")
    if recipe.scope_paths:
        print("Scope: " + ", ".join(path.as_posix() for path in recipe.scope_paths))
    for limitation in recipe.limitations:
        print(f"Limitation: {limitation}")


def _print_subsystems(subsystems) -> None:
    if not subsystems:
        print("No subsystems found.")
        return
    print(f"Subsystems: {len(subsystems)}")
    for subsystem in subsystems:
        print(f"- {subsystem.subsystem_id}: {subsystem.name}")
        print(
            "  Scope: " + ", ".join(path.as_posix() for path in subsystem.scope_paths)
        )


def _print_subsystem(subsystem) -> None:
    print(f"Subsystem: {subsystem.subsystem_id}")
    print(f"Name: {subsystem.name}")
    print(f"Confidence: {subsystem.confidence.value}")
    print("Scope: " + ", ".join(path.as_posix() for path in subsystem.scope_paths))
    if subsystem.package_ids:
        print("Packages: " + ", ".join(subsystem.package_ids))
    if subsystem.owner_hint_ids:
        print("Owner hints: " + ", ".join(subsystem.owner_hint_ids))
    if subsystem.release_surface_ids:
        print("Release surfaces: " + ", ".join(subsystem.release_surface_ids))


def _print_background_job(job: BackgroundJobRecord) -> None:
    if job.job_type == "repository-index-refresh":
        label = "repository index refresh"
    else:
        label = "repository intelligence refresh"
    print(f"Queued {label} job {job.job_id}: {job.state.value}")


__all__ = ["_repo_command"]
