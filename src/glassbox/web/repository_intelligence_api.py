"""HTTP models for repository intelligence v2 APIs."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceMemoryReference
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSourceManifest
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.runtime.eval_recommendations import EvalRecommendationReport
from glassbox.runtime.repository_intelligence_freshness import (
    RepositoryIntelligenceFreshnessCue,
)
from glassbox.runtime.repository_intelligence_queries import (
    RepositoryIntelligencePathInspection,
)
from glassbox.web.memory_api import WorkspaceMemoryCandidateResponse
from glassbox.web.repository_index_api import RepositoryIndexEntryResponse
from glassbox.web.repository_index_api import RepositoryIndexProvenanceResponse
from glassbox.web.repository_index_api import RepositoryIndexStatusResponse
from glassbox.web.repository_index_api import WorkspaceTopologyStatusResponse
from glassbox.web.repository_index_api import build_repository_index_entry_response
from glassbox.web.repository_index_api import build_repository_index_status_response
from glassbox.web.session_api import PageInfoResponse


class RepositoryIntelligenceSourceManifestResponse(BaseModel):
    manifest_id: str
    path: str
    source_type: str
    role: str
    digest: str | None = None
    provenance: list[RepositoryIndexProvenanceResponse]
    limitations: list[str]


class RepositoryIntelligencePathHintResponse(BaseModel):
    hint_id: str
    kind: str
    path: str
    package_id: str | None = None
    language: str | None = None
    confidence: str
    provenance: list[RepositoryIndexProvenanceResponse]
    limitations: list[str]


class RepositoryIntelligencePackageBoundaryResponse(BaseModel):
    package_id: str
    name: str
    kind: str
    root: str
    manifest_paths: list[str]
    source_roots: list[str]
    test_roots: list[str]
    doc_roots: list[str]
    generated_paths: list[str]
    confidence: str
    provenance: list[RepositoryIndexProvenanceResponse]
    limitations: list[str]


class RepositoryIntelligenceCommandRecipeResponse(BaseModel):
    recipe_id: str
    name: str
    command: str
    purpose: str
    review_relevance: str
    risk: str
    toolchain: str | None = None
    scope_paths: list[str]
    timeout_seconds: int | None = None
    confidence: str
    provenance: list[RepositoryIndexProvenanceResponse]
    limitations: list[str]


class RepositoryIntelligenceOwnershipHintResponse(BaseModel):
    hint_id: str
    owner_label: str
    scope_paths: list[str]
    subsystem: str | None = None
    confidence: str
    provenance: list[RepositoryIndexProvenanceResponse]
    limitations: list[str]


class RepositoryIntelligenceSubsystemResponse(BaseModel):
    subsystem_id: str
    name: str
    scope_paths: list[str]
    package_ids: list[str]
    owner_hint_ids: list[str]
    release_surface_ids: list[str]
    tags: list[str]
    confidence: str
    provenance: list[RepositoryIndexProvenanceResponse]
    limitations: list[str]


class RepositoryIntelligenceReleaseSurfaceResponse(BaseModel):
    surface_id: str
    name: str
    kind: str
    scope_paths: list[str]
    command_recipe_ids: list[str]
    confidence: str
    provenance: list[RepositoryIndexProvenanceResponse]
    limitations: list[str]


class RepositoryIntelligenceMemoryReferenceResponse(BaseModel):
    reference_id: str
    memory_id: str
    kind: str
    summary: str
    source_label: str | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    tags: list[str]
    redacted: bool
    confidence: str
    provenance: dict[str, Any]
    limitations: list[str]


class RepositoryIntelligenceOverviewResponse(BaseModel):
    index: RepositoryIndexStatusResponse
    topology: WorkspaceTopologyStatusResponse | None = None
    source_manifests: list[RepositoryIntelligenceSourceManifestResponse]
    source_roots: list[RepositoryIntelligencePathHintResponse]
    test_roots: list[RepositoryIntelligencePathHintResponse]
    doc_roots: list[RepositoryIntelligencePathHintResponse]
    generated_paths: list[RepositoryIntelligencePathHintResponse]
    policy_sensitive_paths: list[RepositoryIntelligencePathHintResponse]
    package_boundaries: list[RepositoryIntelligencePackageBoundaryResponse]
    subsystems: list[RepositoryIntelligenceSubsystemResponse]
    release_surfaces: list[RepositoryIntelligenceReleaseSurfaceResponse]
    memory_references: list[RepositoryIntelligenceMemoryReferenceResponse]
    limitations: list[str]


class RepositoryIntelligenceFreshnessResponse(BaseModel):
    index: RepositoryIndexStatusResponse
    topology: WorkspaceTopologyStatusResponse | None = None
    cues: list[RepositoryIntelligenceFreshnessCue] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class RepositoryIntelligencePathInspectionResponse(BaseModel):
    path: str
    snapshot_status: str
    packages: list[RepositoryIntelligencePackageBoundaryResponse]
    path_hints: list[RepositoryIntelligencePathHintResponse]
    subsystems: list[RepositoryIntelligenceSubsystemResponse]
    command_recipes: list[RepositoryIntelligenceCommandRecipeResponse]
    ownership_hints: list[RepositoryIntelligenceOwnershipHintResponse]
    release_surfaces: list[RepositoryIntelligenceReleaseSurfaceResponse]
    next_actions: list[str]


class RepositoryIntelligenceCommandRecipeListPageResponse(BaseModel):
    page: PageInfoResponse
    items: list[RepositoryIntelligenceCommandRecipeResponse]


class RepositoryIntelligenceCommandRecipeDetailResponse(BaseModel):
    recipe: RepositoryIntelligenceCommandRecipeResponse


class RepositoryIntelligenceSubsystemListPageResponse(BaseModel):
    page: PageInfoResponse
    items: list[RepositoryIntelligenceSubsystemResponse]


class RepositoryIntelligenceSubsystemDetailResponse(BaseModel):
    subsystem: RepositoryIntelligenceSubsystemResponse
    ownership_hints: list[RepositoryIntelligenceOwnershipHintResponse]
    release_surfaces: list[RepositoryIntelligenceReleaseSurfaceResponse]
    command_recipes: list[RepositoryIntelligenceCommandRecipeResponse]


class RepositoryIntelligenceSearchPageResponse(BaseModel):
    query: str
    page: PageInfoResponse
    items: list[RepositoryIndexEntryResponse]


class RepositoryIntelligenceVerificationRecommendationResponse(BaseModel):
    status: str
    paths: list[str]
    report: EvalRecommendationReport | None = None
    detail: str | None = None
    next_actions: list[str] = Field(default_factory=list)


class RepositoryIntelligenceMemoryCandidateListPageResponse(BaseModel):
    session_id: str
    page: PageInfoResponse
    items: list[WorkspaceMemoryCandidateResponse]


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


def build_path_inspection_response(
    inspection: RepositoryIntelligencePathInspection,
) -> RepositoryIntelligencePathInspectionResponse:
    return RepositoryIntelligencePathInspectionResponse(
        path=inspection.path.as_posix(),
        snapshot_status=inspection.snapshot_status,
        packages=build_package_boundary_responses(inspection.packages),
        path_hints=build_path_hint_responses(inspection.path_hints),
        subsystems=build_subsystem_responses(inspection.subsystems),
        command_recipes=build_command_recipe_responses(inspection.command_recipes),
        ownership_hints=build_ownership_hint_responses(inspection.ownership_hints),
        release_surfaces=build_release_surface_responses(inspection.release_surfaces),
        next_actions=inspection.next_actions,
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
        provenance=[_provenance_response(item) for item in manifest.provenance],
        limitations=manifest.limitations,
    )


def build_path_hint_responses(
    hints: Sequence[RepositoryIntelligencePathHint],
) -> list[RepositoryIntelligencePathHintResponse]:
    return [
        RepositoryIntelligencePathHintResponse(
            hint_id=hint.hint_id,
            kind=hint.kind.value,
            path=hint.path.as_posix(),
            package_id=hint.package_id,
            language=hint.language,
            confidence=hint.confidence.value,
            provenance=[_provenance_response(item) for item in hint.provenance],
            limitations=hint.limitations,
        )
        for hint in hints
    ]


def build_package_boundary_responses(
    packages: Sequence[RepositoryIntelligencePackageBoundary],
) -> list[RepositoryIntelligencePackageBoundaryResponse]:
    return [
        RepositoryIntelligencePackageBoundaryResponse(
            package_id=package.package_id,
            name=package.name,
            kind=package.kind.value,
            root=package.root.as_posix(),
            manifest_paths=[path.as_posix() for path in package.manifest_paths],
            source_roots=[path.as_posix() for path in package.source_roots],
            test_roots=[path.as_posix() for path in package.test_roots],
            doc_roots=[path.as_posix() for path in package.doc_roots],
            generated_paths=[path.as_posix() for path in package.generated_paths],
            confidence=package.confidence.value,
            provenance=[_provenance_response(item) for item in package.provenance],
            limitations=package.limitations,
        )
        for package in packages
    ]


def build_command_recipe_responses(
    recipes: Sequence[RepositoryIntelligenceCommandRecipe],
) -> list[RepositoryIntelligenceCommandRecipeResponse]:
    return [
        RepositoryIntelligenceCommandRecipeResponse(
            recipe_id=recipe.recipe_id,
            name=recipe.name,
            command=recipe.command,
            purpose=recipe.purpose.value,
            review_relevance=recipe.review_relevance.value,
            risk=recipe.risk.value,
            toolchain=recipe.toolchain,
            scope_paths=[path.as_posix() for path in recipe.scope_paths],
            timeout_seconds=recipe.timeout_seconds,
            confidence=recipe.confidence.value,
            provenance=[_provenance_response(item) for item in recipe.provenance],
            limitations=recipe.limitations,
        )
        for recipe in recipes
    ]


def build_ownership_hint_responses(
    hints: Sequence[RepositoryIntelligenceOwnershipHint],
) -> list[RepositoryIntelligenceOwnershipHintResponse]:
    return [
        RepositoryIntelligenceOwnershipHintResponse(
            hint_id=hint.hint_id,
            owner_label=hint.owner_label,
            scope_paths=[path.as_posix() for path in hint.scope_paths],
            subsystem=hint.subsystem,
            confidence=hint.confidence.value,
            provenance=[_provenance_response(item) for item in hint.provenance],
            limitations=hint.limitations,
        )
        for hint in hints
    ]


def build_subsystem_responses(
    subsystems: Sequence[RepositoryIntelligenceSubsystem],
) -> list[RepositoryIntelligenceSubsystemResponse]:
    return [
        RepositoryIntelligenceSubsystemResponse(
            subsystem_id=subsystem.subsystem_id,
            name=subsystem.name,
            scope_paths=[path.as_posix() for path in subsystem.scope_paths],
            package_ids=subsystem.package_ids,
            owner_hint_ids=subsystem.owner_hint_ids,
            release_surface_ids=subsystem.release_surface_ids,
            tags=subsystem.tags,
            confidence=subsystem.confidence.value,
            provenance=[_provenance_response(item) for item in subsystem.provenance],
            limitations=subsystem.limitations,
        )
        for subsystem in subsystems
    ]


def build_release_surface_responses(
    surfaces: Sequence[RepositoryIntelligenceReleaseSurface],
) -> list[RepositoryIntelligenceReleaseSurfaceResponse]:
    return [
        RepositoryIntelligenceReleaseSurfaceResponse(
            surface_id=surface.surface_id,
            name=surface.name,
            kind=surface.kind.value,
            scope_paths=[path.as_posix() for path in surface.scope_paths],
            command_recipe_ids=surface.command_recipe_ids,
            confidence=surface.confidence.value,
            provenance=[_provenance_response(item) for item in surface.provenance],
            limitations=surface.limitations,
        )
        for surface in surfaces
    ]


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


def build_entry_search_page_response(
    *,
    query: str,
    cursor: int,
    limit: int,
    entries: Sequence[RepositoryIndexEntry],
) -> RepositoryIntelligenceSearchPageResponse:
    items = list(entries[cursor : cursor + limit])
    next_cursor = cursor + len(items) if len(entries) > cursor + limit else None
    return RepositoryIntelligenceSearchPageResponse(
        query=query,
        page=PageInfoResponse(
            cursor=cursor,
            limit=limit,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            returned_count=len(items),
        ),
        items=[build_repository_index_entry_response(entry) for entry in items],
    )


def build_repository_status_response_from_snapshot(
    snapshot,
    *,
    path: str,
) -> RepositoryIndexStatusResponse:
    return build_repository_index_status_response(snapshot, path=path)


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
