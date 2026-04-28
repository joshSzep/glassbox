"""Workspace-scoped persistent runtime owner helpers."""

import asyncio
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.error import URLError
from urllib.request import urlopen

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import ValidationError

from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.bootstrap_storage import resolve_runtime_storage_paths
from glassbox.web import WebServerConfig
from glassbox.web import build_web_server

_OWNER_FILENAME = "runtime-owner.json"
_STDOUT_LOG_FILENAME = "runtime-owner.stdout.log"
_STDERR_LOG_FILENAME = "runtime-owner.stderr.log"


@dataclass(frozen=True, slots=True)
class RuntimeOwnerPaths:
    """Workspace-local paths used by the persistent runtime owner."""

    workspace_root: Path
    database_path: Path
    metadata_path: Path
    stdout_log_path: Path
    stderr_log_path: Path


class RuntimeOwnerRecord(BaseModel):
    """Serialized metadata for the active persistent runtime owner."""

    model_config = ConfigDict(frozen=True)

    pid: int
    workspace_root: Path
    database_path: Path
    host: str
    port: int
    dashboard_url: str
    started_at: datetime


class RuntimeOwnerStatus(BaseModel):
    """Observed status for the workspace-scoped runtime owner."""

    model_config = ConfigDict(frozen=True)

    state: Literal["not_running", "stale", "running"]
    record: RuntimeOwnerRecord | None = None
    health: Literal["ok", "unreachable"] | None = None


def resolve_runtime_owner_paths(
    cwd: Path,
    *,
    db_path: Path | None = None,
) -> RuntimeOwnerPaths:
    """Resolve workspace-local metadata and log paths for the daemon owner."""

    storage_paths = resolve_runtime_storage_paths(cwd, db_path=db_path)
    runtime_dir = storage_paths.workspace_root / ".glassbox"
    return RuntimeOwnerPaths(
        workspace_root=storage_paths.workspace_root,
        database_path=storage_paths.database_path,
        metadata_path=runtime_dir / _OWNER_FILENAME,
        stdout_log_path=runtime_dir / _STDOUT_LOG_FILENAME,
        stderr_log_path=runtime_dir / _STDERR_LOG_FILENAME,
    )


def inspect_runtime_owner(
    cwd: Path,
    *,
    db_path: Path | None = None,
) -> RuntimeOwnerStatus:
    """Inspect the workspace runtime owner metadata and current health."""

    paths = resolve_runtime_owner_paths(cwd, db_path=db_path)
    return _inspect_runtime_owner_paths(paths)


def ensure_runtime_owner_absent(
    cwd: Path,
    *,
    db_path: Path | None = None,
    action_description: str,
) -> None:
    """Reject local mutating commands while a persistent owner is active."""

    status = inspect_runtime_owner(cwd, db_path=db_path)
    if status.state == "stale":
        clear_stale_runtime_owner(cwd, db_path=db_path)
        return
    if status.state != "running":
        return

    assert status.record is not None
    raise ValueError(
        f"cannot {action_description} while the workspace runtime is owned by "
        f"glassbox daemon (pid {status.record.pid}, {status.record.dashboard_url}); "
        "use `glassbox daemon stop` first"
    )


def clear_stale_runtime_owner(
    cwd: Path,
    *,
    db_path: Path | None = None,
) -> bool:
    """Remove stale owner metadata for a dead background runtime process."""

    paths = resolve_runtime_owner_paths(cwd, db_path=db_path)
    return _clear_stale_runtime_owner_paths(paths)


