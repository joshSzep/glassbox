"""Tests for the v5 terminal release gate documentation and script."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_DOC = REPO_ROOT / "docs" / "v5-terminal-release-gate.md"
GATE_SCRIPT = REPO_ROOT / "scripts" / "validate_v5_terminal_release_gate.py"


def test_v5_terminal_release_gate_documents_required_requirements() -> None:
    gate = GATE_DOC.read_text(encoding="utf-8")

    required_sections = [
        "## Release Command",
        "## Release Checklist",
        "## Automated Coverage Map",
        "## Manual Validation",
        "## Known Non-Blocking Gaps",
        "## Plain Line-Mode Decision",
    ]
    required_requirements = [
        "Full-screen launch",
        "Co-hosted dashboard",
        "Transcript",
        "Streaming",
        "Composer",
        "Command palette",
        "Approvals",
        "Questions",
        "Tool activity",
        "Details pane",
        "Attach",
        "Reconnect",
        "Interruption and exit",
        "Fallback",
        "Packaging",
        "Docs",
    ]

    for section in required_sections:
        assert section in gate
    for requirement in required_requirements:
        assert requirement in gate
    assert "Plain line mode remains supported" in gate


def test_v5_terminal_release_gate_script_runs_expected_checks() -> None:
    script = GATE_SCRIPT.read_text(encoding="utf-8")

    expected_commands = [
        "ruff",
        "ty",
        "pytest",
        "glassbox",
        "eval",
        "build",
        "--wheel",
        "--sdist",
        "--isolated",
        "session",
        "chat",
        "attach",
        "--plain",
    ]
    expected_tests = [
        "tests/unit/test_cli_tui_workflows.py",
        "tests/unit/test_cli_tui_app.py",
        "tests/unit/test_cli_tui_widgets.py",
        "tests/integration/test_cli_tui_launch_smoke.py",
        "tests/integration/test_cli_interactive_commands.py",
        "tests/integration/test_daemon_runtime.py",
        "tests/unit/test_packaging_metadata.py",
    ]

    for command_fragment in expected_commands:
        assert command_fragment in script
    for test_path in expected_tests:
        assert test_path in script
