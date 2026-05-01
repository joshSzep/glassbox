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
        "Tasks: "
        f"{report.tasks.active_count} active, "
        f"{report.tasks.blocked_count} blocked, "
        f"{report.tasks.failed_count} failed, "
        f"{report.tasks.budget_exhausted_count} budget exhausted, "
        f"{report.tasks.verification_failed_count} verification failure(s)"
    )
    print(
        "Background jobs: "
        f"{report.background_jobs.pending_count} pending, "
        f"{report.background_jobs.running_count} running, "
        f"{report.background_jobs.stale_count} stale, "
        f"{report.background_jobs.failed_count} failed, "
        f"{report.background_jobs.retryable_count} retryable, "
        f"{report.background_jobs.abandoned_count} abandoned"
    )
    if report.background_jobs.last_failure_job_id is not None:
        print(
            "Last job failure: "
            f"{report.background_jobs.last_failure_job_id} "
            f"({report.background_jobs.last_failure_message or 'no message'})"
        )
    print(
        "Workspace memory: "
        f"{report.memory.active_count} active, "
        f"{report.memory.stale_count} stale, "
        f"{report.memory.imported_count} imported, "
        f"{report.memory.invalidated_count} invalidated, "
        f"{report.memory.pruned_count} pruned, "
        f"{report.memory.redacted_count} redacted"
    )
    print(
        "Repository index: "
        f"{report.repository_index.status}, "
        f"{report.repository_index.entry_count} entries"
    )
    if report.repository_index.failure_reason is not None:
        print(f"Repository index failure: {report.repository_index.failure_reason}")
    print(
        "Branch searches: "
        f"{report.branch_searches.active_count} active, "
        f"{report.branch_searches.completed_count} completed, "
        f"{report.branch_searches.abandoned_count} abandoned, "
        f"{report.branch_searches.needs_review_count} needing review, "
        f"{report.branch_searches.failed_verification_count} failed verification"
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
    for line in _format_observability_safe_workflow_lines(report):
        print(line)
    if not report.next_actions:
        print("Next: no immediate action")
        return
    print("Next:")
    for action in report.next_actions:
        print(f"  - {action}")


def _format_observability_safe_workflow_lines(
    report: WorkspaceObservabilityReport,
) -> list[str]:
    lines = [
        "Safe workflow summary:",
        "  - Daemon: glassbox daemon status --cwd .",
        "  - Projections: glassbox projection check --all --cwd .",
        "  - Artifacts: glassbox artifacts inspect --cwd .",
        "  - Provider: glassbox provider diagnostics --cwd .",
        "  - Provider evidence: glassbox provider canary evidence --cwd .",
        "  - Repository index: glassbox repo index status --cwd .",
        "  - Backup before maintenance: glassbox backup create --cwd .",
    ]
    if report.repository_index.status in {"missing", "stale", "failed"}:
        lines.append(
            "  - Refresh index after status review: glassbox repo index build --cwd ."
        )
    if report.background_jobs.pending_count or report.background_jobs.failed_count:
        lines.append("  - Jobs: glassbox job list --cwd .")
    if report.tasks.latest_failed_task_id is not None:
        lines.append(
            "  - Failed task: "
            f"glassbox task show {report.tasks.latest_failed_task_id} --cwd ."
        )
    elif report.tasks.latest_blocked_task_id is not None:
        lines.append(
            "  - Blocked task: "
            f"glassbox task show {report.tasks.latest_blocked_task_id} --cwd ."
        )
    if report.branch_searches.latest_needs_review_search_id is not None:
        lines.append(
            "  - Branch-search review: "
            "glassbox branch-search show "
            f"{report.branch_searches.latest_needs_review_search_id} --cwd ."
        )
    return lines
