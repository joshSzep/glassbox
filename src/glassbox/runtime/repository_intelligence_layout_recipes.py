"""Command recipe discovery helpers for repository intelligence layouts."""

from pathlib import Path

from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.types import CommandPurpose
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceCommandRisk
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import RepositoryIntelligencePackageKind
from glassbox.runtime.repository_intelligence_layout_common import _dedupe_paths
from glassbox.runtime.repository_intelligence_layout_common import _read_json
from glassbox.runtime.repository_intelligence_layout_common import _read_toml
from glassbox.runtime.repository_intelligence_layout_common import _slug


def discover_package_command_recipes(
    root: Path,
    packages: list[RepositoryIntelligencePackageBoundary],
) -> list[RepositoryIntelligenceCommandRecipe]:
    """Discover command recipes from package manifests."""

    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    for package in packages:
        manifest_path = package.manifest_paths[0] if package.manifest_paths else None
        if package.kind == RepositoryIntelligencePackageKind.PYTHON and manifest_path:
            recipes.extend(_pyproject_command_recipes(root, manifest_path, package))
        elif (
            package.kind == RepositoryIntelligencePackageKind.FRONTEND and manifest_path
        ):
            recipes.extend(_node_command_recipes(root, manifest_path, package))
    return recipes


def discover_release_script_command_recipes(
    root: Path,
) -> list[RepositoryIntelligenceCommandRecipe]:
    """Discover advisory command recipes from release scripts."""

    scripts_root = root / "scripts"
    if not scripts_root.exists():
        return []
    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    for script in sorted(scripts_root.glob("validate*_release_gate.py"))[:20]:
        relative = script.relative_to(root)
        recipes.append(
            make_repository_intelligence_command_recipe(
                recipe_id=f"release-script:{_slug(relative)}",
                name=relative.as_posix(),
                command=f"uv run python {relative.as_posix()} --dry-run",
                source_path=relative,
                source_type=RepositoryIndexSourceType.FILE_SYSTEM,
                scope_paths=[Path("scripts")],
                confidence=RepositoryIntelligenceConfidence.MEDIUM,
                toolchain="uv",
                limitations=[
                    "Release script recipes are advisory; release authority "
                    "still comes from deterministic gate evidence."
                ],
            )
        )
    return recipes


def make_repository_intelligence_command_recipe(
    *,
    recipe_id: str,
    name: str,
    command: str,
    source_path: Path,
    source_type: RepositoryIndexSourceType,
    scope_paths: list[Path],
    confidence: RepositoryIntelligenceConfidence,
    toolchain: str | None = None,
    limitations: list[str] | None = None,
) -> RepositoryIntelligenceCommandRecipe:
    """Build a command recipe with deterministic purpose and risk metadata."""

    from glassbox.runtime.command_evidence import classify_command_purpose

    assessment = classify_command_purpose(command)
    return RepositoryIntelligenceCommandRecipe(
        recipe_id=f"recipe:{recipe_id}",
        name=name,
        command=command,
        purpose=assessment.purpose,
        review_relevance=assessment.review_relevance,
        risk=_command_risk(assessment.purpose),
        toolchain=toolchain,
        scope_paths=_dedupe_paths(scope_paths),
        timeout_seconds=_timeout_for_purpose(assessment.purpose),
        confidence=confidence,
        provenance=[
            RepositoryIndexProvenance(
                source_type=source_type,
                path=source_path,
                note=assessment.reason,
            )
        ],
        limitations=limitations or [],
    )


def command_toolchain(command: str) -> str | None:
    first = command.split(maxsplit=1)[0] if command.split() else ""
    return first or None


def recipe_ids_for_purposes(
    recipes: list[RepositoryIntelligenceCommandRecipe],
    purposes: set[CommandPurpose],
) -> list[str]:
    return [recipe.recipe_id for recipe in recipes if recipe.purpose in purposes][:20]


def recipe_ids_for_commands(
    recipes: list[RepositoryIntelligenceCommandRecipe],
    needles: list[str],
) -> list[str]:
    return [
        recipe.recipe_id
        for recipe in recipes
        if any(needle in recipe.command for needle in needles)
    ][:20]


