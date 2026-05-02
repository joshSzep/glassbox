"""CLI command handlers for task-plan inspection."""

import argparse
from datetime import UTC
from datetime import datetime
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.status_task import print_task_detail
from glassbox.cli.status_task import print_task_events
from glassbox.cli.status_task import print_task_summaries
from glassbox.core.events import EventEnvelope
from glassbox.core.types import BackgroundJobKind
from glassbox.core.types import PauseWindowPolicy
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.continuation_windows import active_continuation_window_job
from glassbox.runtime.continuation_windows import approve_continuation_window
from glassbox.runtime.pause_windows import cancel_pause_window
from glassbox.runtime.pause_windows import schedule_pause_window
from glassbox.runtime.task_queries import TaskPlanRepository
from glassbox.runtime.task_queries import TaskQueryService


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
        print_task_summaries(summaries)
    return 0


def _task_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        query_service = TaskQueryService(
            cast(TaskPlanRepository, runtime_context.repositories.sessions),
            workspace_root=cwd,
        )
        detail = query_service.get_task_detail(args.task_id)
        related_changesets = [
            changeset
            for changeset in ChangesetQueryService(
                cast(ChangesetRepository, runtime_context.repositories.sessions)
            ).list_changesets(session_id=detail.task.session_id)
            if changeset.task_id == detail.task.task_id
        ]

    if args.json:
        payload = detail.model_dump(mode="json")
        payload["related_changesets"] = [
            changeset.model_dump(mode="json") for changeset in related_changesets
        ]
        print_json_output(payload)
    else:
        print_task_detail(detail)
        if related_changesets:
            print("Related changesets:")
            for changeset in related_changesets:
                print(f"  {changeset.changeset_id}  {changeset.status}")
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
        print_task_events(events)
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


__all__ = ["_task_command"]
