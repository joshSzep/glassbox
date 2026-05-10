"""Tests for the standalone installed-wheel smoke script."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "validate_installed_wheel_smoke.py"


def test_installed_wheel_smoke_dry_run_lists_v11_version_surface(
    tmp_path: Path,
) -> None:
    wheel_path = tmp_path / "glassbox-0.10.0-py3-none-any.whl"
    wheel_path.write_bytes(b"placeholder")
    evidence_dir = tmp_path / "evidence"

    result = subprocess.run(
        [
            sys.executable,
            str(SMOKE_SCRIPT),
            "--dry-run",
            "--wheel",
            str(wheel_path),
            "--evidence-dir",
            str(evidence_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Installed wheel smoke dry run" in result.stdout
    assert "installed terminal: version" in result.stdout
    assert "installed terminal: command guide" in result.stdout
    assert "installed autonomy: profile list" in result.stdout
    assert "installed task: list" in result.stdout
    assert "installed first-run: readiness check" in result.stdout
    assert "installed first-run: provider diagnostics" in result.stdout
    assert "installed memory: list" in result.stdout
    assert "installed repository index: status" in result.stdout
    assert "installed repository intelligence: status" in result.stdout
    assert "installed repository intelligence: stale cues" in result.stdout
    assert "installed background jobs: list" in result.stdout
    assert "installed branch-search: list" in result.stdout
    assert "installed dashboard: static routes" in result.stdout
    assert "installed eval: release profile show" in result.stdout

    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["gate"] == "installed-wheel-smoke"
    assert summary["status"] == "dry_run"
    assert summary["artifacts"]["wheel_path"] == str(wheel_path.resolve())
    assert any(
        stage["label"] == "installed first-run: readiness check"
        for stage in summary["stages"]
    )
    assert any(
        stage["label"] == "installed repository intelligence: status"
        for stage in summary["stages"]
    )
