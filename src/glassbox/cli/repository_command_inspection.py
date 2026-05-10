"""Inspection and recommendation handlers for repository intelligence CLI."""

import argparse
from pathlib import Path

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.replay_eval_formatters import _print_eval_recommendations
from glassbox.cli.repository_command_formatters import _print_command_recipe
from glassbox.cli.repository_command_formatters import _print_command_recipes
from glassbox.cli.repository_command_formatters import _print_index_entries
from glassbox.cli.repository_command_formatters import _print_index_entry
from glassbox.cli.repository_command_formatters import _print_index_snapshot
from glassbox.cli.repository_command_formatters import _print_next_actions
from glassbox.cli.repository_command_formatters import _print_path_intelligence
from glassbox.cli.repository_command_formatters import _print_subsystem
from glassbox.cli.repository_command_formatters import _print_subsystems
from glassbox.cli.repository_command_formatters import _print_topology_snapshot
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
from glassbox.runtime.repository_index import RepositoryIndexLoadError
from glassbox.runtime.repository_index import get_repository_index_entry
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.repository_index import search_repository_index
from glassbox.runtime.workspace_topology import load_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path


def _repo_path_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    try:
        snapshot = load_repository_index(cwd)
    except RepositoryIndexLoadError as exc:
        raise _repository_index_cli_error(exc) from exc
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
    try:
        snapshot = load_repository_index(cwd)
    except RepositoryIndexLoadError as exc:
        raise _repository_index_cli_error(exc) from exc
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
    try:
        snapshot = load_repository_index(cwd)
    except RepositoryIndexLoadError as exc:
        raise _repository_index_cli_error(exc) from exc
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


def _repo_index_search_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, _ = resolve_runtime_location(args)
    try:
        entries = search_repository_index(cwd, args.query, limit=args.limit)
    except RepositoryIndexLoadError as exc:
        raise _repository_index_cli_error(exc) from exc
    if args.json:
        print_json_output([entry.model_dump(mode="json") for entry in entries])
    else:
        _print_index_entries(entries)
    return 0


def _repo_index_show_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    try:
        entry = get_repository_index_entry(cwd, args.entry_id)
    except RepositoryIndexLoadError as exc:
        raise _repository_index_cli_error(exc) from exc
    if args.json:
        print_json_output(entry.model_dump(mode="json"))
    else:
        _print_index_entry(entry)
    return 0


def _repo_index_inspect_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    try:
        snapshot = load_repository_index(cwd)
    except RepositoryIndexLoadError as exc:
        raise _repository_index_cli_error(exc) from exc
    if args.json:
        print_json_output(snapshot.model_dump(mode="json"))
    else:
        _print_index_snapshot(snapshot, repository_index_path(cwd))
    return 0


def _repo_topology_show_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    snapshot = load_workspace_topology(cwd)
    if args.json:
        print_json_output(snapshot.model_dump(mode="json"))
    else:
        _print_topology_snapshot(snapshot, workspace_topology_path(cwd))
    return 0


def _repository_index_cli_error(error: RepositoryIndexLoadError) -> ValueError:
    actions = "; ".join(error.safe_next_actions)
    return ValueError(
        f"{error.detail}. Safe next actions: {actions}. Path: {error.path}"
    )


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


__all__ = [
    "_repo_index_inspect_command",
    "_repo_index_search_command",
    "_repo_index_show_command",
    "_repo_path_command",
    "_repo_recommend_command",
    "_repo_recipes_command",
    "_repo_subsystem_command",
    "_repo_topology_show_command",
]
