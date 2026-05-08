"""Repository intelligence layout discovery for v2 index snapshots."""

import hashlib
import json
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.models import RepositoryIntelligencePackageBoundary
from glassbox.core.models import RepositoryIntelligencePathHint
from glassbox.core.models import RepositoryIntelligenceSourceManifest
from glassbox.core.types import CommandPurpose
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceCommandRisk
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.core.types import RepositoryIntelligencePackageKind
from glassbox.core.types import RepositoryIntelligencePathKind
from glassbox.runtime.repository_index_discovery import BUILD_OUTPUT_NAMES
from glassbox.runtime.repository_index_discovery import CACHE_PATH_NAMES
from glassbox.runtime.repository_index_discovery import classify_repository_path
from glassbox.runtime.repository_index_discovery import (
    is_policy_sensitive_repository_path,
)

EXCLUDED_PATH_LIMITATION = (
    "Excluded from file crawling; retained as path-level posture only."
)


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
    limitations: list[str]


def discover_repository_intelligence_layout(
    root: Path,
    *,
    built_at: datetime,
) -> RepositoryIntelligenceLayout:
    """Derive roots, package boundaries, manifests, and generated path hints."""

    del built_at
    source_manifests: list[RepositoryIntelligenceSourceManifest] = []
    source_roots: list[RepositoryIntelligencePathHint] = []
    test_roots: list[RepositoryIntelligencePathHint] = []
    doc_roots: list[RepositoryIntelligencePathHint] = []
    generated_paths: list[RepositoryIntelligencePathHint] = []
    policy_sensitive_paths: list[RepositoryIntelligencePathHint] = []
    package_boundaries: list[RepositoryIntelligencePackageBoundary] = []
    command_recipes: list[RepositoryIntelligenceCommandRecipe] = []

    def add_manifest(path: Path, role: str) -> None:
        if not (root / path).exists():
            return
        source_manifests.append(
            RepositoryIntelligenceSourceManifest(
                manifest_id=f"manifest:{_slug(path)}",
                path=path,
                source_type=RepositoryIndexSourceType.MANIFEST,
                role=role,
                digest=_file_digest(root / path),
                provenance=[_provenance(RepositoryIndexSourceType.MANIFEST, path)],
            )
        )

    pyproject = Path("pyproject.toml")
    if (root / pyproject).exists():
        add_manifest(pyproject, "python project manifest")
        package = _python_package(root, pyproject)
        package_boundaries.append(package)
        command_recipes.extend(_pyproject_command_recipes(root, pyproject, package))
        source_roots.extend(
            _path_hints(
                package.source_roots, RepositoryIntelligencePathKind.SOURCE_ROOT
            )
        )
        test_roots.extend(
            _path_hints(package.test_roots, RepositoryIntelligencePathKind.TEST_ROOT)
        )
        doc_roots.extend(
            _path_hints(package.doc_roots, RepositoryIntelligencePathKind.DOC_ROOT)
        )
        generated_paths.extend(_generated_hints(package.generated_paths))
        for lockfile in ("uv.lock", "poetry.lock"):
            add_manifest(Path(lockfile), "python lockfile")

    for package_json in sorted(root.rglob("package.json")):
        relative = package_json.relative_to(root)
        if classify_repository_path(relative).excluded:
            continue
        add_manifest(relative, "node package manifest")
        package = _node_package(root, relative)
        package_boundaries.append(package)
        command_recipes.extend(_node_command_recipes(root, relative, package))
        source_roots.extend(
            _path_hints(
                package.source_roots, RepositoryIntelligencePathKind.SOURCE_ROOT
            )
        )
        test_roots.extend(
            _path_hints(package.test_roots, RepositoryIntelligencePathKind.TEST_ROOT)
        )
        generated_paths.extend(_generated_hints(package.generated_paths))
        for lockfile in ("pnpm-lock.yaml", "package-lock.json"):
            add_manifest(relative.parent / lockfile, "node lockfile")

    if (root / "docs").is_dir():
        docs_path = Path("docs")
        doc_roots.append(_path_hint(docs_path, RepositoryIntelligencePathKind.DOC_ROOT))
        package_boundaries.append(
            RepositoryIntelligencePackageBoundary(
                package_id="docs:docs",
                name="docs",
                kind=RepositoryIntelligencePackageKind.DOCS,
                root=docs_path,
                doc_roots=[docs_path],
                confidence=RepositoryIntelligenceConfidence.HIGH,
                provenance=[
                    _provenance(RepositoryIndexSourceType.DOCUMENTATION, docs_path)
                ],
            )
        )

    if (root / "evals").is_dir():
        eval_root = Path("evals")
        package_boundaries.append(
            RepositoryIntelligencePackageBoundary(
                package_id="evals:evals",
                name="evals",
                kind=RepositoryIntelligencePackageKind.EVAL,
                root=eval_root,
                manifest_paths=_existing_paths(
                    root,
                    [
                        "evals/coverage.json",
                        "evals/impact.json",
                        "evals/profiles.json",
                        "evals/recipes.json",
                    ],
                ),
                confidence=RepositoryIntelligenceConfidence.MEDIUM,
                provenance=[_provenance(RepositoryIndexSourceType.EVAL, eval_root)],
            )
        )
        for manifest in (
            "coverage.json",
            "impact.json",
            "profiles.json",
            "recipes.json",
        ):
            add_manifest(eval_root / manifest, "eval metadata")
        command_recipes.extend(_eval_command_recipes(root))

    generated_paths.extend(_known_generated_and_ignored_hints(root))
    policy_sensitive_paths.extend(_policy_sensitive_hints(root))
    command_recipes.extend(_release_script_command_recipes(root))
    command_recipes.extend(_docs_command_recipes(root))

    return RepositoryIntelligenceLayout(
        source_manifests=_dedupe_by_id(source_manifests, "manifest_id"),
        source_roots=_dedupe_by_id(source_roots, "hint_id"),
        test_roots=_dedupe_by_id(test_roots, "hint_id"),
        doc_roots=_dedupe_by_id(doc_roots, "hint_id"),
        generated_paths=_dedupe_by_id(generated_paths, "hint_id"),
        policy_sensitive_paths=_dedupe_by_id(policy_sensitive_paths, "hint_id"),
        package_boundaries=_dedupe_by_id(package_boundaries, "package_id"),
        command_recipes=_dedupe_command_recipes(command_recipes),
        limitations=[],
    )


