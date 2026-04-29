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
from glassbox.runtime.repository_index import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import get_repository_index_entry
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.repository_index import search_repository_index


def _repo_command(args: argparse.Namespace) -> int:
    repo_command = getattr(args, "repo_command", None)
    if repo_command == "index":
        return _repo_index_command(args)
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
    raise ValueError(f"unsupported repo index subcommand: {index_command}")


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
    try:
        snapshot = load_repository_index(cwd)
    except RepositoryIndexNotFoundError:
        if args.json:
            print_json_output(
                {
                    "status": "missing",
                    "path": str(repository_index_path(cwd)),
                    "entry_count": 0,
                }
            )
        else:
            print(f"Repository index: missing at {repository_index_path(cwd)}")
        return 0
    if args.json:
        print_json_output(_status_payload(snapshot, repository_index_path(cwd)))
    else:
        _print_index_snapshot(snapshot, repository_index_path(cwd))
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


def _status_payload(snapshot: RepositoryIndexSnapshot, path: Path) -> dict[str, object]:
    return {
        "status": snapshot.status.value,
        "path": str(path),
        "entry_count": len(snapshot.entries),
        "built_at": snapshot.built_at.isoformat() if snapshot.built_at else None,
        "schema_version": snapshot.schema_version,
        "builder_version": snapshot.builder_version,
        "source_digest": snapshot.source_digest,
    }


def _print_index_snapshot(snapshot: RepositoryIndexSnapshot, path: Path) -> None:
    print(f"Repository index: {snapshot.status.value}")
    print(f"Path: {path}")
    print(f"Entries: {len(snapshot.entries)}")
    if snapshot.built_at is not None:
        print(f"Built: {snapshot.built_at.isoformat()}")


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


def _print_background_job(job: BackgroundJobRecord) -> None:
    print(f"Queued repository index refresh job {job.job_id}: {job.state.value}")


__all__ = ["_repo_command"]
