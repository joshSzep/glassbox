"""Release-surface discovery for repository intelligence layouts."""

from pathlib import Path

from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.types import CommandPurpose
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import RepositoryIntelligenceReleaseSurfaceKind
from glassbox.runtime.repository_intelligence_layout_common import _provenance
from glassbox.runtime.repository_intelligence_layout_recipes import (
    recipe_ids_for_commands,
)
from glassbox.runtime.repository_intelligence_layout_recipes import (
    recipe_ids_for_purposes,
)


def discover_release_surface_hints(
    root: Path,
    recipes: list[RepositoryIntelligenceCommandRecipe],
) -> list[RepositoryIntelligenceReleaseSurface]:
    """Discover advisory release surfaces from known command recipes."""

    del root
    return [
        RepositoryIntelligenceReleaseSurface(
            surface_id="release-surface:commit-time",
            name="Commit-time verification",
            kind=RepositoryIntelligenceReleaseSurfaceKind.COMMIT_TIME,
            scope_paths=[Path("src"), Path("tests")],
            command_recipe_ids=recipe_ids_for_purposes(
                recipes,
                {CommandPurpose.TEST, CommandPurpose.LINT, CommandPurpose.TYPECHECK},
            ),
            confidence=RepositoryIntelligenceConfidence.MEDIUM,
            provenance=[
                _provenance(RepositoryIndexSourceType.MANIFEST, Path("pyproject.toml"))
            ],
            limitations=[
                "Commit-time surface is advisory until a deterministic hook or "
                "operator action records evidence."
            ],
        ),
        RepositoryIntelligenceReleaseSurface(
            surface_id="release-surface:push-time",
            name="Push-time confirmation",
            kind=RepositoryIntelligenceReleaseSurfaceKind.PUSH_TIME,
            scope_paths=[Path("src"), Path("tests"), Path("frontend")],
            command_recipe_ids=recipe_ids_for_commands(recipes, ["push-confirmation"]),
            confidence=RepositoryIntelligenceConfidence.LOW,
            provenance=[
                _provenance(RepositoryIndexSourceType.EVAL, Path("evals/profiles.json"))
            ],
            limitations=["Push-time mapping is inferred from eval profile metadata."],
        ),
        RepositoryIntelligenceReleaseSurface(
            surface_id="release-surface:release-candidate",
            name="Release-candidate signoff",
            kind=RepositoryIntelligenceReleaseSurfaceKind.RELEASE_CANDIDATE,
            scope_paths=[Path("scripts"), Path("evals"), Path("docs")],
            command_recipe_ids=recipe_ids_for_purposes(
                recipes,
                {CommandPurpose.EVAL, CommandPurpose.RELEASE_GATE},
            ),
            confidence=RepositoryIntelligenceConfidence.HIGH,
            provenance=[
                _provenance(RepositoryIndexSourceType.EVAL, Path("evals/profiles.json"))
            ],
            limitations=[
                "Release-candidate recipes explain likely checks; release "
                "authority remains deterministic gate evidence."
            ],
        ),
        RepositoryIntelligenceReleaseSurface(
            surface_id="release-surface:advisory",
            name="Advisory local evidence",
            kind=RepositoryIntelligenceReleaseSurfaceKind.ADVISORY,
            scope_paths=[Path("docs"), Path("frontend"), Path("src/glassbox/web")],
            command_recipe_ids=recipe_ids_for_commands(recipes, ["advisory"]),
            confidence=RepositoryIntelligenceConfidence.LOW,
            provenance=[
                _provenance(RepositoryIndexSourceType.DOCUMENTATION, Path("docs"))
            ],
            limitations=[
                "Advisory surfaces guide inspection but do not block release."
            ],
        ),
    ]


__all__ = ["discover_release_surface_hints"]
