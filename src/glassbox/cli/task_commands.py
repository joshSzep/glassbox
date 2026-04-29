"""CLI command handlers for task-plan inspection."""

import argparse
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.types import BackgroundJobKind
from glassbox.runtime.bootstrap import open_runtime_context
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
    raise ValueError("specify a task subcommand")


def _task_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        query_service = TaskQueryService(
            cast(TaskPlanRepository, runtime_context.repositories.sessions)
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
            cast(TaskPlanRepository, runtime_context.repositories.sessions)
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
            cast(TaskPlanRepository, runtime_context.repositories.sessions)
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
        job = runtime_context.repositories.sessions.enqueue_background_job(
            task.session_id,
            kind=BackgroundJobKind.MUTATING_CONTINUATION,
            job_type="task-continuation-step",
            title=f"Continue task: {task.title}",
            requested_by=args.requested_by,
            payload={
                "task_id": str(task.task_id),
                "verify_repair": bool(args.verify_repair),
            },
            task_id=task.task_id,
        )

    if args.json:
        print_json_output(job.model_dump(mode="json"))
    else:
        print(f"Queued continuation job {job.job_id} for task {task.task_id}")
    return 0


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


def _print_task_events(events: list[TaskEventView]) -> None:
    if not events:
        print("No task events found")
        return
    print(f"Task events: {len(events)}")
    for event in events:
        print(f"{event.sequence}  {event.event_type}  {event.created_at.isoformat()}")


__all__ = ["_task_command"]
