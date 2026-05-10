"""Typed local workspace topology models.

Topology is rebuildable repository intelligence. It can guide path-aware
verification, but source files and manifests remain authoritative.
"""

import json
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.runtime.repository_index import build_repository_index
from glassbox.runtime.repository_index_discovery import BUILDER_VERSION
from glassbox.runtime.repository_index_discovery import classify_repository_path
from glassbox.runtime.repository_index_discovery import scan_indexable_files
from glassbox.runtime.repository_index_discovery import source_digest
from glassbox.runtime.repository_index_discovery import source_digest_inputs

TOPOLOGY_FILE = "workspace-topology.json"
TOPOLOGY_BUILDER_VERSION = f"{BUILDER_VERSION}:topology-v1"

TopologyComponentKind = Literal[
    "workspace",
    "package",
    "app",
    "library",
    "docs",
    "tests",
    "tooling",
    "generated",
]
TopologyDependencyKind = Literal[
    "runtime",
    "development",
    "build",
    "test",
    "workspace",
    "toolchain",
]
TopologyFreshness = Literal["fresh", "stale", "failed", "missing"]
TopologyManifestKind = Literal[
    "pyproject",
    "package_json",
    "workspace",
    "lockfile",
    "tool_config",
    "other",
]
TopologyProvenanceSource = Literal[
    "repository_index",
    "manifest",
    "lockfile",
    "config",
    "documentation",
    "path_convention",
    "user_hint",
]
TopologyRecommendationPosture = Literal["fresh", "degraded", "unavailable"]


class TopologyProvenance(BaseModel):
    """Inspectable evidence behind a topology claim."""

    model_config = ConfigDict(extra="forbid")

    source: TopologyProvenanceSource
    path: Path | None = None
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    source_label: str | None = Field(default=None, max_length=500)
    content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_source_shape(self) -> TopologyProvenance:
        if self.line_end is not None and self.line_start is None:
            raise ValueError("line_end requires line_start")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end must be greater than or equal to line_start")
        if self.source != "user_hint" and self.path is None:
            raise ValueError("non-user topology provenance requires path")
        if self.path is not None:
            _validate_relative_path(self.path, "provenance path")
        return self


class TopologyManifestRef(BaseModel):
    """A manifest, lockfile, or config file that shaped topology."""

    model_config = ConfigDict(extra="forbid")

    path: Path
    kind: TopologyManifestKind
    ecosystem: str | None = Field(default=None, max_length=100)
    package_manager: str | None = Field(default=None, max_length=100)
    provenance: list[TopologyProvenance] = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: Path) -> Path:
        return _validate_relative_path(value, "manifest path")


class WorkspaceTopologyComponent(BaseModel):
    """One workspace component such as an app, package, docs root, or test root."""

    model_config = ConfigDict(extra="forbid")

    component_id: str = Field(min_length=1, max_length=200)
    kind: TopologyComponentKind
    name: str = Field(min_length=1, max_length=500)
    root_path: Path
    language: str | None = Field(default=None, max_length=100)
    ecosystem: str | None = Field(default=None, max_length=100)
    package_manager: str | None = Field(default=None, max_length=100)
    manifests: list[TopologyManifestRef] = Field(default_factory=list)
    lockfiles: list[TopologyManifestRef] = Field(default_factory=list)
    source_roots: list[Path] = Field(default_factory=list)
    test_roots: list[Path] = Field(default_factory=list)
    docs_roots: list[Path] = Field(default_factory=list)
    generated_output_roots: list[Path] = Field(default_factory=list)
    ownership_hints: list[str] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=20)
    provenance: list[TopologyProvenance] = Field(min_length=1)

    @field_validator(
        "root_path",
        "source_roots",
        "test_roots",
        "docs_roots",
        "generated_output_roots",
        mode="after",
    )
    @classmethod
    def validate_component_paths(cls, value: Path | list[Path]) -> Path | list[Path]:
        if isinstance(value, list):
            return [_validate_relative_path(path, "component path") for path in value]
        return _validate_relative_path(value, "component path")

    @model_validator(mode="after")
    def validate_component_shape(self) -> WorkspaceTopologyComponent:
        if self.kind == "generated" and not self.generated_output_roots:
            raise ValueError(
                "generated topology components require generated_output_roots"
            )
        if self.kind == "docs" and not self.docs_roots:
            raise ValueError("docs topology components require docs_roots")
        if self.kind == "tests" and not self.test_roots:
            raise ValueError("tests topology components require test_roots")
        return self


