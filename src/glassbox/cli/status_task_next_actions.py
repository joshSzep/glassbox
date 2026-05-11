"""Typed next-action records for task status output."""

from glassbox.cli.next_action_output import next_action_record_payloads
from glassbox.cli.next_action_output import next_action_records_for_cli
from glassbox.core import NextActionPriority
from glassbox.core import NextActionTargetKind
from glassbox.runtime.task_queries import TaskDetailView


def task_next_action_records(detail: TaskDetailView):
    task = detail.task
    commands = [
        f"glassbox task show {task.task_id} --cwd .",
        f"glassbox session status {task.session_id} --cwd .",
        "glassbox eval recommend PATH --cwd .",
    ]
    if detail.verification_summary.failed_count:
        commands.append(f"glassbox task events {task.task_id} --cwd .")
    return next_action_records_for_cli(
        commands,
        target_kind=NextActionTargetKind.TASK,
        target_id=str(task.task_id),
        purpose="Inspect task, session, and verification posture before continuing.",
        evidence_summary=(
            "Task detail is derived from local task and verification events."
        ),
        priority=NextActionPriority.ACTION_NEEDED
        if task.blocked_reason is not None or detail.verification_summary.failed_count
        else NextActionPriority.RECOMMENDED,
        limitations=["Continuation commands are not run by status rendering."],
    )


def task_next_action_record_payloads(detail: TaskDetailView) -> list[dict]:
    return next_action_record_payloads(task_next_action_records(detail))


__all__ = ["task_next_action_record_payloads", "task_next_action_records"]
