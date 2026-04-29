"""CLI command handlers for workspace memory inspection."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.bootstrap import open_runtime_context


def _memory_command(args: argparse.Namespace) -> int:
    memory_command = getattr(args, "memory_command", None)
    if memory_command == "list":
        return _memory_list_command(args)
    if memory_command == "show":
        return _memory_show_command(args)
    if memory_command == "confirm":
        return _memory_confirm_command(args)
    if memory_command == "invalidate":
        return _memory_invalidate_command(args)
    if memory_command == "prune":
        return _memory_prune_command(args)
    raise ValueError(f"unsupported memory subcommand: {memory_command}")


def _memory_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        entries = runtime_context.repositories.sessions.list_workspace_memory(
            state=_optional_state(args.state),
            kind=_optional_kind(args.kind),
            query_text=args.query,
            include_pruned=args.include_pruned,
            limit=args.limit,
        )
    if args.json:
        print_json_output([entry.model_dump(mode="json") for entry in entries])
    else:
        _print_memory_list(entries)
    return 0


def _memory_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        entry = runtime_context.repositories.sessions.get_workspace_memory(
            args.memory_id
        )
    if entry is None:
        raise ValueError(f"unknown workspace memory: {args.memory_id}")
    if args.json:
        print_json_output(entry.model_dump(mode="json"))
    else:
        _print_memory_detail(entry)
    return 0


def _memory_confirm_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        entry = runtime_context.repositories.sessions.confirm_workspace_memory(
            args.memory_id,
            confirmed_by=args.confirmed_by,
            reason=args.reason,
        )
    if args.json:
        print_json_output(entry.model_dump(mode="json"))
    else:
        print(f"Confirmed workspace memory {entry.memory_id}: {entry.state.value}")
    return 0


def _memory_invalidate_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        entry = runtime_context.repositories.sessions.invalidate_workspace_memory(
            args.memory_id,
            invalidated_by=args.invalidated_by,
            reason=args.reason,
        )
    if args.json:
        print_json_output(entry.model_dump(mode="json"))
    else:
        print(f"Invalidated workspace memory {entry.memory_id}: {entry.state.value}")
    return 0


def _memory_prune_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        if args.dry_run:
            entry = runtime_context.repositories.sessions.get_workspace_memory(
                args.memory_id
            )
            if entry is None:
                raise ValueError(f"unknown workspace memory: {args.memory_id}")
        else:
            entry = runtime_context.repositories.sessions.prune_workspace_memory(
                args.memory_id,
                pruned_by=args.pruned_by,
                reason=args.reason,
            )
    if args.json:
        print_json_output(entry.model_dump(mode="json"))
    elif args.dry_run:
        print(f"Would prune workspace memory {entry.memory_id}: {entry.state.value}")
    else:
        print(f"Pruned workspace memory {entry.memory_id}: {entry.state.value}")
    return 0


def _optional_state(value: str | None) -> WorkspaceMemoryState | None:
    if value is None:
        return None
    return WorkspaceMemoryState(value)


def _optional_kind(value: str | None) -> WorkspaceMemoryKind | None:
    if value is None:
        return None
    return WorkspaceMemoryKind(value)


def _print_memory_list(entries: list[WorkspaceMemoryEntry]) -> None:
    if not entries:
        print("No workspace memory found.")
        return
    print(f"Workspace memory: {len(entries)}")
    for entry in entries:
        summary = entry.summary or entry.content
        print(
            f"{entry.memory_id}  {entry.state.value:<12}  "
            f"{entry.kind.value:<18}  {summary}"
        )


def _print_memory_detail(entry: WorkspaceMemoryEntry) -> None:
    print(f"Memory: {entry.memory_id}")
    print(f"Session: {entry.session_id}")
    print(f"State: {entry.state.value}")
    print(f"Kind: {entry.kind.value}")
    print(f"Summary: {entry.summary or ''}")
    print(f"Content: {entry.content}")
    print(f"Source: {entry.provenance.source_type.value}")
    if entry.provenance.source_label is not None:
        print(f"Source label: {entry.provenance.source_label}")
    if entry.confirmed_by is not None:
        print(f"Confirmed by: {entry.confirmed_by}")
    if entry.invalidated_by is not None:
        print(f"Invalidated by: {entry.invalidated_by}")
    if entry.invalidation_reason is not None:
        print(f"Invalidation reason: {entry.invalidation_reason}")
    if entry.pruned_by is not None:
        print(f"Pruned by: {entry.pruned_by}")
    if entry.prune_reason is not None:
        print(f"Prune reason: {entry.prune_reason}")
    print(f"Redacted: {'yes' if entry.redacted else 'no'}")
    print(f"Updated: {entry.updated_at.isoformat()}")


__all__ = ["_memory_command"]
