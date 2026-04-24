"""Run frontend unit tests through Node's built-in test runner."""

import shutil
import subprocess
from pathlib import Path


def test_dashboard_state_reducer_unit_tests() -> None:
    """The browser reducer and pane renderer tests should pass under Node."""

    node = shutil.which("node")
    assert node is not None, "node is required for frontend unit tests"

    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [
            node,
            "--test",
            "tests/frontend/test_approval_actions.js",
            "tests/frontend/test_interaction_actions.js",
            "tests/frontend/test_dashboard_state.js",
            "tests/frontend/test_dashboard_render.js",
            "tests/frontend/test_dashboard_app.js",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        "frontend unit tests failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
