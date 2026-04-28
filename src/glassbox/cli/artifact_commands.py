"""CLI command handlers for artifact retention operations."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.store.artifact_retention import ArtifactGcReport
from glassbox.store.artifact_retention import ArtifactRetentionPolicy
from glassbox.store.artifact_retention import inspect_artifact_state
from glassbox.store.artifact_retention import run_artifact_gc


def _artifacts_command(args: argparse.Namespace) -> int:
    if args.artifacts_command == "inspect":
        return _artifact_inspect_command(args)
    if args.artifacts_command == "prune":
        return _artifact_prune_command(args)
    raise ValueError("unknown artifacts command")


def _artifact_inspect_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    _validate_artifact_args(args)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        report = inspect_artifact_state(
            cwd,
            runtime_context.repositories.sessions,
            policy=_artifact_retention_policy(args),
        )

    if args.json:
        print_json_output(report.to_json_payload())
        return 0

    _print_artifact_inspection_report(report)
    return 0


def _artifact_prune_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="prune artifacts locally",
    )
    _validate_artifact_args(args)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        report = run_artifact_gc(
            cwd,
            runtime_context.repositories.sessions,
            policy=_artifact_retention_policy(args),
            dry_run=args.dry_run,
        )

    if args.json:
        print_json_output(report.to_json_payload())
        return 0

    _print_artifact_prune_report(report, dry_run=args.dry_run)
    return 0


def _print_artifact_prune_report(
    report: ArtifactGcReport,
    *,
    dry_run: bool,
) -> None:
    action_label = "Would delete" if dry_run else "Deleted"
    action_count = len(report.candidates) if dry_run else len(report.deleted)
    action_size = report.candidate_size_bytes if dry_run else report.deleted_size_bytes
    print(
        "Artifact prune: "
        f"{len(report.protected)} protected, "
        f"{len(report.candidates)} stale, "
        f"{action_count} {'would be deleted' if dry_run else 'deleted'} "
        f"({action_size} bytes)"
    )
    _print_artifact_pressure_summary(report)
    if report.missing_references:
        print(f"Missing referenced artifacts: {len(report.missing_references)}")
        for path in report.missing_references:
            print(f"  missing {path.as_posix()}")

    entries = report.candidates if dry_run else report.deleted
    for entry in entries:
        print(
            f"{action_label}: {entry.relative_path.as_posix()} "
            f"[{entry.category}, {entry.size_bytes} bytes, "
            f"age {entry.age_days} day(s), sha256 {entry.content_sha256}]"
        )
        print(f"  Reason: {entry.reason}")


def _print_artifact_inspection_report(report: ArtifactGcReport) -> None:
    print(
        "Artifact inspect: "
        f"{len(report.protected)} protected, "
        f"{len(report.candidates)} stale, "
        f"{len(report.missing_references)} missing reference(s), "
        f"{report.candidate_size_bytes} reclaimable bytes"
    )
    _print_artifact_pressure_summary(report)
    if report.missing_references:
        print(f"Missing referenced artifacts: {len(report.missing_references)}")
        for path in report.missing_references:
            print(f"  missing {path.as_posix()}")

    for entry in report.protected:
        print(
            f"Protected: {entry.relative_path.as_posix()} "
            f"[{entry.category}, {entry.size_bytes} bytes, "
            f"age {entry.age_days} day(s), sha256 {entry.content_sha256}]"
        )
        print(f"  Reason: {entry.reason}")

    for entry in report.candidates:
        print(
            f"Stale: {entry.relative_path.as_posix()} "
            f"[{entry.category}, {entry.size_bytes} bytes, "
            f"age {entry.age_days} day(s), sha256 {entry.content_sha256}]"
        )
        print(f"  Reason: {entry.reason}")


def _validate_artifact_args(args: argparse.Namespace) -> None:
    if args.max_age_days < 0:
        raise ValueError("--max-age-days must be zero or greater")
    if args.warning_threshold_mb < 0:
        raise ValueError("--warning-threshold-mb must be zero or greater")


def _artifact_retention_policy(args: argparse.Namespace) -> ArtifactRetentionPolicy:
    threshold_bytes = args.warning_threshold_mb * 1024 * 1024
    return ArtifactRetentionPolicy(
        eval_max_age_days=args.max_age_days,
        storage_warning_threshold_bytes=threshold_bytes,
    )


def _print_artifact_pressure_summary(report: ArtifactGcReport) -> None:
    print(
        "Artifact storage: "
        f"{report.reported_count} managed file(s), "
        f"{report.reported_size_bytes} reported bytes, "
        f"{report.glassbox_size_bytes} total .glassbox bytes"
    )
    print(f"Retention classes: {_format_category_counts(report.category_counts)}")
    if report.oldest_age_days is not None:
        print(f"Oldest managed artifact age: {report.oldest_age_days} day(s)")
    if report.storage_warning is not None:
        print(f"Storage warning: {report.storage_warning}")


def _format_category_counts(category_counts: dict[str, int]) -> str:
    if not category_counts:
        return "none"
    return ", ".join(
        f"{category}={count}" for category, count in sorted(category_counts.items())
    )
