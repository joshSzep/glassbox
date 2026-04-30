"""CLI command handlers for background job inspection."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.types import BackgroundJobState
from glassbox.runtime.bootstrap import open_runtime_context


def _job_command(args: argparse.Namespace) -> int:
    job_command = getattr(args, "job_command", None)
    if job_command == "list":
        return _job_list_command(args)
    if job_command == "show":
        return _job_show_command(args)
    if job_command == "cancel":
        return _job_cancel_command(args)
    if job_command == "retry":
        return _job_retry_command(args)
    if job_command == "abandon":
        return _job_abandon_command(args)
    raise ValueError(f"unsupported job subcommand: {job_command}")


def _job_list_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    state = _optional_state(getattr(args, "state", None))
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        jobs = runtime_context.repositories.sessions.list_background_jobs(
            state=state,
            limit=args.limit,
        )
    if args.json:
        print_json_output([job.model_dump(mode="json") for job in jobs])
    else:
        _print_job_list(jobs)
    return 0


def _job_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        job = runtime_context.repositories.sessions.get_background_job(args.job_id)
    if job is None:
        raise ValueError(f"unknown background job: {args.job_id}")
    if args.json:
        print_json_output(job.model_dump(mode="json"))
    else:
        _print_job_detail(job)
    return 0


def _job_cancel_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        job = runtime_context.repositories.sessions.cancel_background_job(
            args.job_id,
            requested_by=args.requested_by,
            reason=args.reason,
        )
    if args.json:
        print_json_output(job.model_dump(mode="json"))
    else:
        print(f"Cancellation requested for {job.job_id}: {job.state.value}")
    return 0


def _job_retry_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        job = runtime_context.repositories.sessions.retry_background_job(
            args.job_id,
            requested_by=args.requested_by,
            reason=args.reason,
            retry_budget=args.retry_budget,
        )
    if args.json:
        print_json_output(job.model_dump(mode="json"))
    else:
        print(f"Retry requested for {job.job_id}: {job.state.value}")
    return 0


def _job_abandon_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        job = runtime_context.repositories.sessions.abandon_background_job(
            args.job_id,
            abandoned_by=args.abandoned_by,
            reason=args.reason,
        )
    if args.json:
        print_json_output(job.model_dump(mode="json"))
    else:
        print(f"Abandoned {job.job_id}: {job.state.value}")
    return 0


def _optional_state(value: str | None) -> BackgroundJobState | None:
    if value is None:
        return None
    return BackgroundJobState(value)


def _print_job_list(jobs: list[BackgroundJobRecord]) -> None:
    if not jobs:
        print("No background jobs found.")
        return
    for job in jobs:
        print(f"{job.job_id}  {job.state.value:<22}  {job.kind.value:<22}  {job.title}")
        print(f"  State detail: {_job_state_detail(job)}")
        next_action = _job_next_actions(job)[0]
        print(f"  Next: {next_action}")


def _print_job_detail(job: BackgroundJobRecord) -> None:
    print(f"Job: {job.job_id}")
    print(f"Session: {job.session_id}")
    print(f"State: {job.state.value}")
    print(f"Kind: {job.kind.value}")
    print(f"Type: {job.job_type}")
    print(f"Title: {job.title}")
    print(f"Requested by: {job.requested_by}")
    print(f"Priority: {job.priority}")
    print(f"State detail: {_job_state_detail(job)}")
    if job.worker_id is not None:
        print(f"Worker: {job.worker_id}")
    if job.lease_expires_at is not None:
        print(f"Lease expires: {job.lease_expires_at.isoformat()}")
    if job.progress_message is not None:
        print(f"Progress: {job.progress_message}")
    if job.failure_message is not None:
        failure_kind = (
            job.failure_kind.value if job.failure_kind is not None else "unknown"
        )
        print(f"Failure: {failure_kind}: {job.failure_message}")
        print(f"Retryable: {'yes' if job.retryable else 'no'}")
    if job.failure_artifact_path is not None:
        print(f"Failure artifact: {job.failure_artifact_path}")
    if job.retry_requested_by is not None:
        print(f"Retry requested by: {job.retry_requested_by}")
    if job.retry_reason is not None:
        print(f"Retry reason: {job.retry_reason}")
    if job.retry_exhausted_reason is not None:
        print(f"Retry exhausted: {job.retry_exhausted_reason}")
    if job.abandoned_by is not None:
        print(f"Abandoned by: {job.abandoned_by}")
    if job.abandoned_reason is not None:
        print(f"Abandon reason: {job.abandoned_reason}")
    print(f"Updated: {job.updated_at.isoformat()}")
    next_actions = _job_next_actions(job)
    if next_actions:
        print("Next actions:")
        for action in next_actions:
            print(f"- {action}")


def _job_state_detail(job: BackgroundJobRecord) -> str:
    state = job.state
    if state == BackgroundJobState.QUEUED:
        return "Queued for daemon pickup; inspect daemon status if it does not start."
    if state == BackgroundJobState.CLAIMED:
        return "Claimed by a daemon worker; inspect lease and heartbeat before acting."
    if state == BackgroundJobState.RUNNING:
        return "Running under the daemon owner; inspect progress before cancelling."
    if state == BackgroundJobState.PAUSED:
        return "Paused background work; inspect before retrying or abandoning."
    if state == BackgroundJobState.CANCELLATION_REQUESTED:
        return "Cancellation requested; wait for daemon acknowledgement or inspect."
    if state == BackgroundJobState.CANCELLED:
        return "Cancelled terminal state; queue a new job if work is still needed."
    if state == BackgroundJobState.STALE:
        return "Worker lease expired; inspect before retrying or abandoning."
    if state == BackgroundJobState.FAILED:
        if job.retryable:
            return "Failed but retryable; inspect failure evidence before retrying."
        return "Failed and not retryable; inspect failure evidence before abandoning."
    if state == BackgroundJobState.ABANDONED:
        return "Abandoned terminal state; retained for history only."
    if state == BackgroundJobState.COMPLETED:
        return "Completed successfully; retained as background work evidence."
    return "Background job state is retained for inspection."


def _job_next_actions(job: BackgroundJobRecord) -> list[str]:
    show = f"glassbox job show {job.job_id}"
    if job.state == BackgroundJobState.QUEUED:
        return [show, "glassbox daemon status"]
    if job.state in {
        BackgroundJobState.CLAIMED,
        BackgroundJobState.PAUSED,
        BackgroundJobState.RUNNING,
    }:
        return [show, f"glassbox job cancel {job.job_id} --reason 'operator stop'"]
    if job.state == BackgroundJobState.CANCELLATION_REQUESTED:
        return [show, "glassbox daemon status"]
    if job.state == BackgroundJobState.STALE:
        return [
            show,
            f"glassbox job retry {job.job_id} --reason 'stale lease reviewed'",
            f"glassbox job abandon {job.job_id} --reason 'stale lease not needed'",
        ]
    if job.state == BackgroundJobState.FAILED:
        actions = [show]
        if job.retryable:
            actions.append(
                f"glassbox job retry {job.job_id} --reason 'failure reviewed'"
            )
        actions.append(f"glassbox job abandon {job.job_id} --reason 'failure reviewed'")
        return actions
    if job.state in {
        BackgroundJobState.CANCELLED,
        BackgroundJobState.ABANDONED,
        BackgroundJobState.COMPLETED,
    }:
        return [show]
    return [show]


__all__ = ["_job_command"]
