"""CLI commands for context compaction workflows."""

import argparse
from pathlib import Path

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.types import ContextCompactionScope
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.context_compaction_service import (
    create_deterministic_context_compaction,
)
from glassbox.runtime.context_compaction_service import invalidate_context_compaction
from glassbox.runtime.context_compaction_service import refresh_context_compaction


def _session_compact_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="create a context compaction locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        payload = create_deterministic_context_compaction(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
            args.session_id,
            scope=ContextCompactionScope(args.scope),
            task_id=args.task_id,
            source_start_sequence=args.source_start_sequence,
            source_end_sequence=args.source_end_sequence,
        )

    if args.json:
        print_json_output(payload.model_dump(mode="json"))
        return 0

    print(
        "Created context compaction "
        f"{payload.compaction_id} for source events "
        f"{payload.source_start_sequence}-{payload.source_end_sequence}"
    )
    print(
        f"Artifact: {_compaction_artifact_path(args.session_id, payload.artifact_id)}"
    )
    print(f"Summary: {payload.summary}")
    return 0


def _session_compactions_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        rows = repository.list_context_compactions(
            args.session_id,
            task_id=args.task_id,
            limit=args.limit,
        )

    if args.json:
        print_json_output([row.model_dump(mode="json") for row in rows])
        return 0

    if not rows:
        print("No context compactions found")
        return 0

    print(f"Context compactions: {len(rows)}")
    for row in rows:
        print(
            f"{row.compaction_id}  {row.scope.value}  "
            f"events {row.source_start_sequence}-{row.source_end_sequence}  "
            f"{row.freshness.value}"
        )
        print(
            f"  Artifact: {_compaction_artifact_path(row.session_id, row.artifact_id)}"
        )
        print(f"  Summary: {row.summary}")
        if row.freshness_reason:
            print(f"  Freshness reason: {row.freshness_reason}")
        if row.superseded_by_compaction_id:
            print(f"  Superseded by: {row.superseded_by_compaction_id}")
        if row.limitations:
            print(f"  Limitations: {'; '.join(row.limitations)}")
    return 0


def _session_compaction_refresh_command(args: argparse.Namespace) -> int:
    if not args.yes:
        print(
            "Refreshing a context compaction records a replacement artifact and "
            "marks the original stale. Re-run with --yes to confirm."
        )
        return 2

    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="refresh a context compaction locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        refreshed, change = refresh_context_compaction(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
            args.session_id,
            args.compaction_id,
            reason=args.reason,
        )

    if args.json:
        print_json_output(
            {
                "refreshed_compaction": refreshed.model_dump(mode="json"),
                "previous_compaction": change.model_dump(mode="json"),
            }
        )
        return 0

    print(
        "Refreshed context compaction "
        f"{args.compaction_id} with replacement {refreshed.compaction_id}"
    )
    print(
        "Replacement source events: "
        f"{refreshed.source_start_sequence}-{refreshed.source_end_sequence}"
    )
    print(f"Previous freshness reason: {change.reason}")
    return 0


def _session_compaction_invalidate_command(args: argparse.Namespace) -> int:
    if not args.yes:
        print(
            "Invalidating a context compaction keeps the artifact for audit but "
            "excludes it from active prompt context. Re-run with --yes to confirm."
        )
        return 2

    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="invalidate a context compaction locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        change = invalidate_context_compaction(
            runtime_context.repositories.sessions,
            args.session_id,
            args.compaction_id,
            reason=args.reason,
        )

    if args.json:
        print_json_output(change.model_dump(mode="json"))
        return 0

    print(f"Invalidated context compaction {args.compaction_id}")
    print(f"Freshness reason: {change.reason}")
    return 0


def _compaction_artifact_path(session_id, artifact_id) -> str:
    return (
        Path(".glassbox")
        / "sessions"
        / str(session_id)
        / "artifacts"
        / f"{artifact_id}.context-compaction.json"
    ).as_posix()


__all__ = [
    "_session_compact_command",
    "_session_compaction_invalidate_command",
    "_session_compaction_refresh_command",
    "_session_compactions_command",
]
