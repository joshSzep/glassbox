"""CLI command handlers for workspace observability summaries."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.observability import WorkspaceObservabilityReport
from glassbox.runtime.observability import build_workspace_observability_report


def _observability_command(args: argparse.Namespace) -> int:
    observability_command = getattr(args, "observability_command", None)
    if observability_command == "status":
        return _observability_status_command(args)
    raise ValueError("specify an observability subcommand")


def _observability_status_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    runtime_status = inspect_runtime_owner(cwd, db_path=db_path)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        report = build_workspace_observability_report(
            workspace_root=cwd,
            runtime_status=runtime_status,
            session_repository=runtime_context.repositories.sessions,
            event_transport_stats=runtime_context.infrastructure.event_transport.stats(),
        )

    if args.json:
        print_json_output(report.model_dump(mode="json"))
    else:
        _print_observability_report(report)
    return 0


def _print_observability_report(report: WorkspaceObservabilityReport) -> None:
    print(f"Workspace: {report.workspace_root}")
    print(f"Runtime: {report.runtime.state} ({report.runtime.health or 'n/a'})")
    print(
        "Event transport: "
        f"{report.runtime.event_transport.state}, "
        f"{report.runtime.event_transport.subscriber_count} subscriber(s), "
        f"{report.runtime.event_transport.dropped_events} dropped event(s), "
        "queue peak "
        f"{report.runtime.event_transport.max_queue_depth}/"
        f"{report.runtime.event_transport.queue_capacity}"
    )
    print(f"Reconnect: {report.runtime.event_transport.reconnect_mode}")
    print(f"Reconnect hint: {report.runtime.event_transport.reconnect_hint}")
    print(
        "Projections: "
        f"{report.projections.ok_count} ok, "
        f"{report.projections.degraded_count} degraded, "
        f"max lag {report.projections.max_lag}, "
        f"max rebuild scope {report.projections.max_rebuild_event_count} event(s)"
    )
    print(
        "Artifacts: "
        f"{report.artifacts.protected_count} protected, "
        f"{report.artifacts.candidate_count} prune candidate(s), "
        f"{report.artifacts.reclaimable_bytes} reclaimable bytes, "
        f"{report.artifacts.glassbox_size_bytes} total .glassbox bytes"
    )
    if report.artifacts.storage_warning is not None:
        print(f"Artifact warning: {report.artifacts.storage_warning}")
    print(
        "Verification: "
        f"{report.verification.latest_suite_status or 'not run'} "
        f"({report.verification.summary_count} retained summary/summaries)"
    )
    if report.verification.latest_summary_path is not None:
        print(f"Latest eval summary: {report.verification.latest_summary_path}")
    print(
        "Provider canary: "
        f"{report.provider_canary.latest_status} "
        f"({report.provider_canary.summary_count} retained summary/summaries)"
    )
    if report.provider_canary.latest_summary_path is not None:
        print(f"Latest provider canary: {report.provider_canary.latest_summary_path}")
    if not report.next_actions:
        print("Next: no immediate action")
        return
    print("Next:")
    for action in report.next_actions:
        print(f"  - {action}")
