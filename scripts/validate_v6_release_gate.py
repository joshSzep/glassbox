"""Run the v6 release-hardening gate."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
DEFAULT_EVIDENCE_ROOT = REPO_ROOT / ".glassbox" / "releases"

FOCUSED_CANCELLATION_TESTS = [
    "tests/unit/test_model_loop.py",
    "tests/integration/test_turn_engine.py",
    "tests/integration/test_command_tool.py",
    "tests/unit/test_subprocess_classification.py",
]

FOCUSED_TRANSPORT_DAEMON_TESTS = [
    "tests/unit/test_runtime_transport.py",
    "tests/integration/test_web_sse_events.py",
    "tests/integration/test_daemon_runtime.py",
    "tests/integration/test_cli_session_commands.py",
]

FOCUSED_TUI_DASHBOARD_TESTS = [
    "tests/unit/test_tui_framework_smoke.py",
    "tests/unit/test_cli_tui_conversation.py",
    "tests/unit/test_cli_tui_widgets.py",
    "tests/unit/test_cli_tui_app.py",
    "tests/unit/test_cli_tui_commands.py",
    "tests/unit/test_cli_tui_workflows.py",
    "tests/integration/test_cli_tui_launch_smoke.py",
    "tests/integration/test_cli_interactive_commands.py",
    "tests/integration/test_web_session_interaction.py",
    "tests/integration/test_web_spa_static.py",
    "tests/unit/test_packaging_metadata.py",
]


@dataclass(frozen=True, slots=True)
class GateStage:
    """One command stage in the v6 automated gate."""

    label: str
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InstalledSmokeCheck:
    """One installed-wheel smoke command."""

    label: str
    command: tuple[str, ...]
    input_text: str | None = None


def build_gate_stages() -> list[GateStage]:
    """Return the deterministic blocking stages for the v6 gate."""

    return [
        GateStage("python format", ("uv", "run", "ruff", "format", "--check", ".")),
        GateStage("python lint", ("uv", "run", "ruff", "check", ".")),
        GateStage("python typecheck", ("uv", "run", "ty", "check")),
        GateStage(
            "focused cancellation suite",
            ("uv", "run", "pytest", *FOCUSED_CANCELLATION_TESTS),
        ),
        GateStage(
            "focused transport and daemon suite",
            ("uv", "run", "pytest", *FOCUSED_TRANSPORT_DAEMON_TESTS),
        ),
        GateStage(
            "focused terminal and dashboard suite",
            ("uv", "run", "pytest", *FOCUSED_TUI_DASHBOARD_TESTS),
        ),
        GateStage("full python tests", ("uv", "run", "pytest")),
        GateStage("deterministic eval smoke", ("uv", "run", "glassbox", "eval", "run")),
        GateStage("frontend lint", ("pnpm", "--dir", "frontend", "lint")),
        GateStage("frontend typecheck", ("pnpm", "--dir", "frontend", "typecheck")),
        GateStage("frontend tests", ("pnpm", "--dir", "frontend", "test")),
        GateStage(
            "frontend API generation",
            ("pnpm", "--dir", "frontend", "api:generate"),
        ),
        GateStage(
            "frontend generated API freshness",
            (
                "git",
                "--no-pager",
                "diff",
                "--exit-code",
                "--",
                "frontend/generated/openapi.json",
                "frontend/generated/api-types.ts",
            ),
        ),
        GateStage("frontend production build", ("pnpm", "--dir", "frontend", "build")),
        GateStage(
            "frontend static asset validation",
            ("uv", "run", "python", "scripts/validate_frontend_release_assets.py"),
        ),
        GateStage("package build", ("uv", "build", "--wheel", "--sdist")),
        GateStage(
            "package contents validation",
            ("uv", "run", "python", "scripts/validate_package_contents.py"),
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Glassbox v6 release-hardening gate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the gate stages without executing them",
    )
    parser.add_argument(
        "--include-provider-canaries",
        action="store_true",
        help="run advisory live-provider canaries when credentials are available",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help=(
            "directory for the retained gate summary; defaults under .glassbox/releases"
        ),
    )
    args = parser.parse_args(argv)

    stages = build_gate_stages()
    evidence_dir = _resolve_evidence_dir(args.evidence_dir)
    summary = _new_evidence_summary(
        evidence_dir,
        include_provider_canaries=args.include_provider_canaries,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        _print_dry_run(stages, include_provider_canaries=args.include_provider_canaries)
        _record_planned_stages(summary, stages)
        _finish_summary(summary, "dry_run")
        _write_evidence_summary(evidence_dir, summary)
        return 0

    for stage in stages:
        exit_code = _run_stage(summary, stage)
        if exit_code != 0:
            _finish_summary(summary, "failed")
            _write_evidence_summary(evidence_dir, summary)
            return exit_code

    if args.include_provider_canaries:
        exit_code = _run_stage(
            summary,
            GateStage(
                "advisory provider canaries",
                (
                    "uv",
                    "run",
                    "glassbox",
                    "eval",
                    "run",
                    "--profile",
                    "live-provider-canary",
                ),
            ),
        )
        if exit_code != 0:
            print(
                "\nV6 release gate failed: advisory provider canaries",
                file=sys.stderr,
            )
            _finish_summary(summary, "failed")
            _write_evidence_summary(evidence_dir, summary)
            return exit_code
    else:
        print("\n==> advisory provider canaries")
        print("skipped; pass --include-provider-canaries to run when configured")
        _record_advisory_skip(
            summary,
            label="advisory provider canaries",
            reason="pass --include-provider-canaries to run when configured",
        )

    wheel_path = _latest_glassbox_wheel()
    if wheel_path is None:
        print("V6 release gate failed: built wheel not found", file=sys.stderr)
        _record_stage_result(
            summary,
            label="resolve built wheel",
            command=("find", "dist", "-name", "glassbox-*.whl"),
            status="failed",
            exit_code=1,
            started_at=_now_iso(),
            ended_at=_now_iso(),
        )
        _finish_summary(summary, "failed")
        _write_evidence_summary(evidence_dir, summary)
        return 1

    summary["artifacts"]["wheel_path"] = str(wheel_path.relative_to(REPO_ROOT))
    exit_code = _run_installed_wheel_smoke(summary, wheel_path)
    _finish_summary(summary, "passed" if exit_code == 0 else "failed")
    _write_evidence_summary(evidence_dir, summary)
    return exit_code


def _print_dry_run(
    stages: Sequence[GateStage],
    *,
    include_provider_canaries: bool,
) -> None:
    print("V6 release gate dry run")
    for stage in stages:
        print(f"- {stage.label}: {_format_command(stage.command)}")
    if include_provider_canaries:
        print(
            "- advisory provider canaries: "
            "uv run glassbox eval run --profile live-provider-canary"
        )
    else:
        print("- advisory provider canaries: skipped by default")
    print("- installed wheel smoke: latest dist/glassbox-*.whl")


def _run(label: str, command: Sequence[str], *, input_text: str | None = None) -> int:
    print(f"\n==> {label}")
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=input_text,
        text=input_text is not None,
        check=False,
    )
    if result.returncode != 0:
        print(f"\nV6 release gate failed: {label}", file=sys.stderr)
    return result.returncode


def _run_stage(summary: dict[str, Any], stage: GateStage) -> int:
    started_at = _now_iso()
    exit_code = _run(stage.label, stage.command)
    ended_at = _now_iso()
    _record_stage_result(
        summary,
        label=stage.label,
        command=stage.command,
        status="passed" if exit_code == 0 else "failed",
        exit_code=exit_code,
        started_at=started_at,
        ended_at=ended_at,
    )
    return exit_code


def _latest_glassbox_wheel() -> Path | None:
    wheels = sorted(
        DIST_DIR.glob("glassbox-*.whl"),
        key=lambda path: path.stat().st_mtime,
    )
    if not wheels:
        return None
    return wheels[-1]


def _run_installed_wheel_smoke(summary: dict[str, Any], wheel_path: Path) -> int:
    print(f"\n==> installed wheel smoke ({wheel_path.name})")
    with tempfile.TemporaryDirectory(prefix="glassbox-v6-gate-") as temp_dir:
        smoke_root = Path(temp_dir)
        _prepare_eval_smoke_workspace(smoke_root / "eval")
        _prepare_profile_smoke_workspace(smoke_root / "profile")
        _prepare_empty_smoke_workspace(smoke_root / "readiness")
        _prepare_handoff_smoke_workspace(smoke_root / "handoff")

        smoke_checks = build_installed_wheel_smoke_checks(wheel_path, smoke_root)
        daemon_stop_check = next(
            check for check in smoke_checks if check.label == "installed daemon: stop"
        )
        daemon_started = False
        for check in smoke_checks:
            exit_code = _run_installed_smoke_check(summary, check)
            if check.label == "installed daemon: start" and exit_code == 0:
                daemon_started = True
            if check.label == "installed daemon: stop" and exit_code == 0:
                daemon_started = False
            if exit_code != 0:
                if daemon_started and check.label != "installed daemon: stop":
                    _run_installed_smoke_check(summary, daemon_stop_check)
                return exit_code

        exit_code = _run_installed_dashboard_static_smoke(
            summary,
            wheel_path,
            smoke_root / "dashboard",
        )
        if exit_code != 0:
            return exit_code
    print("\nInstalled wheel smoke passed.")
    return 0


def build_installed_wheel_smoke_checks(
    wheel_path: Path,
    smoke_root: Path,
    *,
    daemon_port: int | None = None,
) -> list[InstalledSmokeCheck]:
    """Return installed-wheel smoke commands for isolated workspaces."""

    terminal_workspace = smoke_root / "terminal"
    autonomy_workspace = smoke_root / "autonomy"
    task_workspace = smoke_root / "task"
    readiness_workspace = smoke_root / "readiness"
    provider_workspace = smoke_root / "provider"
    profile_workspace = smoke_root / "profile"
    memory_workspace = smoke_root / "memory"
    index_workspace = smoke_root / "index"
    queue_workspace = smoke_root / "queue"
    changeset_workspace = smoke_root / "changeset"
    job_workspace = smoke_root / "job"
    branch_search_workspace = smoke_root / "branch-search"
    daemon_workspace = smoke_root / "daemon"
    eval_workspace = smoke_root / "eval"
    handoff_workspace = smoke_root / "handoff"
    handoff_package_path = handoff_workspace / "handoff.json"
    daemon_host = "127.0.0.1"
    daemon_port_text = str(daemon_port if daemon_port is not None else 8766)
    return [
        InstalledSmokeCheck(
            "installed terminal: root help",
            _installed_glassbox_command(wheel_path, "--help"),
        ),
        InstalledSmokeCheck(
            "installed terminal: version",
            _installed_glassbox_command(wheel_path, "--version"),
        ),
        InstalledSmokeCheck(
            "installed terminal: command tree",
            _installed_glassbox_command(wheel_path, "command", "tree"),
        ),
        InstalledSmokeCheck(
            "installed terminal: command guide",
            _installed_glassbox_command(wheel_path, "command", "guide", "--json"),
        ),
        InstalledSmokeCheck(
            "installed terminal: chat help",
            _installed_glassbox_command(wheel_path, "session", "chat", "--help"),
        ),
        InstalledSmokeCheck(
            "installed terminal: attach help",
            _installed_glassbox_command(wheel_path, "session", "attach", "--help"),
        ),
        InstalledSmokeCheck(
            "installed terminal: plain fallback",
            _installed_glassbox_command(
                wheel_path,
                "session",
                "chat",
                "--plain",
                "--no-dashboard",
                "--cwd",
                str(terminal_workspace),
            ),
            input_text="/exit\n",
        ),
        InstalledSmokeCheck(
            "installed autonomy: profile list",
            _installed_glassbox_command(
                wheel_path,
                "autonomy",
                "profile",
                "list",
                "--json",
                "--cwd",
                str(autonomy_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed task: list",
            _installed_glassbox_command(
                wheel_path,
                "task",
                "list",
                "--json",
                "--cwd",
                str(task_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed first-run: readiness check",
            _installed_glassbox_command(
                wheel_path,
                "readiness",
                "check",
                "--json",
                "--cwd",
                str(readiness_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed first-run: provider diagnostics",
            _installed_glassbox_command(
                wheel_path,
                "provider",
                "diagnostics",
                "--cwd",
                str(provider_workspace),
                "--model-name",
                "openai:gpt-5.4",
            ),
        ),
        InstalledSmokeCheck(
            "installed first-run: profile example",
            _installed_glassbox_command(
                wheel_path,
                "provider",
                "diagnostics",
                "--cwd",
                str(profile_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed memory: list",
            _installed_glassbox_command(
                wheel_path,
                "memory",
                "list",
                "--json",
                "--cwd",
                str(memory_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed repository index: status",
            _installed_glassbox_command(
                wheel_path,
                "repo",
                "index",
                "status",
                "--json",
                "--cwd",
                str(index_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed repository intelligence: status",
            _installed_glassbox_command(
                wheel_path,
                "repo",
                "status",
                "--json",
                "--cwd",
                str(index_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed repository intelligence: stale cues",
            _installed_glassbox_command(
                wheel_path,
                "repo",
                "stale",
                "--json",
                "--cwd",
                str(index_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed operator queue: list",
            _installed_glassbox_command(
                wheel_path,
                "queue",
                "list",
                "--json",
                "--cwd",
                str(queue_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed changeset: verification plan help",
            _installed_glassbox_command(
                wheel_path,
                "changeset",
                "verification-plan",
                "--help",
            ),
        ),
        InstalledSmokeCheck(
            "installed changeset: evidence graph help",
            _installed_glassbox_command(
                wheel_path,
                "changeset",
                "evidence-graph",
                "--help",
            ),
        ),
        InstalledSmokeCheck(
            "installed session: evidence graph help",
            _installed_glassbox_command(
                wheel_path,
                "session",
                "evidence-graph",
                "--help",
                "--cwd",
                str(changeset_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed background jobs: list",
            _installed_glassbox_command(
                wheel_path,
                "job",
                "list",
                "--json",
                "--cwd",
                str(job_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed branch-search: list",
            _installed_glassbox_command(
                wheel_path,
                "branch-search",
                "list",
                "--json",
                "--cwd",
                str(branch_search_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed handoff: command help",
            _installed_glassbox_command(wheel_path, "handoff", "--help"),
        ),
        InstalledSmokeCheck(
            "installed handoff: inspect help",
            _installed_glassbox_command(wheel_path, "handoff", "inspect", "--help"),
        ),
        InstalledSmokeCheck(
            "installed handoff: package compatibility",
            _installed_glassbox_command(
                wheel_path,
                "handoff",
                "inspect",
                str(handoff_package_path),
                "--json",
                "--cwd",
                str(handoff_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed handoff: readiness help",
            _installed_glassbox_command(
                wheel_path,
                "session",
                "handoff-readiness",
                "--help",
            ),
        ),
        InstalledSmokeCheck(
            "installed daemon: status before start",
            _installed_glassbox_command(
                wheel_path,
                "daemon",
                "status",
                "--json",
                "--cwd",
                str(daemon_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed daemon: start",
            _installed_glassbox_command(
                wheel_path,
                "daemon",
                "start",
                "--host",
                daemon_host,
                "--port",
                daemon_port_text,
                "--cwd",
                str(daemon_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed daemon: status after start",
            _installed_glassbox_command(
                wheel_path,
                "daemon",
                "status",
                "--json",
                "--cwd",
                str(daemon_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed daemon: stop",
            _installed_glassbox_command(
                wheel_path,
                "daemon",
                "stop",
                "--cwd",
                str(daemon_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed eval: profile list",
            _installed_glassbox_command(
                wheel_path,
                "eval",
                "profile",
                "list",
                "--cwd",
                str(eval_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed eval: release profile show",
            _installed_glassbox_command(
                wheel_path,
                "eval",
                "profile",
                "show",
                "release-candidate",
                "--json",
                "--cwd",
                str(eval_workspace),
            ),
        ),
        InstalledSmokeCheck(
            "installed eval: deterministic smoke",
            _installed_glassbox_command(
                wheel_path,
                "eval",
                "run",
                "smoke.hello",
                "--cwd",
                str(eval_workspace),
            ),
        ),
    ]


def build_installed_dashboard_smoke_command(
    wheel_path: Path,
    workspace: Path,
    *,
    port: int,
) -> tuple[str, ...]:
    """Return the long-running dashboard command used by installed smoke."""

    return _installed_glassbox_command(
        wheel_path,
        "dashboard",
        "serve",
        "--cwd",
        str(workspace),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    )


def _installed_glassbox_command(wheel_path: Path, *args: str) -> tuple[str, ...]:
    return (
        "uv",
        "run",
        "--no-project",
        "--refresh",
        "--isolated",
        "--with",
        str(wheel_path),
        "glassbox",
        *args,
    )


def _run_installed_smoke_check(
    summary: dict[str, Any],
    check: InstalledSmokeCheck,
) -> int:
    started_at = _now_iso()
    exit_code = _run(check.label, check.command, input_text=check.input_text)
    ended_at = _now_iso()
    _record_stage_result(
        summary,
        label=check.label,
        command=check.command,
        status="passed" if exit_code == 0 else "failed",
        exit_code=exit_code,
        started_at=started_at,
        ended_at=ended_at,
    )
    return exit_code


def _run_installed_dashboard_static_smoke(
    summary: dict[str, Any],
    wheel_path: Path,
    workspace: Path,
) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    port = _allocate_local_port()
    command = build_installed_dashboard_smoke_command(
        wheel_path,
        workspace,
        port=port,
    )
    label = "installed dashboard: static routes"
    started_at = _now_iso()
    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    exit_code = 1
    try:
        base_url = f"http://127.0.0.1:{port}"
        index_html = _wait_for_http_text(f"{base_url}/")
        app_html = _http_text(f"{base_url}/app")
        asset_path = _first_static_asset_path(app_html or index_html)
        _http_bytes(f"{base_url}{asset_path}")
        exit_code = 0
    except (TimeoutError, URLError, ValueError) as exc:
        print(f"\nV6 release gate failed: {label}: {exc}", file=sys.stderr)
    finally:
        _terminate_process(process)
        ended_at = _now_iso()
        _record_stage_result(
            summary,
            label=label,
            command=command,
            status="passed" if exit_code == 0 else "failed",
            exit_code=exit_code,
            started_at=started_at,
            ended_at=ended_at,
        )
    return exit_code


def _prepare_eval_smoke_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO_ROOT / "evals", workspace / "evals")


def _prepare_profile_smoke_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "glassbox.profile.json").write_text(
        json.dumps(
            {
                "profile_version": 1,
                "runtime": {
                    "model_name": "local-test-model",
                    "approval_mode": "never",
                },
                "verification": {"eval_profile": "commit-smoke"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _prepare_handoff_smoke_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    package = {
        "export_kind": "glassbox_session_export",
        "export_version": 1,
        "metadata": {"session_id": "installed-smoke-session"},
        "handoff": {"next_action_summary": "Inspect only."},
        "transcript": [],
    }
    (workspace / "handoff.json").write_text(
        json.dumps(package, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _prepare_empty_smoke_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)


def _allocate_local_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http_text(url: str, *, timeout_seconds: float = 15.0) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return _http_text(url)
        except URLError as exc:
            last_error = exc
            time.sleep(0.1)
    raise TimeoutError(f"timed out waiting for {url}: {last_error}")


def _http_text(url: str) -> str:
    return _http_bytes(url).decode("utf-8", errors="replace")


def _http_bytes(url: str) -> bytes:
    with urlopen(url, timeout=5.0) as response:
        if response.status != 200:
            raise ValueError(f"{url} returned HTTP {response.status}")
        return response.read()


def _first_static_asset_path(html: str) -> str:
    match = re.search(r'(?:src|href)="(/app/_next/[^"]+)"', html)
    if match is None:
        raise ValueError("dashboard shell did not reference an /app/_next asset")
    return match.group(1)


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        process.communicate(timeout=1)
        return
    process.terminate()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=5)


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)


def _resolve_evidence_dir(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_EVIDENCE_ROOT / f"{timestamp}-v6-gate"


def _new_evidence_summary(
    evidence_dir: Path,
    *,
    include_provider_canaries: bool,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "gate": "v6-release",
        "status": "dry_run" if dry_run else "running",
        "started_at": _now_iso(),
        "ended_at": None,
        "evidence_dir": str(evidence_dir),
        "command": list(sys.argv),
        "environment": {
            "cwd": str(REPO_ROOT),
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        },
        "options": {
            "include_provider_canaries": include_provider_canaries,
            "dry_run": dry_run,
        },
        "stages": [],
        "advisory": [],
        "artifacts": {
            "dist_dir": str(DIST_DIR.relative_to(REPO_ROOT)),
            "eval_summary_hint": ".glassbox/evals/",
            "manual_evidence_hint": "docs/v6-release-evidence.md",
        },
        "next_actions": [],
    }


def _record_planned_stages(
    summary: dict[str, Any],
    stages: Sequence[GateStage],
) -> None:
    for stage in stages:
        _record_stage_result(
            summary,
            label=stage.label,
            command=stage.command,
            status="planned",
            exit_code=None,
            started_at=None,
            ended_at=None,
        )


def _record_stage_result(
    summary: dict[str, Any],
    *,
    label: str,
    command: Sequence[str],
    status: str,
    exit_code: int | None,
    started_at: str | None,
    ended_at: str | None,
) -> None:
    summary["stages"].append(
        {
            "label": label,
            "command": list(command),
            "status": status,
            "exit_code": exit_code,
            "started_at": started_at,
            "ended_at": ended_at,
        }
    )


def _record_advisory_skip(
    summary: dict[str, Any],
    *,
    label: str,
    reason: str,
) -> None:
    summary["advisory"].append(
        {
            "label": label,
            "status": "skipped",
            "reason": reason,
        }
    )


def _finish_summary(summary: dict[str, Any], status: str) -> None:
    summary["status"] = status
    summary["ended_at"] = _now_iso()
    if status == "failed":
        summary["next_actions"].append("inspect failed stage output above")
    elif status == "dry_run":
        summary["next_actions"].append("rerun without --dry-run to execute the gate")
    elif status == "passed":
        summary["next_actions"].append(
            "attach manual release evidence before RC signoff"
        )


def _write_evidence_summary(evidence_dir: Path, summary: dict[str, Any]) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nV6 release evidence written to {summary_path}")
    return summary_path


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
