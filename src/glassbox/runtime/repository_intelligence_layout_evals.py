"""Eval command recipe discovery for repository intelligence layouts."""

from pathlib import Path

from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.runtime.repository_intelligence_layout_common import _dedupe_paths
from glassbox.runtime.repository_intelligence_layout_common import _read_json
from glassbox.runtime.repository_intelligence_layout_recipes import command_toolchain
from glassbox.runtime.repository_intelligence_layout_recipes import (
    make_repository_intelligence_command_recipe,
)


def discover_eval_command_recipes(
    root: Path,
) -> list[RepositoryIntelligenceCommandRecipe]:
    """Discover command recipes from eval metadata."""

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
                make_repository_intelligence_command_recipe(
                    recipe_id=f"eval-recipe:{recipe_id}:{index}",
                    name=title,
                    command=command.strip(),
                    source_path=path,
                    source_type=RepositoryIndexSourceType.EVAL,
                    scope_paths=scope_paths,
                    confidence=RepositoryIntelligenceConfidence.HIGH,
                    toolchain=command_toolchain(command.strip()),
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
            make_repository_intelligence_command_recipe(
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


__all__ = ["discover_eval_command_recipes"]
