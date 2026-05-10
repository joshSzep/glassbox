"""Documentation command recipe discovery for repository intelligence layouts."""

from pathlib import Path

from glassbox.core.models import RepositoryIntelligenceCommandRecipe
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence
from glassbox.runtime.repository_intelligence_layout_common import _slug
from glassbox.runtime.repository_intelligence_layout_recipes import command_toolchain
from glassbox.runtime.repository_intelligence_layout_recipes import (
    make_repository_intelligence_command_recipe,
)


def discover_docs_command_recipes(
    root: Path,
) -> list[RepositoryIntelligenceCommandRecipe]:
    """Discover advisory command recipes from documented command examples."""

    docs_paths = [root / "README.md", *sorted((root / "docs").glob("*.md"))[:20]]
    recipes: list[RepositoryIntelligenceCommandRecipe] = []
    for path in docs_paths:
        if not path.exists() or not path.is_file():
            continue
        relative = path.relative_to(root)
        scope = relative.parent if relative.parent != Path(".") else Path(".")
        for index, command in enumerate(_documented_commands(path)[:10]):
            recipes.append(
                make_repository_intelligence_command_recipe(
                    recipe_id=f"docs:{_slug(relative)}:{index}",
                    name=f"Documented command in {relative.as_posix()}",
                    command=command,
                    source_path=relative,
                    source_type=RepositoryIndexSourceType.DOCUMENTATION,
                    scope_paths=[scope],
                    confidence=RepositoryIntelligenceConfidence.LOW,
                    toolchain=command_toolchain(command),
                    limitations=[
                        "Documentation command examples may need operator "
                        "confirmation before use."
                    ],
                )
            )
    return recipes[:50]


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


__all__ = ["discover_docs_command_recipes"]
