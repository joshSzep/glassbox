"""CLI command handlers for the persistent workspace runtime owner."""

import argparse

from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.daemon import clear_stale_runtime_owner
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.daemon import run_runtime_owner
from glassbox.runtime.daemon import start_runtime_owner
from glassbox.runtime.daemon import stop_runtime_owner


def _daemon_command(args: argparse.Namespace) -> int:
    daemon_command = getattr(args, "daemon_command", None)
    if daemon_command == "start":
        return _daemon_start_command(args)
    if daemon_command == "stop":
        return _daemon_stop_command(args)
    if daemon_command == "status":
        return _daemon_status_command(args)
    if daemon_command == "run-owner":
        return _daemon_run_owner_command(args)
    raise ValueError("unknown daemon subcommand")


def _daemon_start_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    recovered_stale_owner = clear_stale_runtime_owner(cwd, db_path=db_path)
    record = start_runtime_owner(
        cwd,
        host=args.host,
        port=args.port,
        db_path=db_path,
    )
    if recovered_stale_owner:
        print("Recovered stale workspace daemon owner metadata.")
    print(f"Daemon running at {record.dashboard_url}")
    print(f"Daemon pid: {record.pid}")
    return 0


def _daemon_stop_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    status = stop_runtime_owner(cwd, db_path=db_path)
    if status.state == "stale":
        print("Removed stale workspace daemon owner metadata.")
        return 0
    assert status.record is not None
    print(f"Stopped daemon pid {status.record.pid}")
    return 0


def _daemon_status_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    status = inspect_runtime_owner(cwd, db_path=db_path)
    if status.state == "not_running":
        print("Status: not running")
        return 0
    if status.state == "stale":
        assert status.record is not None
        print("Status: stale")
        print(f"Pid: {status.record.pid}")
        print(f"Dashboard: {status.record.dashboard_url}")
        return 0

    assert status.record is not None
    print("Status: running")
    print(f"Pid: {status.record.pid}")
    print(f"Dashboard: {status.record.dashboard_url}")
    print(f"Health: {status.health}")
    return 0


def _daemon_run_owner_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    run_runtime_owner(
        cwd,
        host=args.host,
        port=args.port,
        db_path=db_path,
    )
    return 0
