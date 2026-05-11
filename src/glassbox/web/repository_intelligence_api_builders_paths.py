"""Path, recipe, subsystem, and search builders for repository intelligence APIs."""

from collections.abc import Sequence

from glassbox.core.models import RepositoryIndexEntry
from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.runtime.repository_intelligence_queries import (
    RepositoryIntelligencePathInspection,
)
from glassbox.web.repository_index_api import RepositoryIndexProvenanceResponse
from glassbox.web.repository_index_api import build_repository_index_entry_response
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceCommandRecipeResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceOwnershipHintResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligencePackageBoundaryResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligencePathHintResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligencePathInspectionResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceReleaseSurfaceResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceSearchPageResponse,
)
from glassbox.web.repository_intelligence_api_models import (
    RepositoryIntelligenceSubsystemResponse,
)
from glassbox.web.session_api import PageInfoResponse


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
            provenance=[provenance_response(item) for item in hint.provenance],
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
            provenance=[provenance_response(item) for item in package.provenance],
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
            provenance=[provenance_response(item) for item in recipe.provenance],
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
            provenance=[provenance_response(item) for item in hint.provenance],
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
            provenance=[provenance_response(item) for item in subsystem.provenance],
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
            provenance=[provenance_response(item) for item in surface.provenance],
            limitations=surface.limitations,
        )
        for surface in surfaces
    ]


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


def provenance_response(
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