def start_runtime_owner(
    cwd: Path,
    *,
    host: str,
    port: int,
    db_path: Path | None = None,
    startup_timeout_seconds: float = 5.0,
) -> RuntimeOwnerRecord:
    """Spawn the persistent runtime owner and wait for a healthy startup."""

    paths = resolve_runtime_owner_paths(cwd, db_path=db_path)
    ensure_runtime_owner_absent(
        cwd,
        db_path=db_path,
        action_description="start a second daemon owner",
    )
    paths.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "glassbox",
        "daemon",
        "run-owner",
        "--cwd",
        str(paths.workspace_root),
        "--host",
        host,
        "--port",
        str(port),
    ]
    if db_path is not None:
        command.extend(["--db-path", str(paths.database_path)])

    with paths.stdout_log_path.open("ab") as stdout_handle:
        with paths.stderr_log_path.open("ab") as stderr_handle:
            process = subprocess.Popen(
                command,
                stdout=stdout_handle,
                stderr=stderr_handle,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )

    return _wait_for_healthy_runtime_owner(
        cwd,
        db_path=db_path,
        process=process,
        startup_timeout_seconds=startup_timeout_seconds,
    )


def stop_runtime_owner(
    cwd: Path,
    *,
    db_path: Path | None = None,
    shutdown_timeout_seconds: float = 5.0,
) -> RuntimeOwnerStatus:
    """Stop the active persistent runtime owner for a workspace."""

    paths = resolve_runtime_owner_paths(cwd, db_path=db_path)
    status = _inspect_runtime_owner_paths(paths)
    if status.state == "not_running":
        raise ValueError("no workspace daemon is running")
    if status.state == "stale":
        _clear_stale_runtime_owner_paths(paths)
        return status

    assert status.record is not None
    os.kill(status.record.pid, signal.SIGTERM)

    deadline = time.monotonic() + shutdown_timeout_seconds
    while time.monotonic() < deadline:
        if not paths.metadata_path.exists():
            return status
        if _clear_stale_runtime_owner_paths(paths):
            return status
        if not _process_is_alive(status.record.pid):
            _clear_stale_runtime_owner_paths(paths)
            return status
        time.sleep(0.05)

    raise ValueError(
        f"daemon pid {status.record.pid} did not shut down within "
        f"{shutdown_timeout_seconds:.1f}s"
    )


def run_runtime_owner(
    cwd: Path,
    *,
    host: str,
    port: int,
    db_path: Path | None = None,
) -> None:
    """Run the persistent runtime owner in the current process."""

    asyncio.run(
        _run_runtime_owner_async(
            cwd,
            host=host,
            port=port,
            db_path=db_path,
        )
    )


async def _run_runtime_owner_async(
    cwd: Path,
    *,
    host: str,
    port: int,
    db_path: Path | None,
) -> None:
    paths = resolve_runtime_owner_paths(cwd, db_path=db_path)
    record = _acquire_runtime_owner(paths, host=host, port=port)
    stop_event = asyncio.Event()
    try:
        _install_shutdown_handlers(stop_event)
        with open_runtime_context(
            paths.workspace_root,
            db_path=paths.database_path,
        ) as runtime_context:
            server = build_web_server(runtime_context, host=host, port=port)
            try:
                await server.start()
                await stop_event.wait()
            finally:
                await server.stop()
    finally:
        _release_runtime_owner(paths, pid=record.pid)


def _wait_for_healthy_runtime_owner(
    cwd: Path,
    *,
    db_path: Path | None,
    process: subprocess.Popen[bytes],
    startup_timeout_seconds: float,
) -> RuntimeOwnerRecord:
    paths = resolve_runtime_owner_paths(cwd, db_path=db_path)
    deadline = time.monotonic() + startup_timeout_seconds
    while time.monotonic() < deadline:
        status = _inspect_runtime_owner_paths(paths)
        if (
            status.state == "running"
            and status.record is not None
            and status.record.pid == process.pid
            and status.health == "ok"
        ):
            return status.record
        if process.poll() is not None:
            raise ValueError(_startup_failure_message(cwd, db_path=db_path))
        time.sleep(0.05)

    raise ValueError(_startup_failure_message(cwd, db_path=db_path))


