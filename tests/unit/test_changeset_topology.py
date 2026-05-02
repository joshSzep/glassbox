"""Tests for changeset topology impact summaries."""

from pathlib import Path

from glassbox.runtime.changeset_topology import derive_changeset_topology_impacts
from glassbox.runtime.workspace_topology import build_and_write_workspace_topology


def test_changeset_topology_impacts_name_components_tests_and_dependencies(
    tmp_path: Path,
) -> None:
    _write_workspace(tmp_path)
    build_and_write_workspace_topology(tmp_path)

    impacts, limitations = derive_changeset_topology_impacts(
        workspace_root=tmp_path,
        changed_paths=[
            "src/demo/widget.py",
            "frontend/components/console/widget.tsx",
        ],
    )

    assert limitations == []
    assert [impact.component_id for impact in impacts] == [
        "package:demo",
        "app:frontend",
    ]
    python_impact = impacts[0]
    assert python_impact.matched_paths == ["src/demo/widget.py"]
    assert python_impact.test_roots == ["tests"]
    assert python_impact.topology_freshness == "fresh"
    assert "runtime dependency: fastapi" in python_impact.dependency_hints

    frontend_impact = impacts[1]
    assert frontend_impact.matched_paths == ["frontend/components/console/widget.tsx"]
    assert frontend_impact.test_roots == ["frontend/tests"]
    assert frontend_impact.recommendation_posture == "fresh"
    assert "development dependency: vitest" in frontend_impact.dependency_hints


def test_changeset_topology_impacts_degrade_when_snapshot_is_stale(
    tmp_path: Path,
) -> None:
    _write_workspace(tmp_path)
    build_and_write_workspace_topology(tmp_path)
    (tmp_path / "src" / "demo" / "extra.py").write_text("VALUE = 1\n", encoding="utf-8")

    impacts, limitations = derive_changeset_topology_impacts(
        workspace_root=tmp_path,
        changed_paths=["src/demo/widget.py"],
    )

    assert "Workspace topology is stale" in limitations[0]
    assert impacts[0].recommendation_posture == "degraded"
    assert "Topology inputs changed" in impacts[0].limitations[-1]


def test_changeset_topology_impacts_are_optional_when_snapshot_is_missing(
    tmp_path: Path,
) -> None:
    impacts, limitations = derive_changeset_topology_impacts(
        workspace_root=tmp_path,
        changed_paths=["src/demo/widget.py"],
    )

    assert impacts == []
    assert limitations == []


def _write_workspace(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["fastapi>=0.115"]
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "src" / "demo").mkdir(parents=True)
    (tmp_path / "src" / "demo" / "widget.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_widget.py").write_text(
        "def test_widget() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package.json").write_text(
        """
{
  "name": "frontend",
  "devDependencies": {
    "vitest": "^3.0.0"
  }
}
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "frontend" / "pnpm-lock.yaml").write_text("", encoding="utf-8")
    (tmp_path / "frontend" / "components" / "console").mkdir(parents=True)
    (tmp_path / "frontend" / "components" / "console" / "widget.tsx").write_text(
        "export function Widget() { return null; }\n",
        encoding="utf-8",
    )
    (tmp_path / "frontend" / "tests").mkdir()
    (tmp_path / "frontend" / "tests" / "widget.test.ts").write_text(
        "test('widget', () => {});\n",
        encoding="utf-8",
    )
