"""Repository intelligence layout discovery for v2 index snapshots."""

from datetime import datetime
from pathlib import Path

from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.runtime.repository_intelligence_layout_common import _dedupe_by_id
from glassbox.runtime.repository_intelligence_layout_docs import (
    discover_docs_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_evals import (
    discover_eval_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_models import (
    RepositoryIntelligenceLayout,
)
from glassbox.runtime.repository_intelligence_layout_ownership import (
    discover_codeowners_ownership_hints,
)
from glassbox.runtime.repository_intelligence_layout_ownership import (
    discover_subsystem_owner_hints,
)
from glassbox.runtime.repository_intelligence_layout_packages import (
    discover_repository_intelligence_packages,
)
from glassbox.runtime.repository_intelligence_layout_paths import (
    discover_repository_intelligence_paths,
)
from glassbox.runtime.repository_intelligence_layout_recipes import (
    dedupe_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_recipes import (
    discover_package_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_recipes import (
    discover_release_script_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_release import (
    discover_release_surface_hints,
)
from glassbox.runtime.repository_intelligence_layout_subsystems import (
    discover_repository_intelligence_subsystems,
)


def discover_repository_intelligence_layout(
    root: Path,
    *,
    built_at: datetime,
) -> RepositoryIntelligenceLayout:
    """Derive roots, package boundaries, manifests, and generated path hints."""

    del built_at
    command_recipes: list[RepositoryIntelligenceCommandRecipe] = []
    ownership_hints: list[RepositoryIntelligenceOwnershipHint] = []
    subsystems: list[RepositoryIntelligenceSubsystem] = []
    release_surfaces: list[RepositoryIntelligenceReleaseSurface] = []

    package_discovery = discover_repository_intelligence_packages(root)
    package_boundaries = package_discovery.package_boundaries
    path_discovery = discover_repository_intelligence_paths(root, package_boundaries)

    command_recipes.extend(discover_package_command_recipes(root, package_boundaries))
    command_recipes.extend(discover_eval_command_recipes(root))
    command_recipes.extend(discover_release_script_command_recipes(root))
    command_recipes.extend(discover_docs_command_recipes(root))
    ownership_hints.extend(discover_codeowners_ownership_hints(root))
    subsystems.extend(
        discover_repository_intelligence_subsystems(root, package_boundaries)
    )
    ownership_hints.extend(discover_subsystem_owner_hints(root, subsystems))
    release_surfaces.extend(discover_release_surface_hints(root, command_recipes))

    return RepositoryIntelligenceLayout(
        source_manifests=_dedupe_by_id(
            package_discovery.source_manifests, "manifest_id"
        ),
        source_roots=_dedupe_by_id(path_discovery.source_roots, "hint_id"),
        test_roots=_dedupe_by_id(path_discovery.test_roots, "hint_id"),
        doc_roots=_dedupe_by_id(path_discovery.doc_roots, "hint_id"),
        generated_paths=_dedupe_by_id(path_discovery.generated_paths, "hint_id"),
        policy_sensitive_paths=_dedupe_by_id(
            path_discovery.policy_sensitive_paths, "hint_id"
        ),
        package_boundaries=_dedupe_by_id(package_boundaries, "package_id"),
        command_recipes=dedupe_command_recipes(command_recipes),
        ownership_hints=_dedupe_by_id(ownership_hints, "hint_id"),
        subsystems=_dedupe_by_id(subsystems, "subsystem_id"),
        release_sensitive_surfaces=_dedupe_by_id(release_surfaces, "surface_id"),
        limitations=[],
    )


__all__ = [
    "RepositoryIntelligenceLayout",
    "discover_repository_intelligence_layout",
]
