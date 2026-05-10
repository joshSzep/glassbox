"""Tests for the v6 release gate script."""

import subprocess
import sys
from pathlib import Path

from scripts.validate_v6_release_gate import build_gate_stages
from scripts.validate_v6_release_gate import build_installed_dashboard_smoke_command
from scripts.validate_v6_release_gate import build_installed_wheel_smoke_checks

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v6_release_gate.py"
GATE_DOC = REPO_ROOT / "docs" / "v6-release-gate.md"


def test_v6_release_gate_script_runs_expected_checks() -> None:
    script = GATE_SCRIPT.read_text(encoding="utf-8")

    expected_fragments = [
        "focused cancellation suite",
        "focused transport and daemon suite",
        "focused terminal and dashboard suite",
        "full python tests",
        "deterministic eval smoke",
        "frontend lint",
        "frontend typecheck",
        "frontend tests",
        "frontend API generation",
        "frontend generated API freshness",
        "frontend production build",
        "frontend static asset validation",
        "package build",
        "package contents validation",
        "installed wheel smoke",
        "installed terminal: root help",
        "installed terminal: version",
        "installed terminal: command guide",
        "installed autonomy: profile list",
        "installed task: list",
        "installed first-run: readiness check",
        "installed first-run: provider diagnostics",
        "installed first-run: profile example",
        "installed memory: list",
        "installed repository index: status",
        "installed repository intelligence: status",
        "installed repository intelligence: stale cues",
        "installed background jobs: list",
        "installed branch-search: list",
        "installed daemon: start",
        "installed dashboard: static routes",
        "installed eval: profile list",
        "installed eval: release profile show",
        "installed eval: deterministic smoke",
        "--evidence-dir",
        "summary.json",
        "--include-provider-canaries",
        "live-provider-canary",
        "--dry-run",
    ]
    expected_tests = [
        "tests/unit/test_model_loop.py",
        "tests/integration/test_turn_engine.py",
        "tests/unit/test_runtime_transport.py",
        "tests/integration/test_web_sse_events.py",
        "tests/integration/test_daemon_runtime.py",
        "tests/unit/test_cli_tui_workflows.py",
        "tests/integration/test_web_session_interaction.py",
        "tests/integration/test_web_spa_static.py",
        "tests/unit/test_packaging_metadata.py",
        "scripts/validate_frontend_release_assets.py",
        "frontend/generated/openapi.json",
        "frontend/generated/api-types.ts",
        "scripts/validate_package_contents.py",
    ]

    for fragment in expected_fragments:
        assert fragment in script
    for test_path in expected_tests:
        assert test_path in script


