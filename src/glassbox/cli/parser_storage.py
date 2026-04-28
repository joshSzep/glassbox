"""Artifact and backup argument parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments


def _add_artifact_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    artifacts_parser = subparsers.add_parser(
        "artifacts",
        help="inspect and clean managed artifact files",
        description=(
            "Inspect managed Glassbox artifact files and remove stale derived "
            "outputs without touching canonical event data."
        ),
    )
    artifacts_subparsers = artifacts_parser.add_subparsers(
        dest="artifacts_command",
        required=True,
    )

    inspect_parser = artifacts_subparsers.add_parser(
        "inspect",
        help="inspect managed artifact state",
        description=(
            "Inspect managed .glassbox artifacts without deleting files. "
            "Event-referenced session artifacts and source-controlled eval "
            "bundles are protected."
        ),
    )
    _add_runtime_location_arguments(inspect_parser)
    inspect_parser.add_argument(
        "--max-age-days",
        type=int,
        default=30,
        help="age threshold for managed .glassbox/evals artifacts",
    )
    inspect_parser.add_argument(
        "--warning-threshold-mb",
        type=int,
        default=512,
        help="warn when local .glassbox storage meets or exceeds this size",
    )
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="print the artifact inspection report as JSON",
    )

    prune_parser = artifacts_subparsers.add_parser(
        "prune",
        help="prune stale managed artifacts",
        description=(
            "Report or remove stale .glassbox artifacts. Event-referenced "
            "session artifacts and source-controlled eval bundles are protected."
        ),
    )
    _add_runtime_location_arguments(prune_parser)
    prune_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report cleanup actions without deleting files",
    )
    prune_parser.add_argument(
        "--max-age-days",
        type=int,
        default=30,
        help="age threshold for managed .glassbox/evals artifacts",
    )
    prune_parser.add_argument(
        "--warning-threshold-mb",
        type=int,
        default=512,
        help="warn when local .glassbox storage meets or exceeds this size",
    )
    prune_parser.add_argument(
        "--json",
        action="store_true",
        help="print the artifact retention report as JSON",
    )


def _add_backup_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    backup_parser = subparsers.add_parser(
        "backup",
        help="create, inspect, or restore workspace state backups",
        description=(
            "Create, inspect, or restore workspace-local Glassbox backups. "
            "Backups include the canonical SQLite database and event-referenced "
            ".glassbox artifacts, not portable replay or eval baseline bundles."
        ),
    )
    backup_subparsers = backup_parser.add_subparsers(
        dest="backup_command",
        required=True,
    )

    create_parser = backup_subparsers.add_parser(
        "create",
        help="create a workspace backup archive",
        description=(
            "Create an inspectable zip archive containing the canonical SQLite "
            "database and event-referenced workspace artifacts."
        ),
    )
    create_parser.add_argument(
        "output",
        nargs="?",
        help="optional output path for the backup archive",
    )
    create_parser.add_argument(
        "--json",
        action="store_true",
        help="print the backup report as JSON",
    )
    _add_runtime_location_arguments(create_parser)

    inspect_parser = backup_subparsers.add_parser(
        "inspect",
        help="inspect a workspace backup archive",
        description=(
            "Inspect and validate a Glassbox workspace backup archive without "
            "restoring it."
        ),
    )
    inspect_parser.add_argument("archive", help="backup archive to inspect")
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        help="print the inspection report as JSON",
    )
    _add_runtime_location_arguments(inspect_parser)

    restore_parser = backup_subparsers.add_parser(
        "restore",
        help="restore a workspace backup archive",
        description=(
            "Restore a Glassbox workspace backup into the selected workspace. "
            "The archive manifest and file hashes are validated before writing."
        ),
    )
    restore_parser.add_argument("archive", help="backup archive to restore")
    restore_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing restored files in the target workspace",
    )
    restore_parser.add_argument(
        "--json",
        action="store_true",
        help="print the restore report as JSON",
    )
    _add_runtime_location_arguments(restore_parser)
