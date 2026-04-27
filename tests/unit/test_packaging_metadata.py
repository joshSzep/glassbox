"""Packaging metadata tests for installed Glassbox distributions."""

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_project_metadata_includes_terminal_runtime_dependencies() -> None:
    project = _pyproject()["project"]

    assert project["scripts"]["glassbox"] == "glassbox.cli:main"
    assert "textual>=6,<7" in project["dependencies"]
    assert all(
        "node" not in dependency.lower() for dependency in project["dependencies"]
    )
    assert all(
        "pnpm" not in dependency.lower() for dependency in project["dependencies"]
    )


def test_build_targets_package_dashboard_static_assets() -> None:
    hatch_config = _pyproject()["tool"]["hatch"]["build"]["targets"]

    assert "src/glassbox/web/static_next/**" in hatch_config["wheel"]["artifacts"]
    assert "src/glassbox/web/static_next/**" in hatch_config["sdist"]["artifacts"]
    assert "src/glassbox" in hatch_config["wheel"]["packages"]
