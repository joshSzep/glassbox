"""Task status formatting helpers for the CLI."""

from glassbox.cli.next_action_output import print_next_action_records
from glassbox.cli.status_task_next_actions import task_next_action_records
from glassbox.runtime.task_queries import TaskDetailView
from glassbox.runtime.task_queries import TaskEventView
from glassbox.runtime.task_queries import TaskSummaryView


def print_task_summaries(summaries: list[TaskSummaryView]) -> None:
    if not summaries:
        print("No tasks found")
        return
    print(f"Tasks: {len(summaries)}")
    for summary in summaries:
        print(
            f"{summary.task_id}  {summary.status}  "
            f"updated {summary.updated_at.isoformat()}"
        )
        print(f"  Session: {summary.session_id}")
        print(f"  Title: {summary.title}")
        print(f"  Next: {summary.next_action_summary}")


def print_task_detail(detail: TaskDetailView) -> None:
    task = detail.task
    print(f"Task {task.task_id}: {task.title}")
    print(f"Status: {task.status}")
    print(f"Session: {task.session_id}")
    print(f"Goal: {task.goal}")
    print(f"Next: {task.next_action_summary}")
    if task.blocked_reason is not None:
        print(f"Blocked: {task.blocked_reason}")
        if task.blocked_detail:
            print(f"Detail: {task.blocked_detail}")
    print(f"Steps: {len(detail.steps)}")
    for step in detail.steps:
        print(f"  {step.order}. {step.title} [{step.status}]")
        if step.blocked_reason is not None:
            print(f"     blocked: {step.blocked_reason}")
    print(f"Verifications: {len(detail.verifications)}")
    for verification in detail.verifications:
        print(
            f"  {verification.check_name} [{verification.status}] "
            f"{verification.verification_id}"
        )
        if verification.summary:
            print(f"     {verification.summary}")
    summary = detail.verification_summary
    print(f"Verification ledger: {summary.current_posture}")
    print(
        "  "
        f"{summary.passed_count} passed, "
        f"{summary.failed_count} failed, "
        f"{summary.running_count} running, "
        f"{summary.total_count} total"
    )
    if summary.latest_success_check_name is not None:
        print(
            "  Last successful check: "
            f"{summary.latest_success_check_name} "
            f"(sequence {summary.latest_success_sequence})"
        )
    if summary.latest_failed_check_name is not None:
        print(
            "  Latest failed check: "
            f"{summary.latest_failed_check_name} "
            f"(sequence {summary.latest_failed_sequence})"
        )
    if detail.last_known_good is None:
        print("Last known good: none")
    else:
        lkg = detail.last_known_good
        print(
            "Last known good: "
            f"{lkg.check_name} at sequence {lkg.sequence} "
            f"[{lkg.evidence_status}]"
        )
        if lkg.checkpoint_id is not None:
            print(
                "  Checkpoint: "
                f"{lkg.checkpoint_id} "
                f"(sequence {lkg.checkpoint_sequence})"
            )
        if lkg.changed_paths:
            print(f"  Covered paths: {', '.join(lkg.changed_paths[:5])}")
    repair = detail.repair_history
    print(f"Repair history: {repair.status}")
    print(
        "  "
        f"{repair.failure_count} failures, "
        f"{repair.retry_count} retries, "
        f"{repair.repaired_count} repaired"
    )
    if repair.latest_failure_summary is not None:
        print(f"  Latest failure: {repair.latest_failure_summary}")
    drift = detail.verification_drift
    print(f"Verification drift: {drift.posture}")
    print(f"  {drift.reason}")
    if drift.changed_paths:
        print(f"  Changed paths: {', '.join(drift.changed_paths[:5])}")
    if drift.stale_changed_paths:
        print(f"  Stale paths: {', '.join(drift.stale_changed_paths[:5])}")
    print_next_action_records(task_next_action_records(detail))
    for line in format_task_safe_workflow_lines(detail):
        print(line)


def format_task_safe_workflow_lines(detail: TaskDetailView) -> list[str]:
    task = detail.task
    task_id = task.task_id
    session_id = task.session_id
    lines = [
        "Safe workflow summary:",
        f"  - Session posture: glassbox session status {session_id} --cwd .",
        f"  - Task detail: glassbox task show {task_id} --cwd .",
        "  - Verification plan: glassbox eval recommend PATH --cwd .",
        "  - Verification audit: glassbox eval audit --cwd .",
        "  - Budget and recovery jobs: glassbox job list --cwd .",
        (
            "  - Mutating continuation after inspection: "
            f"glassbox task continue {task_id} --cwd ."
        ),
        (
            "  - Mutating pause before risky work: "
            f"glassbox task pause-window {task_id} --before-risky-action "
            "--reason REASON --cwd ."
        ),
    ]
    if detail.last_known_good is not None and detail.last_known_good.checkpoint_id:
        lines.append(
            f"  - Checkpoint source: glassbox session status {session_id} --cwd ."
        )
    if detail.verification_summary.failed_count:
        lines.append(
            f"  - Failed verification detail: glassbox task events {task_id} --cwd ."
        )
    return lines


def print_task_events(events: list[TaskEventView]) -> None:
    if not events:
        print("No task events found")
        return
    print(f"Task events: {len(events)}")
    for event in events:
        print(f"{event.sequence}  {event.event_type}  {event.created_at.isoformat()}")


__all__ = [
    "format_task_safe_workflow_lines",
    "print_task_detail",
    "print_task_events",
    "print_task_summaries",
    "task_next_action_records",
]
