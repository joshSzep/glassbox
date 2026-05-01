"""Repository-owned verification recipes for common change families."""

from fnmatch import fnmatch
from pathlib import Path
from pathlib import PurePosixPath

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.runtime.evals import _ensure_path_within_root
from glassbox.runtime.evals import _normalize_identifier

EVAL_VERIFICATION_RECIPE_MANIFEST_VERSION = 1
DEFAULT_EVAL_VERIFICATION_RECIPES_PATH = Path("evals") / "recipes.json"


class EvalVerificationRecipe(BaseModel):
    """Declarative verification guidance for one recurring change family."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    title: str
    path_globs: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    profile_ids: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("recipe_id")
    @classmethod
    def validate_recipe_id(cls, value: str) -> str:
        return _normalize_identifier(value, kind="recipe_id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be empty")
        return title

    @field_validator("path_globs", "commands")
    @classmethod
    def validate_non_empty_strings(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            candidate = item.strip()
            if not candidate:
                raise ValueError("recipe list entries must not be empty")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("profile_ids")
    @classmethod
    def validate_profile_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for profile_id in value:
            candidate = _normalize_identifier(profile_id, kind="profile_id")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for case_id in value:
            candidate = _normalize_identifier(case_id, kind="case_id")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        notes = value.strip()
        return notes or None

    @model_validator(mode="after")
    def validate_recipe_targets(self) -> EvalVerificationRecipe:
        if not self.path_globs:
            raise ValueError("verification recipe must declare at least one path glob")
        if not self.commands:
            raise ValueError("verification recipe must declare at least one command")
        return self


class EvalVerificationRecipeManifest(BaseModel):
    """On-disk manifest for repository-owned verification recipes."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = EVAL_VERIFICATION_RECIPE_MANIFEST_VERSION
    recipes: list[EvalVerificationRecipe] = Field(default_factory=list)

    @field_validator("manifest_version")
    @classmethod
    def validate_manifest_version(cls, value: int) -> int:
        if value != EVAL_VERIFICATION_RECIPE_MANIFEST_VERSION:
            raise ValueError(
                f"unsupported eval verification recipe manifest version: {value}"
            )
        return value

    @field_validator("recipes")
    @classmethod
    def validate_recipes(
        cls, value: list[EvalVerificationRecipe]
    ) -> list[EvalVerificationRecipe]:
        seen_recipe_ids: set[str] = set()
        for recipe in value:
            if recipe.recipe_id in seen_recipe_ids:
                raise ValueError(
                    f"duplicate eval verification recipe id: {recipe.recipe_id}"
                )
            seen_recipe_ids.add(recipe.recipe_id)
        return value


def load_eval_verification_recipe_manifest(
    workspace_root: Path,
    *,
    recipes_path: Path | None = None,
) -> EvalVerificationRecipeManifest:
    """Load repository-owned verification recipes from disk."""

    resolved_recipes_path = _resolve_recipes_path(
        workspace_root,
        recipes_path=recipes_path,
    )
    try:
        raw_manifest = resolved_recipes_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"missing eval verification recipe manifest: {resolved_recipes_path}"
        ) from exc

    try:
        manifest = EvalVerificationRecipeManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(
            f"invalid eval verification recipe manifest {resolved_recipes_path}: {exc}"
        ) from exc

    _ensure_path_within_root(
        resolved_recipes_path,
        workspace_root.resolve(),
        kind="eval verification recipe manifest",
    )
    return manifest


def maybe_load_eval_verification_recipe_manifest(
    workspace_root: Path,
    *,
    recipes_path: Path | None = None,
) -> EvalVerificationRecipeManifest | None:
    """Load verification recipes when the repository provides them."""

    resolved_recipes_path = _resolve_recipes_path(
        workspace_root,
        recipes_path=recipes_path,
    )
    if not resolved_recipes_path.is_file():
        return None
    return load_eval_verification_recipe_manifest(
        workspace_root,
        recipes_path=recipes_path,
    )


def recipe_matched_paths(
    *,
    normalized_paths: list[str],
    recipe: EvalVerificationRecipe,
) -> list[str]:
    """Return touched paths matched by one verification recipe."""

    matched_paths: list[str] = []
    for normalized_path in normalized_paths:
        pure_path = PurePosixPath(normalized_path)
        if any(
            pure_path.match(path_glob) or fnmatch(normalized_path, path_glob)
            for path_glob in recipe.path_globs
        ):
            matched_paths.append(normalized_path)
    return matched_paths


def _resolve_recipes_path(
    workspace_root: Path,
    *,
    recipes_path: Path | None,
) -> Path:
    if recipes_path is None:
        return (
            workspace_root.resolve() / DEFAULT_EVAL_VERIFICATION_RECIPES_PATH
        ).resolve()
    if recipes_path.is_absolute():
        return recipes_path.resolve()
    return (workspace_root.resolve() / recipes_path).resolve()