def test_v6_release_gate_dry_run_lists_stages(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    result = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--dry-run",
            "--evidence-dir",
            str(evidence_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "V6 release gate dry run" in result.stdout
    assert "python format" in result.stdout
    assert "focused cancellation suite" in result.stdout
    assert "advisory provider canaries: skipped by default" in result.stdout
    assert "installed wheel smoke" in result.stdout


def test_v6_release_gate_dry_run_writes_summary(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    result = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--dry-run",
            "--evidence-dir",
            str(evidence_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    summary_path = evidence_dir / "summary.json"
    assert summary_path.is_file()

    import json

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema_version"] == 1
    assert summary["gate"] == "v6-release"
    assert summary["status"] == "dry_run"
    assert summary["options"]["dry_run"] is True
    assert summary["artifacts"]["dist_dir"] == "dist"
    assert summary["stages"]
    assert summary["stages"][0]["status"] == "planned"
    assert summary["next_actions"] == ["rerun without --dry-run to execute the gate"]


def test_v6_release_gate_builds_installed_smoke_matrix(tmp_path: Path) -> None:
    wheel_path = Path("dist/glassbox-0.1.0-py3-none-any.whl")
    checks = build_installed_wheel_smoke_checks(
        wheel_path,
        tmp_path,
        daemon_port=9876,
    )

    labels = [check.label for check in checks]
    assert labels == [
        "installed terminal: root help",
        "installed terminal: version",
        "installed terminal: command tree",
        "installed terminal: command guide",
        "installed terminal: chat help",
        "installed terminal: attach help",
        "installed terminal: plain fallback",
        "installed autonomy: profile list",
        "installed task: list",
        "installed first-run: readiness check",
        "installed first-run: provider diagnostics",
        "installed first-run: profile example",
        "installed memory: list",
        "installed repository index: status",
        "installed repository intelligence: status",
        "installed repository intelligence: stale cues",
        "installed background jobs: list",
        "installed branch-search: list",
        "installed daemon: status before start",
        "installed daemon: start",
        "installed daemon: status after start",
        "installed daemon: stop",
        "installed eval: profile list",
        "installed eval: release profile show",
        "installed eval: deterministic smoke",
    ]
    expected_prefix = (
        "uv",
        "run",
        "--no-project",
        "--refresh",
        "--isolated",
        "--with",
        str(wheel_path),
    )
    assert all(check.command[:7] == expected_prefix for check in checks)
    assert checks[6].input_text == "/exit\n"
    assert checks[7].command[-3:] == (
        "--json",
        "--cwd",
        str(tmp_path / "autonomy"),
    )
    assert checks[8].command[-3:] == (
        "--json",
        "--cwd",
        str(tmp_path / "task"),
    )
    assert checks[9].command[-3:] == (
        "--json",
        "--cwd",
        str(tmp_path / "readiness"),
    )
    assert checks[10].command[-4:] == (
        "--cwd",
        str(tmp_path / "provider"),
        "--model-name",
        "openai:gpt-5.4",
    )
    assert checks[11].command[-2:] == ("--cwd", str(tmp_path / "profile"))
    assert checks[12].command[-3:] == (
        "--json",
        "--cwd",
        str(tmp_path / "memory"),
    )
    assert checks[13].command[-3:] == (
        "--json",
        "--cwd",
        str(tmp_path / "index"),
    )
    assert checks[14].command[-3:] == (
        "--json",
        "--cwd",
        str(tmp_path / "index"),
    )
    assert checks[15].command[-3:] == (
        "--json",
        "--cwd",
        str(tmp_path / "index"),
    )
    assert checks[16].command[-3:] == ("--json", "--cwd", str(tmp_path / "job"))
    assert checks[17].command[-3:] == (
        "--json",
        "--cwd",
        str(tmp_path / "branch-search"),
    )
    assert "9876" in checks[19].command


def test_v6_release_gate_builds_dashboard_smoke_command(tmp_path: Path) -> None:
    wheel_path = Path("dist/glassbox-0.1.0-py3-none-any.whl")

    command = build_installed_dashboard_smoke_command(
        wheel_path,
        tmp_path,
        port=9877,
    )

    assert command[:7] == (
        "uv",
        "run",
        "--no-project",
        "--refresh",
        "--isolated",
        "--with",
        str(wheel_path),
    )
    assert command[-6:] == (
        "--cwd",
        str(tmp_path),
        "--host",
        "127.0.0.1",
        "--port",
        "9877",
    )


def test_v6_release_gate_doc_maps_script_stages() -> None:
    doc = GATE_DOC.read_text(encoding="utf-8")

    for stage in build_gate_stages():
        assert f"`{stage.label}`" in doc

    for smoke_label in [
        "installed terminal: root help",
        "installed terminal: version",
        "installed terminal: command tree",
        "installed terminal: command guide",
        "installed terminal: chat help",
        "installed terminal: attach help",
        "installed terminal: plain fallback",
        "installed autonomy: profile list",
        "installed task: list",
        "installed first-run: readiness check",
        "installed first-run: provider diagnostics",
        "installed first-run: profile example",
        "installed memory: list",
        "installed repository index: status",
        "installed background jobs: list",
        "installed branch-search: list",
        "installed daemon: start",
        "installed dashboard: static routes",
        "installed eval: profile list",
        "installed eval: release profile show",
        "installed eval: deterministic smoke",
    ]:
        assert f"`{smoke_label}`" in doc

    for policy in [
        "Deterministic stage failure blocks",
        "Provider-canary skips do not block",
        "Provider-canary failures are advisory by default",
        "Manual accessibility or UX findings block",
    ]:
        assert policy in doc
