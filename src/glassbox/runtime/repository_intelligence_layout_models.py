"""Models for repository intelligence layout discovery."""

from dataclasses import dataclass

from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSourceManifest
from glassbox.core.models import RepositoryIntelligenceSubsystem


@dataclass(frozen=True)
class RepositoryIntelligenceLayout:
    """Derived layout sections ready for a repository index snapshot."""

    source_manifests: list[RepositoryIntelligenceSourceManifest]
    source_roots: list[RepositoryIntelligencePathHint]
    test_roots: list[RepositoryIntelligencePathHint]
    doc_roots: list[RepositoryIntelligencePathHint]
    generated_paths: list[RepositoryIntelligencePathHint]
    policy_sensitive_paths: list[RepositoryIntelligencePathHint]
    package_boundaries: list[RepositoryIntelligencePackageBoundary]
    command_recipes: list[RepositoryIntelligenceCommandRecipe]
    ownership_hints: list[RepositoryIntelligenceOwnershipHint]
    subsystems: list[RepositoryIntelligenceSubsystem]
    release_sensitive_surfaces: list[RepositoryIntelligenceReleaseSurface]
    limitations: list[str]


__all__ = ["RepositoryIntelligenceLayout"]
