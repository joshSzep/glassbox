"""CLI command handlers for first-run readiness checks."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.next_action_output import next_action_record_payloads
from glassbox.cli.next_action_output import next_action_records_for_cli
from glassbox.cli.next_action_output import print_next_action_records
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import NextActionPriority
from glassbox.core import NextActionTargetKind
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
        payload = report.model_dump(mode="json")
        records = _readiness_next_action_records(report)
        payload["next_action_records"] = next_action_record_payloads(records)
        print_json_output(payload)
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
            print_next_action_records(
                _readiness_next_action_records(report, actions=check.next_actions),
                heading="  next action records:",
            )
    if report.maintenance_cues:
        print("Maintenance cues:")
        for cue in report.maintenance_cues[:6]:
            print(
                f"  - {cue.title}: {cue.priority.value}, "
                f"{cue.severity.value}; {cue.summary}"
            )


def _readiness_next_action_records(
    report: FirstRunReadinessReport,
    *,
    actions: list[str] | None = None,
):
    source_actions = actions or [
        action for check in report.checks for action in check.next_actions
    ]
    return next_action_records_for_cli(
        source_actions,
        target_kind=NextActionTargetKind.WORKSPACE,
        target_id=str(report.workspace_root),
        purpose="Resolve first-run readiness before starting local Glassbox work.",
        evidence_summary=(
            "Readiness checks inspect local workspace, database, and profile state."
        ),
        priority=NextActionPriority.ACTION_NEEDED
        if report.status == "blocked"
        else NextActionPriority.RECOMMENDED,
        limitations=["Readiness commands do not grant approval for later mutations."],
    )


__all__ = ["_readiness_command"]
