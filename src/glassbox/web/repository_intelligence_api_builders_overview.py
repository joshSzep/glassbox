"""Overview and freshness-adjacent builders for repository intelligence APIs."""

from collections.abc import Sequence

from glassbox.core.models import RepositoryIntelligenceMemoryReference
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSourceManifest
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.web.repository_index_api import RepositoryIndexStatusResponse
from glassbox.web.repository_index_api import WorkspaceTopologyStatusResponse
from glassbox.web.repository_index_api import build_repository_index_status_response
from glassbox.web.repository_intelligence_api_builders_paths import (
    build_package_boundary_responses,
)
from glassbox.web.repository_intelligence_api_builders_paths import (
    build_path_hint_responses,
)
from glassbox.web.repository_intelligence_api_builders_paths import (
    build_release_surface_responses,
)
from glassbox.web.repository_intelligence_api_builders_paths import (
    build_subsystem_responses,
)
from glassbox.web.repository_intelligence_api_builders_paths import provenance_response
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceMemoryReferenceResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceOverviewResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceSourceManifestResponse,
)


def build_repository_intelligence_overview_response(
    *,
    index: RepositoryIndexStatusResponse,
    topology: WorkspaceTopologyStatusResponse | None,
    source_manifests: Sequence[RepositoryIntelligenceSourceManifest],
    source_roots: Sequence[RepositoryIntelligencePathHint],
    test_roots: Sequence[RepositoryIntelligencePathHint],
    doc_roots: Sequence[RepositoryIntelligencePathHint],
    generated_paths: Sequence[RepositoryIntelligencePathHint],
    policy_sensitive_paths: Sequence[RepositoryIntelligencePathHint],
    package_boundaries: Sequence[RepositoryIntelligencePackageBoundary],
    subsystems: Sequence[RepositoryIntelligenceSubsystem],
    release_surfaces: Sequence[RepositoryIntelligenceReleaseSurface],
    memory_references: Sequence[RepositoryIntelligenceMemoryReference],
    limitations: Sequence[str],
) -> RepositoryIntelligenceOverviewResponse:
    return RepositoryIntelligenceOverviewResponse(
        index=index,
        topology=topology,
        source_manifests=[
            build_source_manifest_response(item) for item in source_manifests
        ],
        source_roots=build_path_hint_responses(source_roots),
        test_roots=build_path_hint_responses(test_roots),
        doc_roots=build_path_hint_responses(doc_roots),
        generated_paths=build_path_hint_responses(generated_paths),
        policy_sensitive_paths=build_path_hint_responses(policy_sensitive_paths),
        package_boundaries=build_package_boundary_responses(package_boundaries),
        subsystems=build_subsystem_responses(subsystems),
        release_surfaces=build_release_surface_responses(release_surfaces),
        memory_references=[
            build_memory_reference_response(item) for item in memory_references
        ],
        limitations=list(limitations),
    )


def build_source_manifest_response(
    manifest: RepositoryIntelligenceSourceManifest,
) -> RepositoryIntelligenceSourceManifestResponse:
    return RepositoryIntelligenceSourceManifestResponse(
        manifest_id=manifest.manifest_id,
        path=manifest.path.as_posix(),
        source_type=manifest.source_type.value,
        role=manifest.role,
        digest=manifest.digest,
        provenance=[provenance_response(item) for item in manifest.provenance],
        limitations=manifest.limitations,
    )


def build_memory_reference_response(
    reference: RepositoryIntelligenceMemoryReference,
) -> RepositoryIntelligenceMemoryReferenceResponse:
    return RepositoryIntelligenceMemoryReferenceResponse(
        reference_id=reference.reference_id,
        memory_id=str(reference.memory_id),
        kind=reference.kind.value,
        summary=reference.summary,
        source_label=reference.source_label,
        confirmed_by=reference.confirmed_by,
        confirmed_at=reference.confirmed_at,
        tags=reference.tags,
        redacted=reference.redacted,
        confidence=reference.confidence.value,
        provenance=reference.provenance.model_dump(mode="json"),
        limitations=reference.limitations,
    )


def build_repository_status_response_from_snapshot(
    snapshot,
    *,
    path: str,
) -> RepositoryIndexStatusResponse:
    return build_repository_index_status_response(snapshot, path=path)
