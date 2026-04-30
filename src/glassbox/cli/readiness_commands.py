"""CLI command handlers for first-run readiness checks."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.readiness import FirstRunReadinessReport
from glassbox.runtime.readiness import build_first_run_readiness_report


def _readiness_command(args: argparse.Namespace) -> int:
    readiness_command = getattr(args, "readiness_command", None)
    if readiness_command == "check":
        return _readiness_check_command(args)
    raise ValueError(f"unsupported readiness subcommand: {readiness_command}")


def _readiness_check_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    report = build_first_run_readiness_report(
        cwd,
        db_path=db_path,
        model_name=args.model_name,
    )
    if args.json:
        print_json_output(report.model_dump(mode="json"))
    else:
        _print_readiness_report(report)
    return 0 if report.status != "blocked" else 1


def _print_readiness_report(report: FirstRunReadinessReport) -> None:
    counts = report.summary_counts
    print(f"First-run readiness: {report.status}")
    print(f"Workspace: {report.workspace_root}")
    print(f"Database: {report.database_path}")
    print(
        "Checks: "
        f"{counts['pass']} pass, {counts['warning']} warning, {counts['fail']} fail"
    )
    for check in report.checks:
        print(f"[{check.status}] {check.title}: {check.detail}")
        if check.path is not None:
            print(f"  path: {check.path}")
        if check.next_actions:
            print("  next:")
            for action in check.next_actions:
                print(f"    - {action}")


__all__ = ["_readiness_command"]
