"""HTTP transport models and serializers for repository index APIs."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel

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
    detail: str | None = None


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