class WorkspaceTopologyDependency(BaseModel):
    """A dependency edge between workspace components or an external package."""

    model_config = ConfigDict(extra="forbid")

    dependency_id: str = Field(min_length=1, max_length=200)
    source_component_id: str = Field(min_length=1, max_length=200)
    kind: TopologyDependencyKind
    target_component_id: str | None = Field(default=None, min_length=1, max_length=200)
    external_name: str | None = Field(default=None, min_length=1, max_length=500)
    version_constraint: str | None = Field(default=None, max_length=500)
    manifest_path: Path | None = None
    provenance: list[TopologyProvenance] = Field(min_length=1)

    @field_validator("manifest_path")
    @classmethod
    def validate_manifest_path(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        return _validate_relative_path(value, "dependency manifest path")

    @model_validator(mode="after")
    def validate_target(self) -> WorkspaceTopologyDependency:
        if (self.target_component_id is None) == (self.external_name is None):
            raise ValueError(
                "topology dependencies require exactly one target_component_id "
                "or external_name"
            )
        return self


class WorkspaceTopologySnapshot(BaseModel):
    """Versioned topology snapshot for one local workspace."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1)
    workspace_root: Path
    freshness: TopologyFreshness
    built_at: datetime | None = None
    builder_version: str = Field(default="v1", min_length=1, max_length=100)
    source_digest: str | None = Field(default=None, min_length=64, max_length=64)
    source_inputs: list[str] = Field(default_factory=list)
    components: list[WorkspaceTopologyComponent] = Field(default_factory=list)
    dependencies: list[WorkspaceTopologyDependency] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    failure_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_snapshot(self) -> WorkspaceTopologySnapshot:
        if self.freshness == "fresh" and self.built_at is None:
            raise ValueError("fresh topology snapshots require built_at")
        if self.freshness == "failed" and self.failure_reason is None:
            raise ValueError("failed topology snapshots require failure_reason")
        if self.freshness == "fresh" and not self.components:
            raise ValueError("fresh topology snapshots require at least one component")

        component_ids = [component.component_id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("topology components require unique component_id values")

        dependency_ids = [dependency.dependency_id for dependency in self.dependencies]
        if len(dependency_ids) != len(set(dependency_ids)):
            raise ValueError(
                "topology dependencies require unique dependency_id values"
            )

        known_components = set(component_ids)
        for dependency in self.dependencies:
            if dependency.source_component_id not in known_components:
                raise ValueError(
                    "dependency source_component_id must reference a component"
                )
            if (
                dependency.target_component_id is not None
                and dependency.target_component_id not in known_components
            ):
                raise ValueError(
                    "dependency target_component_id must reference a component"
                )
        return self

    @property
    def recommendation_posture(self) -> TopologyRecommendationPosture:
        """How consumers should treat recommendations derived from this snapshot."""

        if self.freshness == "fresh":
            return "fresh"
        if self.freshness == "stale":
            return "degraded"
        return "unavailable"

    def component_ids_for_path(self, path: Path | str) -> list[str]:
        """Return components whose declared roots contain a relative workspace path."""

        relative = _validate_relative_path(Path(path), "lookup path")
        matches: list[tuple[int, str]] = []
        for component in self.components:
            roots = [
                component.root_path,
                *component.source_roots,
                *component.test_roots,
                *component.docs_roots,
                *component.generated_output_roots,
            ]
            for root in roots:
                if _path_contains(root, relative):
                    matches.append((len(root.parts), component.component_id))
                    break
        return [component_id for _, component_id in sorted(matches, reverse=True)]


class WorkspaceTopologyNotFoundError(ValueError):
    """Raised when topology reads require a missing snapshot."""


def workspace_topology_path(workspace_root: Path) -> Path:
    """Return the local topology artifact path for a workspace."""

    return workspace_root / ".glassbox" / TOPOLOGY_FILE


def build_workspace_topology(
    workspace_root: Path,
    *,
    repository_index: RepositoryIndexSnapshot | None = None,
) -> WorkspaceTopologySnapshot:
    """Build a deterministic topology snapshot from local manifests and index data."""

    root = workspace_root.resolve()
    scan = scan_indexable_files(root)
    files = scan.files
    built_at = datetime.now(UTC)
    index = (
        repository_index
        if repository_index is not None
        else build_repository_index(root)
    )
    components = _derive_components(root, built_at)
    dependencies = _derive_dependencies(root, components)
    limitations: list[str] = []
    if not components:
        limitations.append("no supported topology manifests were discovered")
    if index.status.value != "fresh":
        limitations.append("repository index was not fresh while deriving topology")
    limitations.extend(scan.limitations)

    return WorkspaceTopologySnapshot(
        workspace_root=root,
        freshness="fresh" if components else "missing",
        built_at=built_at if components else None,
        builder_version=TOPOLOGY_BUILDER_VERSION,
        source_digest=source_digest(root, files),
        source_inputs=source_digest_inputs(root, files),
        components=components,
        dependencies=dependencies,
        limitations=limitations,
    )


def build_and_write_workspace_topology(
    workspace_root: Path,
) -> WorkspaceTopologySnapshot:
    """Build and persist the local workspace topology snapshot."""

    snapshot = build_workspace_topology(workspace_root)
    write_workspace_topology(workspace_root, snapshot)
    return snapshot


def write_workspace_topology(
    workspace_root: Path,
    snapshot: WorkspaceTopologySnapshot,
) -> Path:
    """Write a topology snapshot to the local artifact path."""

    path = workspace_topology_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_workspace_topology(workspace_root: Path) -> WorkspaceTopologySnapshot:
    """Load topology and mark it stale if source inputs changed."""

    root = workspace_root.resolve()
    path = workspace_topology_path(root)
    if not path.exists():
        raise WorkspaceTopologyNotFoundError("workspace topology has not been built")
    snapshot = WorkspaceTopologySnapshot.model_validate_json(path.read_text())
    files = scan_indexable_files(root).files
    current_digest = source_digest(root, files)
    if snapshot.source_digest is not None and snapshot.source_digest != current_digest:
        return snapshot.model_copy(update={"freshness": "stale"})
    return snapshot


def _derive_components(
    root: Path, built_at: datetime
) -> list[WorkspaceTopologyComponent]:
    components: list[WorkspaceTopologyComponent] = []
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        components.append(_python_component(root, pyproject, built_at))
    for package_json in sorted(root.rglob("package.json")):
        relative = package_json.relative_to(root)
        if _is_excluded_topology_path(relative):
            continue
        components.append(_node_component(root, package_json, built_at))
    docs = root / "docs"
    if docs.exists() and docs.is_dir():
        components.append(
            WorkspaceTopologyComponent(
                component_id="docs:docs",
                kind="docs",
                name="docs",
                root_path=Path("docs"),
                docs_roots=[Path("docs")],
                provenance=[_provenance("path_convention", Path("docs"))],
            )
        )
    return _dedupe_components(components)


def _python_component(
    root: Path,
    pyproject: Path,
    built_at: datetime,
) -> WorkspaceTopologyComponent:
    relative = pyproject.relative_to(root)
    data = _read_toml(pyproject)
    project = data.get("project", {})
    if not isinstance(project, dict):
        project = {}
    name = str(project.get("name", root.name))
    source_roots = _existing_paths(root, ["src", name.replace("-", "_")])
    test_roots = _existing_paths(root, ["tests"])
    docs_roots = _existing_paths(root, ["docs"])
    generated = _existing_paths(root, ["src/glassbox/web/static_next"])
    lockfiles = _manifest_refs(root, ["uv.lock", "poetry.lock"], "lockfile", built_at)
    return WorkspaceTopologyComponent(
        component_id=f"package:{name}",
        kind="package",
        name=name,
        root_path=Path("."),
        language="python",
        ecosystem="python",
        package_manager="uv" if (root / "uv.lock").exists() else None,
        manifests=[
            TopologyManifestRef(
                path=relative,
                kind="pyproject",
                ecosystem="python",
                package_manager="uv" if (root / "uv.lock").exists() else None,
                provenance=[_provenance("manifest", relative)],
            )
        ],
        lockfiles=lockfiles,
        source_roots=source_roots or [Path(".")],
        test_roots=test_roots,
        docs_roots=docs_roots,
        generated_output_roots=generated,
        provenance=[_provenance("manifest", relative)],
        tags=["python"],
    )


def _node_component(
    root: Path,
    package_json: Path,
    built_at: datetime,
) -> WorkspaceTopologyComponent:
    relative = package_json.relative_to(root)
    component_root = relative.parent
    data = _read_json(package_json)
    name = str(data.get("name") or component_root.name or root.name)
    package_manager = (
        "pnpm" if (package_json.parent / "pnpm-lock.yaml").exists() else None
    )
    source_roots = _existing_paths(
        root,
        [
            component_root / "app",
            component_root / "components",
            component_root / "src",
            component_root / "stores",
        ],
    )
    test_roots = _existing_paths(
        root, [component_root / "tests", component_root / "e2e"]
    )
    generated = _existing_paths(
        root, [component_root / "generated", component_root / "out"]
    )
    return WorkspaceTopologyComponent(
        component_id=f"app:{name}",
        kind="app",
        name=name,
        root_path=component_root,
        language="typescript",
        ecosystem="node",
        package_manager=package_manager,
        manifests=[
            TopologyManifestRef(
                path=relative,
                kind="package_json",
                ecosystem="node",
                package_manager=package_manager,
                provenance=[_provenance("manifest", relative)],
            )
        ],
        lockfiles=_manifest_refs(
            root,
            [component_root / "pnpm-lock.yaml", component_root / "package-lock.json"],
            "lockfile",
            built_at,
        ),
        source_roots=source_roots or [component_root],
        test_roots=test_roots,
        generated_output_roots=generated,
        provenance=[_provenance("manifest", relative)],
        tags=["frontend"],
    )


def _derive_dependencies(
    root: Path,
    components: list[WorkspaceTopologyComponent],
) -> list[WorkspaceTopologyDependency]:
    dependencies: list[WorkspaceTopologyDependency] = []
    component_by_path = {component.root_path: component for component in components}
    pyproject = root / "pyproject.toml"
    python_component = component_by_path.get(Path("."))
    if pyproject.exists() and python_component is not None:
        for name, kind in _pyproject_dependency_names(pyproject):
            dependencies.append(
                _external_dependency(
                    python_component.component_id,
                    name,
                    kind,
                    Path("pyproject.toml"),
                )
            )
    for package_json in sorted(root.rglob("package.json")):
        relative = package_json.relative_to(root)
        if _is_excluded_topology_path(relative):
            continue
        component = component_by_path.get(relative.parent)
        if component is None:
            continue
        for name, kind in _package_dependency_names(package_json):
            dependencies.append(
                _external_dependency(component.component_id, name, kind, relative)
            )
    return _dedupe_dependencies(dependencies)


def _external_dependency(
    component_id: str,
    name: str,
    kind: TopologyDependencyKind,
    manifest_path: Path,
) -> WorkspaceTopologyDependency:
    return WorkspaceTopologyDependency(
        dependency_id=f"dep:{component_id}:{kind}:{name}",
        source_component_id=component_id,
        kind=kind,
        external_name=name,
        manifest_path=manifest_path,
        provenance=[_provenance("manifest", manifest_path)],
    )


def _validate_relative_path(value: Path, label: str) -> Path:
    if value.is_absolute():
        raise ValueError(f"{label} must be relative to the workspace root")
    if any(part == ".." for part in value.parts):
        raise ValueError(f"{label} must not escape the workspace root")
    return value


def _path_contains(root: Path, path: Path) -> bool:
    if root == Path("."):
        return True
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _existing_paths(root: Path, candidates: list[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for candidate in candidates:
        relative = Path(candidate)
        if (root / relative).exists():
            paths.append(relative)
    return paths


def _manifest_refs(
    root: Path,
    candidates: list[str | Path],
    kind: TopologyManifestKind,
    _built_at: datetime,
) -> list[TopologyManifestRef]:
    refs: list[TopologyManifestRef] = []
    for candidate in candidates:
        relative = Path(candidate)
        if (root / relative).exists():
            refs.append(
                TopologyManifestRef(
                    path=relative,
                    kind=kind,
                    provenance=[
                        _provenance(
                            "lockfile" if kind == "lockfile" else "manifest", relative
                        )
                    ],
                )
            )
    return refs


def _provenance(
    source: TopologyProvenanceSource,
    path: Path,
) -> TopologyProvenance:
    return TopologyProvenance(source=source, path=path)


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError, tomllib.TOMLDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _pyproject_dependency_names(
    path: Path,
) -> list[tuple[str, TopologyDependencyKind]]:
    data = _read_toml(path)
    project = data.get("project", {})
    if not isinstance(project, dict):
        return []
    names: list[tuple[str, TopologyDependencyKind]] = []
    for value in project.get("dependencies", []):
        if isinstance(value, str):
            names.append((_dependency_name(value), "runtime"))
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, dict):
        for values in optional.values():
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, str):
                        names.append((_dependency_name(value), "development"))
    return names


def _package_dependency_names(path: Path) -> list[tuple[str, TopologyDependencyKind]]:
    data = _read_json(path)
    names: list[tuple[str, TopologyDependencyKind]] = []
    dependency_sections: tuple[tuple[str, TopologyDependencyKind], ...] = (
        ("dependencies", "runtime"),
        ("devDependencies", "development"),
        ("peerDependencies", "runtime"),
        ("optionalDependencies", "runtime"),
    )
    for section, kind in dependency_sections:
        raw = data.get(section, {})
        if not isinstance(raw, dict):
            continue
        for name in raw:
            if isinstance(name, str):
                names.append((name, kind))
    return names


def _dependency_name(value: str) -> str:
    for separator in ("[", "<", ">", "=", "~", "!", ";", " "):
        value = value.split(separator, 1)[0]
    return value.strip()


def _dedupe_components(
    components: list[WorkspaceTopologyComponent],
) -> list[WorkspaceTopologyComponent]:
    seen: set[str] = set()
    deduped: list[WorkspaceTopologyComponent] = []
    for component in components:
        component_id = component.component_id
        if component_id in seen:
            suffix = component.root_path.as_posix().replace("/", "-") or "root"
            component = component.model_copy(
                update={"component_id": f"{component_id}:{suffix}"}
            )
        seen.add(component.component_id)
        deduped.append(component)
    return deduped


def _dedupe_dependencies(
    dependencies: list[WorkspaceTopologyDependency],
) -> list[WorkspaceTopologyDependency]:
    seen: set[str] = set()
    deduped: list[WorkspaceTopologyDependency] = []
    for dependency in dependencies:
        if dependency.dependency_id in seen:
            continue
        seen.add(dependency.dependency_id)
        deduped.append(dependency)
    return deduped


def _is_excluded_topology_path(relative: Path) -> bool:
    return classify_repository_path(relative).excluded


__all__ = [
    "TOPOLOGY_BUILDER_VERSION",
    "TOPOLOGY_FILE",
    "TopologyComponentKind",
    "TopologyDependencyKind",
    "TopologyFreshness",
    "TopologyManifestKind",
    "TopologyProvenance",
    "TopologyProvenanceSource",
    "TopologyRecommendationPosture",
    "TopologyManifestRef",
    "WorkspaceTopologyNotFoundError",
    "WorkspaceTopologyComponent",
    "WorkspaceTopologyDependency",
    "WorkspaceTopologySnapshot",
    "build_and_write_workspace_topology",
    "build_workspace_topology",
    "load_workspace_topology",
    "workspace_topology_path",
    "write_workspace_topology",
]
