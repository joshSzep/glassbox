"""Topology impact summaries for reviewable changesets."""

from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.workspace_topology import TopologyFreshness
from glassbox.runtime.workspace_topology import TopologyRecommendationPosture
from glassbox.runtime.workspace_topology import WorkspaceTopologyComponent
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot
from glassbox.runtime.workspace_topology import load_workspace_topology


class ChangesetTopologyImpact(BaseModel):
    """Affected local subsystem derived from workspace topology."""

    model_config = ConfigDict(extra="forbid")

    component_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=500)
    kind: str = Field(min_length=1, max_length=100)
    root_path: str = Field(min_length=1, max_length=1000)
    matched_paths: list[str] = Field(default_factory=list)
    test_roots: list[str] = Field(default_factory=list)
    ownership_hints: list[str] = Field(default_factory=list)
    dependency_hints: list[str] = Field(default_factory=list)
    topology_freshness: TopologyFreshness
    recommendation_posture: TopologyRecommendationPosture
    limitations: list[str] = Field(default_factory=list)


def derive_changeset_topology_impacts(
    *,
    workspace_root: Path,
    changed_paths: list[str],
) -> tuple[list[ChangesetTopologyImpact], list[str]]:
    """Return topology-derived affected subsystem summaries for changed paths."""

    if not changed_paths:
        return [], []
    try:
        topology = load_workspace_topology(workspace_root)
    except WorkspaceTopologyNotFoundError:
        return [], []
    except ValueError as exc:
        return [], [f"Workspace topology could not be read: {exc}"]
    if topology.recommendation_posture == "unavailable":
        reason = topology.failure_reason or topology.freshness
        return [], [f"Workspace topology is unavailable; reason: {reason}."]

    limitations: list[str] = []
    if topology.recommendation_posture == "degraded":
        limitations.append(
            "Workspace topology is stale; rebuild before treating subsystem "
            "and test-root guidance as current."
        )

    impacts: list[ChangesetTopologyImpact] = []
    for component in topology.components:
        matched_paths = [
            path
            for path in changed_paths
            if _component_contains_path(component, Path(path))
        ]
        if not matched_paths:
            continue
        component_limitations = list(limitations)
        if topology.recommendation_posture == "degraded":
            component_limitations.append(
                "Topology inputs changed after this component snapshot was built."
            )
        impacts.append(
            ChangesetTopologyImpact(
                component_id=component.component_id,
                name=component.name,
                kind=component.kind,
                root_path=component.root_path.as_posix(),
                matched_paths=matched_paths,
                test_roots=[path.as_posix() for path in component.test_roots],
                ownership_hints=list(component.ownership_hints),
                dependency_hints=_dependency_hints(topology, component.component_id),
                topology_freshness=topology.freshness,
                recommendation_posture=topology.recommendation_posture,
                limitations=list(dict.fromkeys(component_limitations)),
            )
        )
    impacts.sort(key=lambda impact: (impact.root_path, impact.component_id))
    return impacts, limitations


def _component_contains_path(
    component: WorkspaceTopologyComponent,
    path: Path,
) -> bool:
    roots = [
        *component.source_roots,
        *component.test_roots,
        *component.docs_roots,
        *component.generated_output_roots,
    ]
    if not roots:
        roots = [component.root_path]
    if path in {manifest.path for manifest in component.manifests}:
        return True
    if path in {lockfile.path for lockfile in component.lockfiles}:
        return True
    return any(_path_contains(root, path) for root in roots)


def _dependency_hints(
    topology: WorkspaceTopologySnapshot,
    component_id: str,
) -> list[str]:
    hints: list[str] = []
    for dependency in topology.dependencies:
        if dependency.source_component_id == component_id:
            target = dependency.target_component_id or dependency.external_name
            if target is not None:
                hints.append(f"{dependency.kind} dependency: {target}")
        elif dependency.target_component_id == component_id:
            hints.append(f"depended on by: {dependency.source_component_id}")
    return list(dict.fromkeys(hints))[:20]


def _path_contains(root: Path, path: Path) -> bool:
    if root == Path("."):
        return True
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


__all__ = [
    "ChangesetTopologyImpact",
    "derive_changeset_topology_impacts",
]