def _python_package(
    root: Path, pyproject: Path
) -> RepositoryIntelligencePackageBoundary:
    data = _read_toml(root / pyproject)
    project = data.get("project", {})
    if not isinstance(project, dict):
        project = {}
    name = str(project.get("name") or root.name)
    source_candidates = ["src", name.replace("-", "_"), f"src/{name.replace('-', '_')}"]
    generated = _existing_paths(root, ["src/glassbox/web/static_next"])
    return RepositoryIntelligencePackageBoundary(
        package_id=f"package:{name}",
        name=name,
        kind=RepositoryIntelligencePackageKind.PYTHON,
        root=Path("."),
        manifest_paths=[pyproject],
        source_roots=_existing_paths(root, source_candidates) or [Path(".")],
        test_roots=_existing_paths(root, ["tests"]),
        doc_roots=_existing_paths(root, ["docs"]),
        generated_paths=generated,
        confidence=RepositoryIntelligenceConfidence.HIGH,
        provenance=[_provenance(RepositoryIndexSourceType.MANIFEST, pyproject)],
    )


def _node_package(
    root: Path,
    package_json: Path,
) -> RepositoryIntelligencePackageBoundary:
    data = _read_json(root / package_json)
    component_root = package_json.parent
    name = str(data.get("name") or component_root.name or root.name)
    source_roots = _existing_paths(
        root,
        [
            component_root / "app",
            component_root / "components",
            component_root / "src",
            component_root / "stores",
        ],
    )
    test_roots = _existing_paths(
        root,
        [component_root / "tests", component_root / "e2e"],
    )
    generated = _existing_paths(
        root,
        [
            component_root / "generated",
            component_root / "out",
            component_root / ".next",
            component_root / "dist",
            component_root / "build",
        ],
    )
    return RepositoryIntelligencePackageBoundary(
        package_id=f"app:{name}",
        name=name,
        kind=RepositoryIntelligencePackageKind.FRONTEND,
        root=component_root,
        manifest_paths=[package_json],
        source_roots=source_roots or [component_root],
        test_roots=test_roots,
        generated_paths=generated,
        confidence=RepositoryIntelligenceConfidence.HIGH,
        provenance=[_provenance(RepositoryIndexSourceType.MANIFEST, package_json)],
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


def _known_generated_and_ignored_hints(
    root: Path,
) -> list[RepositoryIntelligencePathHint]:
    hints: list[RepositoryIntelligencePathHint] = []
    known_paths: set[Path] = set()
    candidates = [
        "frontend/generated",
        "frontend/out",
        "frontend/.next",
        "src/glassbox/web/static_next",
        "dist",
        "build",
        "coverage",
    ]
    for package_json in sorted(root.rglob("package.json")):
        relative = package_json.relative_to(root)
        if classify_repository_path(relative).excluded:
            continue
        for name in [*BUILD_OUTPUT_NAMES, *CACHE_PATH_NAMES, "generated"]:
            candidates.append((relative.parent / name).as_posix())
    for candidate in candidates:
        relative = Path(candidate)
        if relative in known_paths or not (root / relative).exists():
            continue
        classification = classify_repository_path(relative)
        if not (
            classification.generated
            or classification.cache
            or classification.build_output
        ):
            continue
        known_paths.add(relative)
        hints.append(
            _path_hint(
                relative,
                _generated_kind(classification),
                confidence=RepositoryIntelligenceConfidence.HIGH,
                limitations=(
                    [EXCLUDED_PATH_LIMITATION] if classification.excluded else []
                ),
            )
        )
    return hints


def _policy_sensitive_hints(root: Path) -> list[RepositoryIntelligencePathHint]:
    candidates = [
        ".github",
        "docs/tool-policy",
        "scripts",
        "src/glassbox/tools/policy.py",
        "src/glassbox/tools/policy_config.py",
    ]
    hints: list[RepositoryIntelligencePathHint] = []
    for candidate in candidates:
        relative = Path(candidate)
        if (root / relative).exists() and is_policy_sensitive_repository_path(relative):
            hints.append(
                _path_hint(
                    relative,
                    RepositoryIntelligencePathKind.POLICY_SENSITIVE_PATH,
                    confidence=RepositoryIntelligenceConfidence.MEDIUM,
                )
            )
    for docs_task in sorted((root / "docs").glob("tasks-v*.md"))[:20]:
        relative = docs_task.relative_to(root)
        hints.append(
            _path_hint(
                relative,
                RepositoryIntelligencePathKind.POLICY_SENSITIVE_PATH,
                confidence=RepositoryIntelligenceConfidence.MEDIUM,
            )
        )
    return hints


def _path_hints(
    paths: list[Path],
    kind: RepositoryIntelligencePathKind,
) -> list[RepositoryIntelligencePathHint]:
    return [_path_hint(path, kind) for path in paths]


def _generated_hints(paths: list[Path]) -> list[RepositoryIntelligencePathHint]:
    hints: list[RepositoryIntelligencePathHint] = []
    for path in paths:
        classification = classify_repository_path(path)
        hints.append(
            _path_hint(
                path,
                _generated_kind(classification),
                confidence=RepositoryIntelligenceConfidence.HIGH,
                limitations=(
                    [EXCLUDED_PATH_LIMITATION] if classification.excluded else []
                ),
            )
        )
    return hints


def _generated_kind(classification: Any) -> RepositoryIntelligencePathKind:
    if classification.cache:
        return RepositoryIntelligencePathKind.CACHE_PATH
    if classification.build_output:
        return RepositoryIntelligencePathKind.BUILD_OUTPUT
    return RepositoryIntelligencePathKind.GENERATED_PATH


def _path_hint(
    path: Path,
    kind: RepositoryIntelligencePathKind,
    *,
    confidence: RepositoryIntelligenceConfidence = (
        RepositoryIntelligenceConfidence.HIGH
    ),
    limitations: list[str] | None = None,
) -> RepositoryIntelligencePathHint:
    source_type = (
        RepositoryIndexSourceType.DOCUMENTATION
        if kind == RepositoryIntelligencePathKind.DOC_ROOT
        else RepositoryIndexSourceType.FILE_SYSTEM
    )
    return RepositoryIntelligencePathHint(
        hint_id=f"{kind.value}:{_slug(path)}",
        kind=kind,
        path=path,
        confidence=confidence,
        provenance=[_provenance(source_type, path)],
        limitations=limitations or [],
    )


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


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    return list(dict.fromkeys(paths))


def _existing_paths(root: Path, candidates: Sequence[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for candidate in candidates:
        relative = Path(candidate)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        if (root / relative).exists():
            paths.append(relative)
    return paths


def _provenance(
    source_type: RepositoryIndexSourceType,
    path: Path,
) -> RepositoryIndexProvenance:
    return RepositoryIndexProvenance(source_type=source_type, path=path)


def _file_digest(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return hashlib.sha256(data).hexdigest()


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError:
        return {}
    except tomllib.TOMLDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _dedupe_by_id[T](items: list[T], field_name: str) -> list[T]:
    seen: set[str] = set()
    deduped: list[T] = []
    for item in items:
        value = str(getattr(item, field_name))
        if value in seen:
            continue
        seen.add(value)
        deduped.append(item)
    return deduped


def _slug(path: Path) -> str:
    value = path.as_posix()
    if value in {"", "."}:
        return "root"
    return value.replace("/", ":")


__all__ = [
    "RepositoryIntelligenceLayout",
    "discover_repository_intelligence_layout",
]