def _startup_failure_message(cwd: Path, *, db_path: Path | None) -> str:
    paths = resolve_runtime_owner_paths(cwd, db_path=db_path)
    _clear_stale_runtime_owner_paths(paths)
    log_tail = _tail_text(paths.stderr_log_path)
    if log_tail:
        if _looks_like_port_conflict(log_tail):
            return (
                "daemon failed because the requested host/port appears unavailable; "
                f"see {paths.stderr_log_path}\n{log_tail}"
            )
        return (
            "daemon failed to reach a healthy startup state; "
            f"see {paths.stderr_log_path}\n{log_tail}"
        )
    return (
        f"daemon failed to reach a healthy startup state; see {paths.stderr_log_path}"
    )


def _acquire_runtime_owner(
    paths: RuntimeOwnerPaths,
    *,
    host: str,
    port: int,
) -> RuntimeOwnerRecord:
    paths.metadata_path.parent.mkdir(parents=True, exist_ok=True)
    record = RuntimeOwnerRecord(
        pid=os.getpid(),
        workspace_root=paths.workspace_root,
        database_path=paths.database_path,
        host=host,
        port=port,
        dashboard_url=WebServerConfig(host=host, port=port).dashboard_url,
        started_at=datetime.now(UTC),
    )

    while True:
        try:
            with paths.metadata_path.open("x", encoding="utf-8") as handle:
                handle.write(record.model_dump_json(indent=2))
                handle.write("\n")
            return record
        except FileExistsError as err:
            existing = _read_runtime_owner_record(paths.metadata_path)
            if existing is None or not _process_is_alive(existing.pid):
                paths.metadata_path.unlink(missing_ok=True)
                continue
            raise ValueError(
                f"workspace runtime already owned by glassbox daemon "
                f"(pid {existing.pid}, {existing.dashboard_url})"
            ) from err


def _release_runtime_owner(paths: RuntimeOwnerPaths, *, pid: int) -> None:
    record = _read_runtime_owner_record(paths.metadata_path)
    if record is None or record.pid != pid:
        return
    paths.metadata_path.unlink(missing_ok=True)


def _inspect_runtime_owner_paths(paths: RuntimeOwnerPaths) -> RuntimeOwnerStatus:
    record = _read_runtime_owner_record(paths.metadata_path)
    if record is None:
        return RuntimeOwnerStatus(state="not_running")
    if not _process_is_alive(record.pid):
        return RuntimeOwnerStatus(state="stale", record=record)
    return RuntimeOwnerStatus(
        state="running",
        record=record,
        health=_probe_healthz(record.dashboard_url),
    )


def _clear_stale_runtime_owner_paths(paths: RuntimeOwnerPaths) -> bool:
    status = _inspect_runtime_owner_paths(paths)
    if status.state != "stale":
        return False
    paths.metadata_path.unlink(missing_ok=True)
    return True


def _read_runtime_owner_record(path: Path) -> RuntimeOwnerRecord | None:
    if not path.exists():
        return None
    try:
        return RuntimeOwnerRecord.model_validate_json(path.read_text())
    except OSError, ValidationError:
        return None


def _process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _probe_healthz(dashboard_url: str) -> Literal["ok", "unreachable"]:
    health_url = dashboard_url.rstrip("/") + "/healthz"
    try:
        with urlopen(health_url, timeout=0.5) as response:  # noqa: S310
            body = response.read().decode("utf-8")
        return "ok" if '"status":"ok"' in body.replace(" ", "") else "unreachable"
    except OSError, URLError:
        return "unreachable"


def _install_shutdown_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, stop_event.set)
        except NotImplementedError:
            signal.signal(signum, lambda _sig, _frame: stop_event.set())


def _tail_text(path: Path, *, max_chars: int = 1200) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return content[-max_chars:].strip()


def _looks_like_port_conflict(log_tail: str) -> bool:
    normalized = log_tail.lower()
    return (
        "address already in use" in normalized
        or "error while attempting to bind" in normalized
        or "errno 48" in normalized
    )
