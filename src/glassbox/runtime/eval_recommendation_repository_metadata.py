"""Repository-intelligence source metadata helpers for eval recommendations."""

from pathlib import Path

from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.runtime.eval_recommendation_common import dedupe_strings
from glassbox.runtime.eval_recommendation_matching_common import RecommendationReasonMap
from glassbox.runtime.eval_recommendation_models import EvalRecommendationSourceMetadata
from glassbox.runtime.eval_recommendation_models import PathVerificationFreshness
from glassbox.runtime.eval_recommendation_repository_matching import surface_stage
from glassbox.runtime.evals import EvalCase


def case_repository_intelligence_metadata(
    *,
    cases: list[EvalCase],
    case_reasons: RecommendationReasonMap,
    matched_subsystems: list[tuple[RepositoryIntelligenceSubsystem, list[str]]],
    matched_owners: list[tuple[RepositoryIntelligenceOwnershipHint, list[str]]],
    matched_surfaces: list[tuple[RepositoryIntelligenceReleaseSurface, list[str]]],
    freshness: PathVerificationFreshness,
) -> dict[str, list[EvalRecommendationSourceMetadata]]:
    metadata: dict[str, list[EvalRecommendationSourceMetadata]] = {}
    cases_by_id = {case.case_id: case for case in cases}
    for case_id in case_reasons:
        case = cases_by_id.get(case_id)
        if case is None:
            continue
        for subsystem, paths in matched_subsystems:
            if _case_mentions_subsystem(case, subsystem):
                append_repository_intelligence_metadata(
                    metadata,
                    case_id,
                    subsystem_repository_intelligence_metadata(
                        subsystem,
                        paths,
                        freshness=freshness,
                    ),
                )
        for owner, paths in matched_owners:
            append_repository_intelligence_metadata(
                metadata,
                case_id,
                owner_repository_intelligence_metadata(
                    owner,
                    paths,
                    freshness=freshness,
                ),
            )
        for surface, paths in matched_surfaces:
            if _case_mentions_surface(case, surface):
                append_repository_intelligence_metadata(
                    metadata,
                    case_id,
                    surface_repository_intelligence_metadata(
                        surface,
                        paths,
                        freshness=freshness,
                    ),
                )
    return metadata


def subsystem_repository_intelligence_metadata(
    subsystem: RepositoryIntelligenceSubsystem,
    matched_paths: list[str],
    *,
    freshness: PathVerificationFreshness,
) -> EvalRecommendationSourceMetadata:
    return EvalRecommendationSourceMetadata(
        source="repository-intelligence-snapshot",
        source_id=subsystem.subsystem_id,
        source_path=_provenance_path(subsystem.provenance),
        freshness=freshness,
        matched_paths=dedupe_strings(matched_paths),
        explanation=(
            f"Repository intelligence matched subsystem `{subsystem.name}` "
            "for the changed paths."
        ),
        limitations=list(subsystem.limitations),
    )


def owner_repository_intelligence_metadata(
    owner: RepositoryIntelligenceOwnershipHint,
    matched_paths: list[str],
    *,
    freshness: PathVerificationFreshness,
) -> EvalRecommendationSourceMetadata:
    return EvalRecommendationSourceMetadata(
        source="repository-intelligence-snapshot",
        source_id=owner.hint_id,
        source_path=_provenance_path(owner.provenance),
        freshness=freshness,
        matched_paths=dedupe_strings(matched_paths),
        explanation=(
            f"Repository intelligence matched owner hint `{owner.owner_label}`."
        ),
        limitations=list(owner.limitations),
    )


def surface_repository_intelligence_metadata(
    surface: RepositoryIntelligenceReleaseSurface,
    matched_paths: list[str],
    *,
    freshness: PathVerificationFreshness,
) -> EvalRecommendationSourceMetadata:
    return EvalRecommendationSourceMetadata(
        source="repository-intelligence-snapshot",
        source_id=surface.surface_id,
        source_path=_provenance_path(surface.provenance),
        freshness=freshness,
        matched_paths=dedupe_strings(matched_paths),
        explanation=(
            f"Repository intelligence matched release surface `{surface.name}`."
        ),
        limitations=list(surface.limitations),
    )


def append_repository_intelligence_metadata(
    mapping: dict[str, list[EvalRecommendationSourceMetadata]],
    key: str,
    metadata: EvalRecommendationSourceMetadata,
) -> None:
    rows = mapping.setdefault(key, [])
    dedupe_key = (
        metadata.source,
        metadata.source_id,
        tuple(metadata.matched_paths),
        metadata.freshness,
    )
    if dedupe_key not in {
        (row.source, row.source_id, tuple(row.matched_paths), row.freshness)
        for row in rows
    }:
        rows.append(metadata)


def _case_mentions_subsystem(
    case: EvalCase,
    subsystem: RepositoryIntelligenceSubsystem,
) -> bool:
    tokens = {
        subsystem.subsystem_id.removeprefix("subsystem:"),
        *(tag.lower() for tag in subsystem.tags),
    }
    owner = (case.release_contract.owner or "").lower()
    capabilities = [
        capability.lower() for capability in case.release_contract.capabilities
    ]
    return any(
        token and (token in owner or any(token in cap for cap in capabilities))
        for token in tokens
    )


def _case_mentions_surface(
    case: EvalCase,
    surface: RepositoryIntelligenceReleaseSurface,
) -> bool:
    stage = surface_stage(surface.kind)
    return stage is not None and stage in case.release_contract.verification_stages


def _provenance_path(provenance: object) -> str | None:
    if not isinstance(provenance, list) or not provenance:
        return None
    first = provenance[0]
    source_type = getattr(first, "source_type", None)
    path = getattr(first, "path", None)
    if path is None:
        return None
    if source_type == RepositoryIndexSourceType.FILE_SYSTEM:
        return Path(path).as_posix()
    return Path(path).as_posix()


__all__ = [
    "append_repository_intelligence_metadata",
    "case_repository_intelligence_metadata",
    "owner_repository_intelligence_metadata",
    "subsystem_repository_intelligence_metadata",
    "surface_repository_intelligence_metadata",
]
