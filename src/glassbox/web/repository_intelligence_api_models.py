"""HTTP transport models for repository intelligence v2 APIs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from glassbox.runtime.eval_recommendations import EvalRecommendationReport
from glassbox.runtime.repository_intelligence_freshness import (
    RepositoryIntelligenceFreshnessCue,
)
from glassbox.web.memory_api import WorkspaceMemoryCandidateResponse
from glassbox.web.repository_index_api import RepositoryIndexEntryResponse
from glassbox.web.repository_index_api import RepositoryIndexProvenanceResponse
from glassbox.web.repository_index_api import RepositoryIndexStatusResponse
from glassbox.web.repository_index_api import WorkspaceTopologyStatusResponse
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
