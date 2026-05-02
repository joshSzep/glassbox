"""CLI command handlers for temporary local worktree isolation."""

import argparse
from pathlib import Path
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.types import WorktreeSourceKind
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.worktree_isolation import WorktreeCleanupResult
from glassbox.runtime.worktree_isolation import WorktreeCreateResult
from glassbox.runtime.worktree_isolation import WorktreeIsolationService
from glassbox.runtime.worktree_isolation import WorktreeRecord
from glassbox.runtime.worktree_isolation import WorktreeRepository


def _worktree_command(args: argparse.Namespace) -> int:
    command = getattr(args, "worktree_command", None)
    if command == "create":
        return _worktree_create_command(args)
    if command == "list":
        return _worktree_list_command(args)
    if command == "status":
        return _worktree_status_command(args)
    if command == "cleanup":
        return _worktree_cleanup_command(args)
    raise ValueError("specify a worktree subcommand")


def _worktree_create_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    source_kind = _source_kind_from_cli(args.source_kind)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = WorktreeIsolationService(
            cast(WorktreeRepository, runtime_context.repositories.sessions)
        )
        result = service.create(
            session_id=args.session_id,
            workspace_root=cwd,
            source_kind=source_kind,
            source_id=_source_id_from_args(args),
            changeset_id=args.changeset_id,
            branch_search_id=args.branch_search_id,
            branch_candidate_id=args.branch_candidate_id,
            base_revision=args.base_revision,
            branch_name=args.branch_name,
            path=Path(args.path) if args.path is not None else None,
            created_by=args.actor,
        )

    if args.json:
        print_json_output(_create_payload(result))
    else:
        record = result.record
        print(f"Created worktree {record.worktree_id}")
        print(f"Path: {record.path}")
        print(f"Branch: {record.branch_name}")
        print(f"Base: {record.base_revision}")
        print("Glassbox did not merge, commit, push, or open a PR.")
    return 0


def _worktree_list_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = WorktreeIsolationService(
            cast(WorktreeRepository, runtime_context.repositories.sessions)
        )
        records = service.list_worktrees(
            workspace_root=cwd,
            session_id=args.session_id,
            include_cleaned=args.include_cleaned,
        )

    if args.json:
        print_json_output([record.model_dump(mode="json") for record in records])
    else:
        _print_worktree_list(records)
    return 0


def _worktree_status_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = WorktreeIsolationService(
            cast(WorktreeRepository, runtime_context.repositories.sessions)
        )
        record, event = service.record_status(
            args.worktree_id,
            workspace_root=cwd,
            inspected_by=args.actor,
        )

    if args.json:
        payload = record.model_dump(mode="json")
        payload["event"] = event.model_dump(mode="json")
        print_json_output(payload)
    else:
        _print_worktree_detail(record)
        print(f"Status event sequence: {event.sequence}")
    return 0


def _worktree_cleanup_command(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ValueError(
            "cleanup requires --confirm after inspecting `glassbox worktree status`"
        )
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        service = WorktreeIsolationService(
            cast(WorktreeRepository, runtime_context.repositories.sessions)
        )
        result = service.cleanup(
            args.worktree_id,
            workspace_root=cwd,
            confirmed_by=args.actor,
            discard_user_changes=args.discard_user_changes,
        )

    if args.json:
        print_json_output(_cleanup_payload(result))
    else:
        _print_cleanup_result(result)
    return 1 if result.blocked else 0


def _source_kind_from_cli(value: str) -> WorktreeSourceKind:
    if value == "branch-search-candidate":
        return WorktreeSourceKind.BRANCH_SEARCH_CANDIDATE
    return WorktreeSourceKind(value)


def _source_id_from_args(args: argparse.Namespace) -> str | None:
    if args.source_id:
        return args.source_id
    if args.branch_candidate_id is not None:
        return str(args.branch_candidate_id)
    if args.changeset_id is not None:
        return str(args.changeset_id)
    if args.branch_search_id is not None:
        return str(args.branch_search_id)
    if args.source_kind == "session":
        return str(args.session_id)
    return None


def _create_payload(result: WorktreeCreateResult) -> dict[str, object]:
    return {
        "worktree": result.record.model_dump(mode="json"),
        "event": result.event.model_dump(mode="json"),
        "safe_copy": (
            "Glassbox created a local worktree only; it did not merge, commit, "
            "push, or open a PR."
        ),
    }


def _cleanup_payload(result: WorktreeCleanupResult) -> dict[str, object]:
    return {
        "worktree": result.record.model_dump(mode="json"),
        "event": result.event.model_dump(mode="json"),
        "removed": result.removed,
        "blocked": result.blocked,
        "reason": result.reason,
    }


def _print_worktree_list(records: list[WorktreeRecord]) -> None:
    if not records:
        print("No worktrees found")
        return
    print(f"Worktrees: {len(records)}")
    for record in records:
        print(
            f"{record.worktree_id}  {record.state.value}  "
            f"{record.source_kind.value}  updated {record.updated_at}"
        )
        print(f"  Path: {record.path}")
        print(f"  Branch: {record.branch_name}")
        if record.status.dirty:
            print("  Cleanup: blocked until local changes are reviewed")


def _print_worktree_detail(record: WorktreeRecord) -> None:
    print(f"Worktree {record.worktree_id}")
    print(f"State: {record.state.value}")
    print(f"Path: {record.path}")
    print(f"Branch: {record.branch_name}")
    print(f"Base: {record.base_revision}")
    print(f"Path exists: {record.status.path_exists}")
    print(f"Dirty: {record.status.dirty}")
    if record.status.current_branch:
        print(f"Current branch: {record.status.current_branch}")
    if record.status.head_revision:
        print(f"HEAD: {record.status.head_revision}")
    if record.status.git_status_short:
        print("Git status:")
        for line in record.status.git_status_short:
            print(f"  {line}")
    if record.status.limitations:
        print("Limitations:")
        for limitation in record.status.limitations:
            print(f"  - {limitation}")
    print("Safe next actions:")
    for action in record.status.safe_next_actions:
        print(f"  - {action}")
    print("Glassbox did not merge, commit, push, or open a PR.")


def _print_cleanup_result(result: WorktreeCleanupResult) -> None:
    print(f"Cleanup state: {result.record.state.value}")
    print(f"Reason: {result.reason}")
    print(f"Removed: {result.removed}")
    if result.blocked:
        print("Safe next actions:")
        for action in result.record.status.safe_next_actions:
            print(f"  - {action}")
    print("Glassbox did not merge, commit, push, or open a PR.")


__all__ = ["_worktree_command"]
