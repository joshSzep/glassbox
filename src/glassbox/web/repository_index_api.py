"""HTTP transport models and serializers for repository index APIs."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.runtime.workspace_topology import TopologyManifestRef
from glassbox.runtime.workspace_topology import TopologyProvenance
from glassbox.runtime.workspace_topology import WorkspaceTopologyComponent
from glassbox.runtime.workspace_topology import WorkspaceTopologyDependency
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot
from glassbox.web.session_api import PageInfoResponse
from glassbox.web.task_api import BackgroundJobResponse


class RepositoryIndexProvenanceResponse(BaseModel):
    source_type: str
    path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    source_label: str | None = None
    content_sha256: str | None = None
    tool_name: str | None = None
    note: str | None = None


class RepositoryIndexEntryResponse(BaseModel):
    entry_id: str
    kind: str
    name: str
    summary: str | None = None
    path: str | None = None
    symbol: str | None = None
    language: str | None = None
    provenance: list[RepositoryIndexProvenanceResponse]
    tags: list[str]
    updated_at: datetime


class RepositoryIndexStatusResponse(BaseModel):
    status: str
    path: str
    entry_count: int
    built_at: datetime | None = None
    schema_version: int | None = None
    builder_version: str | None = None
    source_digest: str | None = None
    source_manifest_count: int = 0
    source_root_count: int = 0
    test_root_count: int = 0
    doc_root_count: int = 0
    generated_path_count: int = 0
    policy_sensitive_path_count: int = 0
    package_boundary_count: int = 0
    command_recipe_count: int = 0
    ownership_hint_count: int = 0
    subsystem_count: int = 0
    release_surface_count: int = 0
    memory_reference_count: int = 0
    limitations: list[str] = Field(default_factory=list)
    detail: str | None = None


class RepositoryIndexInspectResponse(BaseModel):
    index: RepositoryIndexStatusResponse
    source_roots: list[str]
    test_roots: list[str]
    doc_roots: list[str]
    generated_paths: list[str]
    policy_sensitive_paths: list[str]
    package_boundaries: list[str]
    command_recipes: list[str]
    ownership_hints: list[str]
    subsystems: list[str]
    release_sensitive_surfaces: list[str]
    memory_references: list[str]
    limitations: list[str]


class RepositoryIndexSearchPageResponse(BaseModel):
    query: str
    page: PageInfoResponse
    items: list[RepositoryIndexEntryResponse]


class RepositoryIndexEntryDetailResponse(BaseModel):
    entry: RepositoryIndexEntryResponse


class RepositoryIndexRebuildRequest(BaseModel):
    session_id: str | None = None
    requested_by: str = "operator"
    background: bool = True


class RepositoryIndexRebuildResponse(BaseModel):
    mode: str
    status: str
    index: RepositoryIndexStatusResponse | None = None
    job: BackgroundJobResponse | None = None
    detail: str | None = None


class TopologyProvenanceResponse(BaseModel):
    source: str
    path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    source_label: str | None = None
    content_sha256: str | None = None
    note: str | None = None


class TopologyManifestResponse(BaseModel):
    path: str
    kind: str
    ecosystem: str | None = None
    package_manager: str | None = None
    provenance: list[TopologyProvenanceResponse]


class WorkspaceTopologyComponentResponse(BaseModel):
    component_id: str
    kind: str
    name: str
    root_path: str
    language: str | None = None
    ecosystem: str | None = None
    package_manager: str | None = None
    manifests: list[TopologyManifestResponse]
    lockfiles: list[TopologyManifestResponse]
    source_roots: list[str]
    test_roots: list[str]
    docs_roots: list[str]
    generated_output_roots: list[str]
    ownership_hints: list[str]
    tags: list[str]
    provenance: list[TopologyProvenanceResponse]


class WorkspaceTopologyDependencyResponse(BaseModel):
    dependency_id: str
    source_component_id: str
    kind: str
    target_component_id: str | None = None
    external_name: str | None = None
    version_constraint: str | None = None
    manifest_path: str | None = None
    provenance: list[TopologyProvenanceResponse]


class WorkspaceTopologyStatusResponse(BaseModel):
    freshness: str
    path: str
    component_count: int
    dependency_count: int
    recommendation_posture: str
    built_at: datetime | None = None
    schema_version: int | None = None
    builder_version: str | None = None
    source_digest: str | None = None
    limitations: list[str]
    failure_reason: str | None = None
    detail: str | None = None
    next_actions: list[str]


class WorkspaceTopologyDetailResponse(BaseModel):
    topology: WorkspaceTopologyStatusResponse
    components: list[WorkspaceTopologyComponentResponse]
    dependencies: list[WorkspaceTopologyDependencyResponse]


class WorkspaceTopologyRebuildRequest(BaseModel):
    requested_by: str = "operator"


class WorkspaceTopologyRebuildResponse(BaseModel):
    status: str
    topology: WorkspaceTopologyStatusResponse


def build_repository_index_status_response(
    snapshot: RepositoryIndexSnapshot,
    *,
    path: str,
) -> RepositoryIndexStatusResponse:
    return RepositoryIndexStatusResponse(
        status=snapshot.status.value,
        path=path,
        entry_count=len(snapshot.entries),
        built_at=snapshot.built_at,
        schema_version=snapshot.schema_version,
        builder_version=snapshot.builder_version,
        source_digest=snapshot.source_digest,
        source_manifest_count=len(snapshot.source_manifests),
        source_root_count=len(snapshot.source_roots),
        test_root_count=len(snapshot.test_roots),
        doc_root_count=len(snapshot.doc_roots),
        generated_path_count=len(snapshot.generated_paths),
        policy_sensitive_path_count=len(snapshot.policy_sensitive_paths),
        package_boundary_count=len(snapshot.package_boundaries),
        command_recipe_count=len(snapshot.command_recipes),
        ownership_hint_count=len(snapshot.ownership_hints),
        subsystem_count=len(snapshot.subsystems),
        release_surface_count=len(snapshot.release_sensitive_surfaces),
        memory_reference_count=len(snapshot.memory_references),
        limitations=snapshot.limitations,
    )


def build_repository_index_inspect_response(
    snapshot: RepositoryIndexSnapshot,
    *,
    path: str,
) -> RepositoryIndexInspectResponse:
    return RepositoryIndexInspectResponse(
        index=build_repository_index_status_response(snapshot, path=path),
        source_roots=[hint.path.as_posix() for hint in snapshot.source_roots],
        test_roots=[hint.path.as_posix() for hint in snapshot.test_roots],
        doc_roots=[hint.path.as_posix() for hint in snapshot.doc_roots],
        generated_paths=[hint.path.as_posix() for hint in snapshot.generated_paths],
        policy_sensitive_paths=[
            hint.path.as_posix() for hint in snapshot.policy_sensitive_paths
        ],
        package_boundaries=[
            package.package_id for package in snapshot.package_boundaries
        ],
        command_recipes=[recipe.recipe_id for recipe in snapshot.command_recipes],
        ownership_hints=[hint.hint_id for hint in snapshot.ownership_hints],
        subsystems=[subsystem.subsystem_id for subsystem in snapshot.subsystems],
        release_sensitive_surfaces=[
            surface.surface_id for surface in snapshot.release_sensitive_surfaces
        ],
        memory_references=[
            reference.reference_id for reference in snapshot.memory_references
        ],
        limitations=snapshot.limitations,
    )


def build_repository_index_entry_response(
    entry: RepositoryIndexEntry,
) -> RepositoryIndexEntryResponse:
    return RepositoryIndexEntryResponse(
        entry_id=entry.entry_id,
        kind=entry.kind.value,
        name=entry.name,
        summary=entry.summary,
        path=entry.path.as_posix() if entry.path is not None else None,
        symbol=entry.symbol,
        language=entry.language,
        provenance=[_provenance_response(item) for item in entry.provenance],
        tags=entry.tags,
        updated_at=entry.updated_at,
    )


def build_repository_index_entry_responses(
    entries: Sequence[RepositoryIndexEntry],
) -> list[RepositoryIndexEntryResponse]:
    return [build_repository_index_entry_response(entry) for entry in entries]


def _provenance_response(
    provenance: RepositoryIndexProvenance,
) -> RepositoryIndexProvenanceResponse:
    return RepositoryIndexProvenanceResponse(
        source_type=provenance.source_type.value,
        path=provenance.path.as_posix() if provenance.path is not None else None,
        line_start=provenance.line_start,
        line_end=provenance.line_end,
        source_label=provenance.source_label,
        content_sha256=provenance.content_sha256,
        tool_name=provenance.tool_name,
        note=provenance.note,
    )


def build_workspace_topology_status_response(
    snapshot: WorkspaceTopologySnapshot,
    *,
    path: str,
    detail: str | None = None,
    next_actions: list[str] | None = None,
) -> WorkspaceTopologyStatusResponse:
    return WorkspaceTopologyStatusResponse(
        freshness=snapshot.freshness,
        path=path,
        component_count=len(snapshot.components),
        dependency_count=len(snapshot.dependencies),
        recommendation_posture=snapshot.recommendation_posture,
        built_at=snapshot.built_at,
        schema_version=snapshot.schema_version,
        builder_version=snapshot.builder_version,
        source_digest=snapshot.source_digest,
        limitations=snapshot.limitations,
        failure_reason=snapshot.failure_reason,
        detail=detail,
        next_actions=next_actions or [],
    )


def build_workspace_topology_detail_response(
    snapshot: WorkspaceTopologySnapshot,
    *,
    path: str,
) -> WorkspaceTopologyDetailResponse:
    return WorkspaceTopologyDetailResponse(
        topology=build_workspace_topology_status_response(snapshot, path=path),
        components=[
            _topology_component_response(component) for component in snapshot.components
        ],
        dependencies=[
            _topology_dependency_response(dependency)
            for dependency in snapshot.dependencies
        ],
    )


def _topology_component_response(
    component: WorkspaceTopologyComponent,
) -> WorkspaceTopologyComponentResponse:
    return WorkspaceTopologyComponentResponse(
        component_id=component.component_id,
        kind=component.kind,
        name=component.name,
        root_path=component.root_path.as_posix(),
        language=component.language,
        ecosystem=component.ecosystem,
        package_manager=component.package_manager,
        manifests=[
            _topology_manifest_response(manifest) for manifest in component.manifests
        ],
        lockfiles=[
            _topology_manifest_response(lockfile) for lockfile in component.lockfiles
        ],
        source_roots=[path.as_posix() for path in component.source_roots],
        test_roots=[path.as_posix() for path in component.test_roots],
        docs_roots=[path.as_posix() for path in component.docs_roots],
        generated_output_roots=[
            path.as_posix() for path in component.generated_output_roots
        ],
        ownership_hints=component.ownership_hints,
        tags=component.tags,
        provenance=[
            _topology_provenance_response(item) for item in component.provenance
        ],
    )


def _topology_dependency_response(
    dependency: WorkspaceTopologyDependency,
) -> WorkspaceTopologyDependencyResponse:
    return WorkspaceTopologyDependencyResponse(
        dependency_id=dependency.dependency_id,
        source_component_id=dependency.source_component_id,
        kind=dependency.kind,
        target_component_id=dependency.target_component_id,
        external_name=dependency.external_name,
        version_constraint=dependency.version_constraint,
        manifest_path=dependency.manifest_path.as_posix()
        if dependency.manifest_path is not None
        else None,
        provenance=[
            _topology_provenance_response(item) for item in dependency.provenance
        ],
    )


def _topology_manifest_response(
    manifest: TopologyManifestRef,
) -> TopologyManifestResponse:
    return TopologyManifestResponse(
        path=manifest.path.as_posix(),
        kind=manifest.kind,
        ecosystem=manifest.ecosystem,
        package_manager=manifest.package_manager,
        provenance=[
            _topology_provenance_response(item) for item in manifest.provenance
        ],
    )


def _topology_provenance_response(
    provenance: TopologyProvenance,
) -> TopologyProvenanceResponse:
    return TopologyProvenanceResponse(
        source=provenance.source,
        path=provenance.path.as_posix() if provenance.path is not None else None,
        line_start=provenance.line_start,
        line_end=provenance.line_end,
        source_label=provenance.source_label,
        content_sha256=provenance.content_sha256,
        note=provenance.note,
    )
