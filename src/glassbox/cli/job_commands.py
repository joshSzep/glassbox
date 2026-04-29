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


def _print_job_detail(job: BackgroundJobRecord) -> None:
    print(f"Job: {job.job_id}")
    print(f"Session: {job.session_id}")
    print(f"State: {job.state.value}")
    print(f"Kind: {job.kind.value}")
    print(f"Type: {job.job_type}")
    print(f"Title: {job.title}")
    print(f"Requested by: {job.requested_by}")
    print(f"Priority: {job.priority}")
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
    print(f"Updated: {job.updated_at.isoformat()}")


__all__ = ["_job_command"]