def dedupe_command_recipes(
    recipes: list[RepositoryIntelligenceCommandRecipe],
) -> list[RepositoryIntelligenceCommandRecipe]:
    by_command: dict[str, RepositoryIntelligenceCommandRecipe] = {}
    for recipe in recipes:
        key = " ".join(recipe.command.split())
        existing = by_command.get(key)
        if existing is None:
            by_command[key] = recipe
            continue
        by_command[key] = existing.model_copy(
            update={
                "provenance": [
                    *existing.provenance,
                    *recipe.provenance,
                ],
                "scope_paths": _dedupe_paths(
                    [*existing.scope_paths, *recipe.scope_paths]
                ),
                "limitations": list(
                    dict.fromkeys([*existing.limitations, *recipe.limitations])
                ),
            }
        )
    return sorted(by_command.values(), key=lambda item: item.recipe_id)


def _pyproject_command_recipes(
    root: Path,
    pyproject: Path,
    package: RepositoryIntelligencePackageBoundary,
) -> list[RepositoryIntelligenceCommandRecipe]:
    data = _read_toml(root / pyproject)
    project = data.get("project", {})
    if not isinstance(project, dict):
        return []
    scripts = project.get("scripts", {})
    if not isinstance(scripts, dict):
        return []
    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    for script_name in sorted(str(name) for name in scripts):
        recipes.append(
            make_repository_intelligence_command_recipe(
                recipe_id=f"pyproject:{script_name}",
                name=f"Python script {script_name}",
                command=f"uv run {script_name}",
                source_path=pyproject,
                source_type=RepositoryIndexSourceType.MANIFEST,
                scope_paths=[package.root, *package.source_roots],
                confidence=RepositoryIntelligenceConfidence.LOW,
                toolchain="uv",
                limitations=[
                    "Console script entrypoint is repository-owned, but its "
                    "review purpose may need operator inspection."
                ],
            )
        )
    return recipes


def _node_command_recipes(
    root: Path,
    package_json: Path,
    package: RepositoryIntelligencePackageBoundary,
) -> list[RepositoryIntelligenceCommandRecipe]:
    data = _read_json(root / package_json)
    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        return []
    manager = _node_package_manager(root, package_json.parent)
    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    for script_name in sorted(str(name) for name in scripts):
        recipes.append(
            make_repository_intelligence_command_recipe(
                recipe_id=f"node:{_slug(package.root)}:{script_name}",
                name=f"{package.name}:{script_name}",
                command=_node_script_command(manager, package.root, script_name),
                source_path=package_json,
                source_type=RepositoryIndexSourceType.MANIFEST,
                scope_paths=[package.root, *package.source_roots, *package.test_roots],
                confidence=RepositoryIntelligenceConfidence.HIGH,
                toolchain=manager,
            )
        )
    return recipes


def _node_package_manager(root: Path, package_root: Path) -> str:
    if (root / package_root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / package_root / "package-lock.json").exists():
        return "npm"
    return "npm"


def _node_script_command(manager: str, package_root: Path, script_name: str) -> str:
    root_arg = package_root.as_posix()
    if manager == "pnpm":
        return f"pnpm --dir {root_arg} {script_name}"
    if root_arg == ".":
        return f"npm run {script_name}"
    return f"npm --prefix {root_arg} run {script_name}"


def _command_risk(purpose: CommandPurpose) -> RepositoryIntelligenceCommandRisk:
    if purpose in {CommandPurpose.PUBLISH, CommandPurpose.DEPLOY}:
        return RepositoryIntelligenceCommandRisk.RELEASE
    if purpose in {CommandPurpose.DANGEROUS, CommandPurpose.CLEANUP}:
        return RepositoryIntelligenceCommandRisk.DESTRUCTIVE
    if purpose in {CommandPurpose.BUILD, CommandPurpose.PACKAGE}:
        return RepositoryIntelligenceCommandRisk.WORKSPACE_WRITE
    if purpose == CommandPurpose.UNKNOWN:
        return RepositoryIntelligenceCommandRisk.UNKNOWN
    return RepositoryIntelligenceCommandRisk.READ_ONLY


def _timeout_for_purpose(purpose: CommandPurpose) -> int | None:
    if purpose in {CommandPurpose.EVAL, CommandPurpose.RELEASE_GATE}:
        return 600
    if purpose in {CommandPurpose.BUILD, CommandPurpose.PACKAGE}:
        return 300
    if purpose in {
        CommandPurpose.TEST,
        CommandPurpose.LINT,
        CommandPurpose.TYPECHECK,
    }:
        return 120
    return None


__all__ = [
    "command_toolchain",
    "dedupe_command_recipes",
    "discover_package_command_recipes",
    "discover_release_script_command_recipes",
    "make_repository_intelligence_command_recipe",
    "recipe_ids_for_commands",
    "recipe_ids_for_purposes",
]
