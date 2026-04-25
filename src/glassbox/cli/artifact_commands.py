"""CLI command handlers for artifact retention operations."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.store.artifact_retention import ArtifactGcReport
from glassbox.store.artifact_retention import ArtifactRetentionPolicy
from glassbox.store.artifact_retention import run_artifact_gc


def _artifacts_command(args: argparse.Namespace) -> int:
    if args.artifacts_command == "gc":
        return _artifact_gc_command(args)
    raise ValueError("unknown artifacts command")


def _artifact_gc_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="garbage collect artifacts locally",
    )
    if args.max_age_days < 0:
        raise ValueError("--max-age-days must be zero or greater")

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        report = run_artifact_gc(
            cwd,
            runtime_context.repositories.sessions,
            policy=ArtifactRetentionPolicy(eval_max_age_days=args.max_age_days),
            dry_run=args.dry_run,
        )

    if args.json:
        print_json_output(report.to_json_payload())
        return 0

    _print_artifact_gc_report(report, dry_run=args.dry_run)
    return 0


def _print_artifact_gc_report(
    report: ArtifactGcReport,
    *,
    dry_run: bool,
) -> None:
    action_label = "Would delete" if dry_run else "Deleted"
    action_count = len(report.candidates) if dry_run else len(report.deleted)
    action_size = report.candidate_size_bytes if dry_run else report.deleted_size_bytes
    print(
        "Artifact GC: "
        f"{len(report.protected)} protected, "
        f"{len(report.candidates)} stale, "
        f"{action_count} {'would be deleted' if dry_run else 'deleted'} "
        f"({action_size} bytes)"
    )
    if report.missing_references:
        print(f"Missing referenced artifacts: {len(report.missing_references)}")
        for path in report.missing_references:
            print(f"  missing {path.as_posix()}")

    entries = report.candidates if dry_run else report.deleted
    for entry in entries:
        print(
            f"{action_label}: {entry.relative_path.as_posix()} "
            f"[{entry.category}, {entry.size_bytes} bytes, "
            f"sha256 {entry.content_sha256}]"
        )
        print(f"  Reason: {entry.reason}")
