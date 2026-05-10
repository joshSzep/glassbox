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
from glassbox.core.types import RepositoryIntelligenceCommandRisk
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import RepositoryIntelligencePackageKind
from glassbox.core.types import RepositoryIntelligenceReleaseSurfaceKind
from glassbox.runtime.repository_intelligence_layout_common import _dedupe_by_id
from glassbox.runtime.repository_intelligence_layout_common import _dedupe_paths
from glassbox.runtime.repository_intelligence_layout_common import _existing_paths
from glassbox.runtime.repository_intelligence_layout_common import _provenance
from glassbox.runtime.repository_intelligence_layout_common import _read_json
from glassbox.runtime.repository_intelligence_layout_common import _read_toml
from glassbox.runtime.repository_intelligence_layout_common import _slug
from glassbox.runtime.repository_intelligence_layout_models import (
    RepositoryIntelligenceLayout,
)
from glassbox.runtime.repository_intelligence_layout_packages import (
    discover_repository_intelligence_packages,
)
from glassbox.runtime.repository_intelligence_layout_paths import (
    discover_repository_intelligence_paths,
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

    for package in package_boundaries:
        manifest_path = package.manifest_paths[0] if package.manifest_paths else None
        if package.kind == RepositoryIntelligencePackageKind.PYTHON and manifest_path:
            command_recipes.extend(
                _pyproject_command_recipes(root, manifest_path, package)
            )
        elif (
            package.kind == RepositoryIntelligencePackageKind.FRONTEND and manifest_path
        ):
            command_recipes.extend(_node_command_recipes(root, manifest_path, package))
        elif package.kind == RepositoryIntelligencePackageKind.EVAL:
            command_recipes.extend(_eval_command_recipes(root))

    command_recipes.extend(_release_script_command_recipes(root))
    command_recipes.extend(_docs_command_recipes(root))
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
        command_recipes=_dedupe_command_recipes(command_recipes),
        ownership_hints=_dedupe_by_id(ownership_hints, "hint_id"),
        subsystems=_dedupe_by_id(subsystems, "subsystem_id"),
        release_sensitive_surfaces=_dedupe_by_id(release_surfaces, "surface_id"),
        limitations=[],
    )


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
            _command_recipe(
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
            _command_recipe(
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


def _eval_command_recipes(root: Path) -> list[RepositoryIntelligenceCommandRecipe]:
    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    recipes.extend(_eval_recipes_file_commands(root, Path("evals/recipes.json")))
    recipes.extend(_eval_profile_commands(root, Path("evals/profiles.json")))
    return recipes


def _eval_recipes_file_commands(
    root: Path,
    path: Path,
) -> list[RepositoryIntelligenceCommandRecipe]:
    data = _read_json(root / path)
    raw_recipes = data.get("recipes", [])
    if not isinstance(raw_recipes, list):
        return []
    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    for raw_recipe in raw_recipes:
        if not isinstance(raw_recipe, dict):
            continue
        recipe_id = str(raw_recipe.get("recipe_id") or "unknown")
        title = str(raw_recipe.get("title") or recipe_id)
        commands = raw_recipe.get("commands", [])
        if not isinstance(commands, list):
            continue
        scope_paths = _scope_paths_from_globs(raw_recipe.get("path_globs", []))
        for index, command in enumerate(commands):
            if not isinstance(command, str) or not command.strip():
                continue
            recipes.append(
                _command_recipe(
                    recipe_id=f"eval-recipe:{recipe_id}:{index}",
                    name=title,
                    command=command.strip(),
                    source_path=path,
                    source_type=RepositoryIndexSourceType.EVAL,
                    scope_paths=scope_paths,
                    confidence=RepositoryIntelligenceConfidence.HIGH,
                    toolchain=_command_toolchain(command.strip()),
                    limitations=[
                        "Eval recipe commands are recommendations and do not "
                        "grant execution permission."
                    ],
                )
            )
    return recipes


def _eval_profile_commands(
    root: Path,
    path: Path,
) -> list[RepositoryIntelligenceCommandRecipe]:
    data = _read_json(root / path)
    profiles = data.get("profiles", [])
    if not isinstance(profiles, list):
        return []
    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        profile_id = str(profile.get("profile_id") or "")
        title = str(profile.get("title") or profile_id)
        if not profile_id:
            continue
        recipes.append(
            _command_recipe(
                recipe_id=f"eval-profile:{profile_id}",
                name=title,
                command=f"uv run glassbox eval run --profile {profile_id} --cwd .",
                source_path=path,
                source_type=RepositoryIndexSourceType.EVAL,
                scope_paths=[Path("evals")],
                confidence=RepositoryIntelligenceConfidence.MEDIUM,
                toolchain="uv",
            )
        )
    return recipes


def _release_script_command_recipes(
    root: Path,
) -> list[RepositoryIntelligenceCommandRecipe]:
    scripts_root = root / "scripts"
    if not scripts_root.exists():
        return []
    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    for script in sorted(scripts_root.glob("validate*_release_gate.py"))[:20]:
        relative = script.relative_to(root)
        recipes.append(
            _command_recipe(
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


def _docs_command_recipes(root: Path) -> list[RepositoryIntelligenceCommandRecipe]:
    docs_paths = [root / "README.md", *sorted((root / "docs").glob("*.md"))[:20]]
    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    for path in docs_paths:
        if not path.exists() or not path.is_file():
            continue
        relative = path.relative_to(root)
        scope = relative.parent if relative.parent != Path(".") else Path(".")
        for index, command in enumerate(_documented_commands(path)[:10]):
            recipes.append(
                _command_recipe(
                    recipe_id=f"docs:{_slug(relative)}:{index}",
                    name=f"Documented command in {relative.as_posix()}",
                    command=command,
                    source_path=relative,
                    source_type=RepositoryIndexSourceType.DOCUMENTATION,
                    scope_paths=[scope],
                    confidence=RepositoryIntelligenceConfidence.LOW,
                    toolchain=_command_toolchain(command),
                    limitations=[
                        "Documentation command examples may need operator "
                        "confirmation before use."
                    ],
                )
            )
    return recipes[:50]


def _command_recipe(
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
            command_recipe_ids=_recipe_ids_for_purposes(
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
            command_recipe_ids=_recipe_ids_for_commands(recipes, ["push-confirmation"]),
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
            command_recipe_ids=_recipe_ids_for_purposes(
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
            command_recipe_ids=_recipe_ids_for_commands(recipes, ["advisory"]),
            confidence=RepositoryIntelligenceConfidence.LOW,
            provenance=[
                _provenance(RepositoryIndexSourceType.DOCUMENTATION, Path("docs"))
            ],
            limitations=[
                "Advisory surfaces guide inspection but do not block release."
            ],
        ),
    ]


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


def _scope_paths_from_globs(value: object) -> list[Path]:
    if not isinstance(value, list):
        return []
    paths: list[Path] = []
    for item in value:
        if not isinstance(item, str):
            continue
        prefix = item.split("*", 1)[0].rstrip("/")
        if not prefix:
            continue
        path = Path(prefix)
        if path.suffix:
            path = path.parent if path.parent != Path(".") else path
        if path.is_absolute() or ".." in path.parts:
            continue
        paths.append(path)
    return _dedupe_paths(paths)


def _documented_commands(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    commands: list[str] = []
    prefixes = (
        "uv run ",
        "pnpm --dir ",
        "npm run ",
        "npm --prefix ",
        "python scripts/",
    )
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("$ "):
            line = line[2:].strip()
        if line.startswith(prefixes) and "\n" not in line and "\r" not in line:
            commands.append(line)
    return list(dict.fromkeys(commands))


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


def _command_toolchain(command: str) -> str | None:
    first = command.split(maxsplit=1)[0] if command.split() else ""
    return first or None


def _recipe_ids_for_purposes(
    recipes: list[RepositoryIntelligenceCommandRecipe],
    purposes: set[CommandPurpose],
) -> list[str]:
    return [recipe.recipe_id for recipe in recipes if recipe.purpose in purposes][:20]


def _recipe_ids_for_commands(
    recipes: list[RepositoryIntelligenceCommandRecipe],
    needles: list[str],
) -> list[str]:
    return [
        recipe.recipe_id
        for recipe in recipes
        if any(needle in recipe.command for needle in needles)
    ][:20]


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


def _dedupe_command_recipes(
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


__all__ = [
    "RepositoryIntelligenceLayout",
    "discover_repository_intelligence_layout",
]
