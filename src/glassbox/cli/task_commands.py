"""CLI command handlers for task-plan inspection."""

import argparse
from datetime import UTC
from datetime import datetime
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.events import EventEnvelope
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import PauseWindowPolicy
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.continuation_windows import active_continuation_window_job
from glassbox.runtime.continuation_windows import approve_continuation_window
from glassbox.runtime.pause_windows import cancel_pause_window
from glassbox.runtime.pause_windows import schedule_pause_window
from glassbox.runtime.task_queries import TaskDetailView
from glassbox.runtime.task_queries import TaskEventView
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.runtime.task_queries import TaskSummaryView


def _task_command(args: argparse.Namespace) -> int:
    task_command = getattr(args, "task_command", None)
    if task_command == "list":
        return _task_list_command(args)
    if task_command == "show":
        return _task_show_command(args)
    if task_command == "events":
        return _task_events_command(args)
    if task_command == "continue":
        return _task_continue_command(args)
    if task_command == "pause-window":
        return _task_pause_window_command(args)
    if task_command == "pause-window-cancel":
        return _task_pause_window_cancel_command(args)
    raise ValueError("specify a task subcommand")


def _task_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        query_service = TaskQueryService(
            cast(TaskPlanRepository, runtime_context.repositories.sessions),
            workspace_root=cwd,
        )
        summaries = query_service.list_task_summaries(
            session_id=args.session_id,
            limit=args.limit,
        )

    if args.json:
        print_json_output([summary.model_dump(mode="json") for summary in summaries])
    else:
        _print_task_summaries(summaries)
    return 0


def _task_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        query_service = TaskQueryService(
            cast(TaskPlanRepository, runtime_context.repositories.sessions),
            workspace_root=cwd,
        )
        detail = query_service.get_task_detail(args.task_id)

    if args.json:
        print_json_output(detail.model_dump(mode="json"))
    else:
        _print_task_detail(detail)
    return 0


def _task_events_command(args: argparse.Namespace) -> int:
    if args.after_sequence < 0:
        raise ValueError("--after must be zero or greater")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        query_service = TaskQueryService(
            cast(TaskPlanRepository, runtime_context.repositories.sessions),
            workspace_root=cwd,
        )
        events = query_service.list_task_events(
            args.task_id,
            after_sequence=args.after_sequence,
            limit=args.limit,
        )

    if args.json:
        print_json_output([event.model_dump(mode="json") for event in events])
    else:
        _print_task_events(events)
    return 0


def _task_continue_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(TaskPlanRepository, runtime_context.repositories.sessions)
        task = repository.get_task(args.task_id)
        if task is None:
            raise ValueError(f"unknown task_id: {args.task_id}")
        payload: dict[str, object] = {
            "task_id": str(task.task_id),
            "verify_repair": bool(args.verify_repair),
        }
        now = datetime.now(UTC)
        if args.continue_for_minutes is not None:
            active_window_job = active_continuation_window_job(
                runtime_context.repositories.sessions.list_background_jobs(),
                task_id=task.task_id,
                now=now,
            )
            if active_window_job is not None:
                raise ValueError(
                    "task already has an active bounded continuation window "
                    f"on job {active_window_job.job_id}"
                )
            approval = approve_continuation_window(
                task_id=task.task_id,
                minutes=args.continue_for_minutes,
                requested_by=args.requested_by,
                decided_by=args.requested_by,
                reason=None,
                checkpoint_id=args.checkpoint_id,
                now=now,
            )
            runtime_context.repositories.sessions.append_events(
                [
                    EventEnvelope(
                        session_id=task.session_id,
                        sequence=0,
                        payload=approval.requested_event,
                    ),
                    EventEnvelope(
                        session_id=task.session_id,
                        sequence=0,
                        payload=approval.resolved_event,
                    ),
                ]
            )
            payload.update(approval.payload)
        job = runtime_context.repositories.sessions.enqueue_background_job(
            task.session_id,
            kind=BackgroundJobKind.MUTATING_CONTINUATION,
            job_type="task-continuation-step",
            title=f"Continue task: {task.title}",
            requested_by=args.requested_by,
            payload=payload,
            task_id=task.task_id,
        )

    if args.json:
        print_json_output(job.model_dump(mode="json"))
    else:
        message = f"Queued continuation job {job.job_id} for task {task.task_id}"
        if args.continue_for_minutes is not None:
            message += f" for {args.continue_for_minutes} minutes"
        print(message)
    return 0


def _task_pause_window_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    policy = _pause_window_policy(args)
    pause_before = None
    if args.pause_before is not None:
        pause_before = datetime.fromisoformat(args.pause_before)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(TaskPlanRepository, runtime_context.repositories.sessions)
        task = repository.get_task(args.task_id)
        if task is None:
            raise ValueError(f"unknown task_id: {args.task_id}")
        event = schedule_pause_window(
            scope="task",
            task_id=task.task_id,
            policy=policy,
            scheduled_by=args.scheduled_by,
            reason=args.reason,
            checkpoint_id=args.checkpoint_id,
            pause_before=pause_before,
        )
        runtime_context.repositories.sessions.append_event(
            EventEnvelope(session_id=task.session_id, sequence=0, payload=event)
        )

    if args.json:
        print_json_output(event.model_dump(mode="json"))
    else:
        print(f"Scheduled pause window {event.pause_window_id} for task {args.task_id}")
    return 0


def _task_pause_window_cancel_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(TaskPlanRepository, runtime_context.repositories.sessions)
        task = repository.get_task(args.task_id)
        if task is None:
            raise ValueError(f"unknown task_id: {args.task_id}")
        event = cancel_pause_window(
            pause_window_id=args.pause_window_id,
            task_id=task.task_id,
            cancelled_by=args.cancelled_by,
            reason=args.reason,
        )
        runtime_context.repositories.sessions.append_event(
            EventEnvelope(session_id=task.session_id, sequence=0, payload=event)
        )

    if args.json:
        print_json_output(event.model_dump(mode="json"))
    else:
        print(f"Cancelled pause window {event.pause_window_id} for task {args.task_id}")
    return 0


def _pause_window_policy(args: argparse.Namespace) -> PauseWindowPolicy:
    if args.pause_before is not None:
        return PauseWindowPolicy.BEFORE_TIME
    if args.checkpoint_id is not None:
        return PauseWindowPolicy.AFTER_CHECKPOINT
    return PauseWindowPolicy.BEFORE_RISKY_ACTION


def _print_task_summaries(summaries: list[TaskSummaryView]) -> None:
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


def _print_task_detail(detail: TaskDetailView) -> None:
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


def _print_task_events(events: list[TaskEventView]) -> None:
    if not events:
        print("No task events found")
        return
    print(f"Task events: {len(events)}")
    for event in events:
        print(f"{event.sequence}  {event.event_type}  {event.created_at.isoformat()}")


__all__ = ["_task_command"]
