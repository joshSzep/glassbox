"""Tests for the v6 release gate script."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v6_release_gate.py"


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
        "frontend production build",
        "package build",
        "installed wheel smoke",
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
    ]

    for fragment in expected_fragments:
        assert fragment in script
    for test_path in expected_tests:
        assert test_path in script


def test_v6_release_gate_dry_run_lists_stages() -> None:
    result = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--dry-run"],
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
