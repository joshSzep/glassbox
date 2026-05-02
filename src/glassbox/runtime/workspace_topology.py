"""Typed local workspace topology models.

Topology is rebuildable repository intelligence. It can guide path-aware
verification, but source files and manifests remain authoritative.
"""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

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


__all__ = [
    "TopologyComponentKind",
    "TopologyDependencyKind",
    "TopologyFreshness",
    "TopologyManifestKind",
    "TopologyProvenance",
    "TopologyProvenanceSource",
    "TopologyRecommendationPosture",
    "TopologyManifestRef",
    "WorkspaceTopologyComponent",
    "WorkspaceTopologyDependency",
    "WorkspaceTopologySnapshot",
]
