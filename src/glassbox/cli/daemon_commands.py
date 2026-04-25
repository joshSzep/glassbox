"""CLI command handlers for the persistent workspace runtime owner."""

import argparse
import json
import shlex
from pathlib import Path

from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.daemon import clear_stale_runtime_owner
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.daemon import resolve_runtime_owner_paths
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
    paths = resolve_runtime_owner_paths(cwd, db_path=db_path)
    report = _runtime_owner_status_report(status, paths.workspace_root, db_path)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    for line in _render_runtime_owner_status(report):
        print(line)
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


def _runtime_owner_status_report(status, cwd: Path, db_path: Path | None) -> dict:
    paths = resolve_runtime_owner_paths(cwd, db_path=db_path)
    record = status.record
    dashboard_url = record.dashboard_url if record is not None else None
    report = {
        "state": status.state,
        "health": status.health,
        "workspace_root": str(paths.workspace_root),
        "database_path": str(paths.database_path),
        "metadata_path": str(paths.metadata_path),
        "stdout_log_path": str(paths.stdout_log_path),
        "stderr_log_path": str(paths.stderr_log_path),
        "pid": record.pid if record is not None else None,
        "host": record.host if record is not None else None,
        "port": record.port if record is not None else None,
        "dashboard_url": dashboard_url,
        "health_url": _health_url(dashboard_url),
        "session_index_url": dashboard_url,
        "started_at": record.started_at.isoformat() if record is not None else None,
        "commands": _runtime_owner_commands(paths.workspace_root, db_path),
    }
    return report


def _render_runtime_owner_status(report: dict) -> list[str]:
    lines = [
        f"Status: {_human_state(report['state'])}",
        f"Workspace: {report['workspace_root']}",
        f"Database: {report['database_path']}",
        f"Owner metadata: {report['metadata_path']}",
        f"Logs: {report['stdout_log_path']} / {report['stderr_log_path']}",
    ]

    if report["state"] == "not_running":
        lines.extend(
            [
                "Runtime owner: none",
                f"Start: {report['commands']['start']}",
            ]
        )
        return lines

    lines.extend(
        [
            f"Pid: {report['pid']}",
            f"Started: {report['started_at']}",
            f"Dashboard: {report['dashboard_url']}",
            f"Health URL: {report['health_url']}",
            f"Session index: {report['session_index_url']}",
        ]
    )
    if report["state"] == "running":
        lines.extend(
            [
                f"Health: {report['health']}",
                f"Attach: {report['commands']['attach']}",
                f"Stop: {report['commands']['stop']}",
            ]
        )
    elif report["state"] == "stale":
        lines.extend(
            [
                "Health: unavailable (owner process is not running)",
                f"Recover: {report['commands']['start']}",
                f"Clear stale owner: {report['commands']['stop']}",
            ]
        )
    return lines


def _runtime_owner_commands(cwd: Path, db_path: Path | None) -> dict[str, str]:
    location_args = ["--cwd", str(cwd)]
    if db_path is not None:
        location_args.extend(["--db-path", str(db_path)])
    quoted_location = " ".join(shlex.quote(value) for value in location_args)
    return {
        "start": f"glassbox daemon start {quoted_location}",
        "status": f"glassbox daemon status {quoted_location}",
        "status_json": f"glassbox daemon status {quoted_location} --json",
        "attach": f"glassbox attach SESSION_ID {quoted_location}",
        "stop": f"glassbox daemon stop {quoted_location}",
    }


def _health_url(dashboard_url: str | None) -> str | None:
    if dashboard_url is None:
        return None
    return dashboard_url.rstrip("/") + "/healthz"


def _human_state(state: str) -> str:
    return state.replace("_", " ")
