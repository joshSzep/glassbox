"""Tests for typed workspace topology contracts."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from glassbox.runtime.workspace_topology import TopologyComponentKind
from glassbox.runtime.workspace_topology import TopologyManifestRef
from glassbox.runtime.workspace_topology import TopologyProvenance
from glassbox.runtime.workspace_topology import TopologyProvenanceSource
from glassbox.runtime.workspace_topology import WorkspaceTopologyComponent
from glassbox.runtime.workspace_topology import WorkspaceTopologyDependency
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot


def test_python_only_topology_snapshot_names_package_and_tests() -> None:
    snapshot = WorkspaceTopologySnapshot(
        workspace_root=Path("/repo"),
        freshness="fresh",
        built_at=_now(),
        source_digest="a" * 64,
        source_inputs=["pyproject.toml", "src/glassbox", "tests"],
        components=[
            WorkspaceTopologyComponent(
                component_id="package:glassbox",
                kind="package",
                name="glassbox",
                root_path=Path("."),
                language="python",
                ecosystem="python",
                package_manager="uv",
                manifests=[
                    TopologyManifestRef(
                        path=Path("pyproject.toml"),
                        kind="pyproject",
                        ecosystem="python",
                        package_manager="uv",
                        provenance=[_provenance("pyproject.toml", "manifest")],
                    ),
                ],
                lockfiles=[
                    TopologyManifestRef(
                        path=Path("uv.lock"),
                        kind="lockfile",
                        ecosystem="python",
                        package_manager="uv",
                        provenance=[_provenance("uv.lock", "lockfile")],
                    ),
                ],
                source_roots=[Path("src/glassbox")],
                test_roots=[Path("tests")],
                docs_roots=[Path("docs")],
                ownership_hints=["runtime maintainers"],
                provenance=[_provenance("pyproject.toml", "manifest")],
            ),
        ],
        dependencies=[
            WorkspaceTopologyDependency(
                dependency_id="dep:glassbox:pydantic",
                source_component_id="package:glassbox",
                kind="runtime",
                external_name="pydantic",
                version_constraint=">=2",
                manifest_path=Path("pyproject.toml"),
                provenance=[_provenance("pyproject.toml", "manifest")],
            ),
        ],
    )

    assert snapshot.recommendation_posture == "fresh"
    assert snapshot.component_ids_for_path("src/glassbox/runtime/changesets.py") == [
        "package:glassbox"
    ]
    assert snapshot.component_ids_for_path("tests/unit/test_workspace_topology.py") == [
        "package:glassbox"
    ]


def test_frontend_only_topology_snapshot_allows_generated_outputs() -> None:
    snapshot = WorkspaceTopologySnapshot(
        workspace_root=Path("/repo/frontend"),
        freshness="fresh",
        built_at=_now(),
        components=[
            WorkspaceTopologyComponent(
                component_id="app:dashboard",
                kind="app",
                name="dashboard",
                root_path=Path("."),
                language="typescript",
                ecosystem="node",
                package_manager="pnpm",
                manifests=[
                    TopologyManifestRef(
                        path=Path("package.json"),
                        kind="package_json",
                        ecosystem="node",
                        package_manager="pnpm",
                        provenance=[_provenance("package.json", "manifest")],
                    ),
                ],
                lockfiles=[
                    TopologyManifestRef(
                        path=Path("pnpm-lock.yaml"),
                        kind="lockfile",
                        ecosystem="node",
                        package_manager="pnpm",
                        provenance=[_provenance("pnpm-lock.yaml", "lockfile")],
                    ),
                ],
                source_roots=[Path("app"), Path("components"), Path("stores")],
                test_roots=[Path("tests"), Path("e2e")],
                generated_output_roots=[Path("generated"), Path("out")],
                provenance=[_provenance("package.json", "manifest")],
            ),
        ],
    )

    assert snapshot.component_ids_for_path(
        "components/console/changeset-console.tsx"
    ) == ["app:dashboard"]
    assert snapshot.component_ids_for_path("generated/api-types.ts") == [
        "app:dashboard"
    ]


def test_mixed_topology_snapshot_models_internal_and_external_dependencies() -> None:
    snapshot = WorkspaceTopologySnapshot(
        workspace_root=Path("/repo"),
        freshness="fresh",
        built_at=_now(),
        components=[
            _component("package:backend", "package", "backend", "src/glassbox"),
            _component("app:dashboard", "app", "dashboard", "frontend"),
        ],
        dependencies=[
            WorkspaceTopologyDependency(
                dependency_id="dep:dashboard:backend-api",
                source_component_id="app:dashboard",
                kind="workspace",
                target_component_id="package:backend",
                provenance=[_provenance("frontend/next.config.ts", "config")],
            ),
            WorkspaceTopologyDependency(
                dependency_id="dep:backend:fastapi",
                source_component_id="package:backend",
                kind="runtime",
                external_name="fastapi",
                manifest_path=Path("pyproject.toml"),
                provenance=[_provenance("pyproject.toml", "manifest")],
            ),
        ],
    )

    assert [dependency.kind for dependency in snapshot.dependencies] == [
        "workspace",
        "runtime",
    ]
    assert snapshot.component_ids_for_path(
        "frontend/e2e/operator-workflows.spec.ts"
    ) == ["app:dashboard"]


def test_stale_and_failed_topology_snapshots_degrade_recommendations() -> None:
    stale = WorkspaceTopologySnapshot(
        workspace_root=Path("/repo"),
        freshness="stale",
        components=[
            _component("package:backend", "package", "backend", "src/glassbox")
        ],
        limitations=[
            "manifest digest changed; rebuild before treating topology as fresh"
        ],
    )

    failed = WorkspaceTopologySnapshot(
        workspace_root=Path("/repo"),
        freshness="failed",
        failure_reason="package manifest could not be parsed",
    )

    assert stale.recommendation_posture == "degraded"
    assert failed.recommendation_posture == "unavailable"


def test_topology_rejects_ambiguous_or_invalid_shapes() -> None:
    with pytest.raises(ValidationError, match="component_id"):
        WorkspaceTopologySnapshot(
            workspace_root=Path("/repo"),
            freshness="fresh",
            built_at=_now(),
            components=[
                _component("package:backend", "package", "backend", "src/glassbox"),
                _component(
                    "package:backend", "package", "backend copy", "lib/glassbox"
                ),
            ],
        )

    with pytest.raises(ValidationError, match="target_component_id"):
        WorkspaceTopologySnapshot(
            workspace_root=Path("/repo"),
            freshness="fresh",
            built_at=_now(),
            components=[
                _component("package:backend", "package", "backend", "src/glassbox")
            ],
            dependencies=[
                WorkspaceTopologyDependency(
                    dependency_id="dep:missing",
                    source_component_id="package:backend",
                    kind="workspace",
                    target_component_id="app:missing",
                    provenance=[_provenance("pyproject.toml", "manifest")],
                ),
            ],
        )

    with pytest.raises(ValidationError, match="relative to the workspace root"):
        _component("package:absolute", "package", "absolute", "/tmp/repo/src")


def _component(
    component_id: str,
    kind: TopologyComponentKind,
    name: str,
    root_path: str,
) -> WorkspaceTopologyComponent:
    return WorkspaceTopologyComponent(
        component_id=component_id,
        kind=kind,
        name=name,
        root_path=Path(root_path),
        source_roots=[Path(root_path)],
        test_roots=[Path("tests") if kind == "package" else Path(f"{root_path}/e2e")],
        provenance=[_provenance(root_path, "path_convention")],
    )


def _provenance(path: str, source: TopologyProvenanceSource) -> TopologyProvenance:
    return TopologyProvenance(
        source=source,
        path=Path(path),
    )


def _now() -> datetime:
    return datetime(2026, 5, 2, tzinfo=UTC)
