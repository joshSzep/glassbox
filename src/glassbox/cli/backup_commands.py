"""CLI command handlers for workspace backup and restore."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_optional_output_path
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.bootstrap_storage import default_database_path
from glassbox.store.workspace_backup import WorkspaceBackupInspectionReport
from glassbox.store.workspace_backup import WorkspaceBackupReport
from glassbox.store.workspace_backup import WorkspaceRestoreReport
from glassbox.store.workspace_backup import create_workspace_backup
from glassbox.store.workspace_backup import default_backup_path
from glassbox.store.workspace_backup import inspect_workspace_backup
from glassbox.store.workspace_backup import restore_workspace_backup


def _backup_command(args: argparse.Namespace) -> int:
    backup_command = getattr(args, "backup_command", None)
    if backup_command == "create":
        return _backup_create_command(args)
    if backup_command == "inspect":
        return _backup_inspect_command(args)
    if backup_command == "restore":
        return _backup_restore_command(args)
    raise ValueError("unknown backup subcommand")


def _backup_create_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="create a workspace backup locally",
    )
    database_path = db_path or default_database_path(cwd)
    output_path = (
        resolve_optional_output_path(cwd, args.output, default_name="unused")
        if args.output is not None
        else default_backup_path(cwd)
    )
    report = create_workspace_backup(
        cwd,
        database_path=database_path,
        output_path=output_path,
    )
    if args.json:
        print_json_output(report.to_json_payload())
        return 0
    _print_backup_report(report)
    return 0


def _backup_inspect_command(args: argparse.Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    del _db_path
    archive_path = resolve_optional_output_path(
        cwd,
        args.archive,
        default_name="unused",
    )
    report = inspect_workspace_backup(archive_path)
    if args.json:
        print_json_output(report.to_json_payload())
        return 0
    _print_backup_inspection_report(report)
    return 0


def _backup_restore_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="restore a workspace backup locally",
    )
    database_path = db_path or default_database_path(cwd)
    archive_path = resolve_optional_output_path(
        cwd,
        args.archive,
        default_name="unused",
    )
    report = restore_workspace_backup(
        archive_path,
        workspace_root=cwd,
        database_path=database_path,
        force=args.force,
    )
    if args.json:
        print_json_output(report.to_json_payload())
        return 0
    _print_restore_report(report)
    return 0


def _print_backup_report(report: WorkspaceBackupReport) -> None:
    print(f"Created workspace backup: {report.archive_path}")
    print(f"Workspace: {report.workspace_root}")
    print(f"Database: {report.database_path}")
    print(
        f"Included {report.session_count} session(s), "
        f"{report.artifact_count} artifact(s), "
        f"{len(report.files)} file(s), {report.total_size_bytes} bytes"
    )


def _print_backup_inspection_report(report: WorkspaceBackupInspectionReport) -> None:
    print(f"Inspected workspace backup: {report.archive_path}")
    print(f"Created: {report.created_at}")
    print(f"Source workspace: {report.source_workspace_root}")
    print(f"Source database: {report.source_database_path}")
    print(
        f"Contains {report.session_count} session(s), "
        f"{report.artifact_count} artifact(s), "
        f"{len(report.files)} file(s), {report.total_size_bytes} bytes"
    )


def _print_restore_report(report: WorkspaceRestoreReport) -> None:
    print(f"Restored workspace backup: {report.archive_path}")
    print(f"Workspace: {report.workspace_root}")
    print(f"Database: {report.database_path}")
    print(
        f"Restored {report.session_count} session(s), "
        f"{report.artifact_count} artifact(s), "
        f"{len(report.restored_files)} file(s)"
    )
