"""Repository intelligence layout discovery for v2 index snapshots."""

from datetime import datetime
from pathlib import Path

from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligenceReleaseSurface
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.core.types import CommandPurpose
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import RepositoryIntelligenceReleaseSurfaceKind
from glassbox.runtime.repository_intelligence_layout_common import _dedupe_by_id
from glassbox.runtime.repository_intelligence_layout_common import _existing_paths
from glassbox.runtime.repository_intelligence_layout_common import _provenance
from glassbox.runtime.repository_intelligence_layout_docs import (
    discover_docs_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_evals import (
    discover_eval_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_models import (
    RepositoryIntelligenceLayout,
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
from glassbox.runtime.repository_intelligence_layout_recipes import (
    recipe_ids_for_commands,
)
from glassbox.runtime.repository_intelligence_layout_recipes import (
    recipe_ids_for_purposes,
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
    ownership_hints.extend(_codeowners_hints(root))
    subsystems.extend(_subsystem_hints(root, package_boundaries))
    ownership_hints.extend(_subsystem_owner_hints(root, subsystems))
    release_surfaces.extend(_release_surface_hints(root, command_recipes))

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


def _codeowners_hints(root: Path) -> list[RepositoryIntelligenceOwnershipHint]:
    codeowners = _first_existing_path(root, [".github/CODEOWNERS", "CODEOWNERS"])
    if codeowners is None:
        return []
    hints: list[RepositoryIntelligenceOwnershipHint] = []
    try:
        lines = (root / codeowners).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        scope = _codeowners_scope(parts[0])
        owners = " ".join(parts[1:])
        hints.append(
            RepositoryIntelligenceOwnershipHint(
                hint_id=f"owner:codeowners:{index}",
                owner_label=owners,
                scope_paths=[scope],
                confidence=RepositoryIntelligenceConfidence.HIGH,
                provenance=[
                    RepositoryIndexProvenance(
                        source_type=RepositoryIndexSourceType.MANIFEST,
                        path=codeowners,
                        line_start=index,
                        line_end=index,
                    )
                ],
                limitations=[
                    "CODEOWNERS-style hints are advisory repository metadata, "
                    "not access-control authority."
                ],
            )
        )
    return hints


def _subsystem_hints(
    root: Path,
    packages: list[RepositoryIntelligencePackageBoundary],
) -> list[RepositoryIntelligenceSubsystem]:
    package_ids_by_root = {package.root: package.package_id for package in packages}
    subsystems: list[RepositoryIntelligenceSubsystem] = []
    for subsystem_id, name, paths, tags in _subsystem_definitions():
        existing = _existing_paths(root, paths)
        if not existing:
            continue
        subsystems.append(
            RepositoryIntelligenceSubsystem(
                subsystem_id=f"subsystem:{subsystem_id}",
                name=name,
                scope_paths=existing,
                package_ids=[
                    package_id
                    for path, package_id in package_ids_by_root.items()
                    if path in existing
                ],
                tags=tags,
                confidence=RepositoryIntelligenceConfidence.MEDIUM,
                provenance=[
                    _provenance(RepositoryIndexSourceType.FILE_SYSTEM, existing[0])
                ],
                limitations=["Subsystem hint is inferred from local path conventions."],
            )
        )
    return subsystems


def _subsystem_owner_hints(
    root: Path,
    subsystems: list[RepositoryIntelligenceSubsystem],
) -> list[RepositoryIntelligenceOwnershipHint]:
    del root
    hints: list[RepositoryIntelligenceOwnershipHint] = []
    for subsystem in subsystems:
        hints.append(
            RepositoryIntelligenceOwnershipHint(
                hint_id=f"owner:{subsystem.subsystem_id}",
                owner_label=f"{subsystem.name} subsystem maintainers",
                scope_paths=subsystem.scope_paths,
                subsystem=subsystem.subsystem_id,
                confidence=RepositoryIntelligenceConfidence.LOW,
                provenance=[
                    RepositoryIndexProvenance(
                        source_type=RepositoryIndexSourceType.FILE_SYSTEM,
                        path=subsystem.scope_paths[0],
                        note="Inferred from repository subsystem path conventions.",
                    )
                ],
                limitations=[
                    "Inferred owner hint names a local subsystem, not a person "
                    "or required reviewer."
                ],
            )
        )
    return hints


def _release_surface_hints(
    root: Path,
    recipes: list[RepositoryIntelligenceCommandRecipe],
) -> list[RepositoryIntelligenceReleaseSurface]:
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


def _codeowners_scope(pattern: str) -> Path:
    cleaned = pattern.lstrip("/")
    prefix = cleaned.split("*", 1)[0].rstrip("/")
    if not prefix:
        return Path(".")
    path = Path(prefix)
    if path.suffix:
        return path.parent if path.parent != Path(".") else path
    return path


def _first_existing_path(root: Path, candidates: list[str]) -> Path | None:
    for candidate in candidates:
        relative = Path(candidate)
        if (root / relative).exists():
            return relative
    return None


def _subsystem_definitions() -> list[tuple[str, str, list[str], list[str]]]:
    return [
        ("runtime", "Runtime", ["src/glassbox/runtime"], ["backend"]),
        ("store", "Store", ["src/glassbox/store"], ["backend", "persistence"]),
        ("web", "Web API", ["src/glassbox/web"], ["api", "dashboard"]),
        ("cli", "CLI", ["src/glassbox/cli"], ["terminal"]),
        ("frontend", "Frontend", ["frontend"], ["dashboard"]),
        ("evals", "Evals", ["evals"], ["verification"]),
        ("docs", "Docs", ["docs", "README.md"], ["documentation"]),
        ("release", "Release scripts", ["scripts"], ["release"]),
        ("packaging", "Packaging", ["pyproject.toml", "uv.lock"], ["packaging"]),
        ("policy", "Policy", ["src/glassbox/tools/policy.py"], ["policy"]),
        ("provider", "Provider", ["src/glassbox/runtime/provider_config.py"], ["llm"]),
        (
            "memory",
            "Workspace memory",
            ["src/glassbox/runtime/workspace_memory_capture.py"],
            ["memory"],
        ),
        (
            "topology",
            "Workspace topology",
            ["src/glassbox/runtime/workspace_topology.py"],
            ["topology"],
        ),
        (
            "review-loop",
            "Review loop",
            ["src/glassbox/runtime/review_briefs.py"],
            ["review"],
        ),
    ]


__all__ = [
    "RepositoryIntelligenceLayout",
    "discover_repository_intelligence_layout",
]
