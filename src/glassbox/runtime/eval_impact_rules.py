"""Repository-owned path impact rules for replay/eval recommendations."""

from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.runtime.evals import _ensure_path_within_root
from glassbox.runtime.evals import _normalize_identifier

EVAL_IMPACT_MANIFEST_VERSION = 1
DEFAULT_EVAL_IMPACT_PATH = Path("evals") / "impact.json"


class EvalImpactRule(BaseModel):
    """Repository-owned path heuristics for replay/eval change impact."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    path_globs: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    profile_ids: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("rule_id")
    @classmethod
    def validate_rule_id(cls, value: str) -> str:
        return _normalize_identifier(value, kind="rule_id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be empty")
        return title

    @field_validator("path_globs")
    @classmethod
    def validate_path_globs(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            candidate = item.strip()
            if not candidate:
                raise ValueError("path_globs entries must not be empty")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("owners")
    @classmethod
    def validate_owners(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for owner in value:
            candidate = _normalize_identifier(owner, kind="owner")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for capability in value:
            candidate = _normalize_identifier(capability, kind="capability_id")
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

    @field_validator("profile_ids")
    @classmethod
    def validate_profile_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for profile_id in value:
            candidate = _normalize_identifier(profile_id, kind="profile_id")
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
    def validate_rule_targets(self) -> EvalImpactRule:
        if not self.path_globs:
            raise ValueError("impact rule must declare at least one path glob")
        if not any([self.owners, self.capabilities, self.case_ids, self.profile_ids]):
            raise ValueError(
                "impact rule must declare at least one owner, capability, "
                "case, or profile target"
            )
        return self


class EvalImpactManifest(BaseModel):
    """On-disk manifest for repository-owned replay/eval impact rules."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = EVAL_IMPACT_MANIFEST_VERSION
    rules: list[EvalImpactRule] = Field(default_factory=list)

    @field_validator("manifest_version")
    @classmethod
    def validate_manifest_version(cls, value: int) -> int:
        if value != EVAL_IMPACT_MANIFEST_VERSION:
            raise ValueError(f"unsupported eval impact manifest version: {value}")
        return value

    @field_validator("rules")
    @classmethod
    def validate_rules(cls, value: list[EvalImpactRule]) -> list[EvalImpactRule]:
        seen_rule_ids: set[str] = set()
        for rule in value:
            if rule.rule_id in seen_rule_ids:
                raise ValueError(f"duplicate eval impact rule id: {rule.rule_id}")
            seen_rule_ids.add(rule.rule_id)
        return value


def load_eval_impact_manifest(
    workspace_root: Path,
    *,
    impact_path: Path | None = None,
) -> EvalImpactManifest:
    """Load repository-owned replay/eval impact rules from disk."""

    resolved_impact_path = _resolve_impact_path(workspace_root, impact_path=impact_path)
    try:
        raw_manifest = resolved_impact_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"missing eval impact manifest: {resolved_impact_path}"
        ) from exc

    try:
        manifest = EvalImpactManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(
            f"invalid eval impact manifest {resolved_impact_path}: {exc}"
        ) from exc

    _ensure_path_within_root(
        resolved_impact_path,
        workspace_root.resolve(),
        kind="eval impact manifest",
    )
    return manifest


def maybe_load_eval_impact_manifest(
    workspace_root: Path,
    *,
    impact_path: Path | None = None,
) -> EvalImpactManifest | None:
    """Load replay/eval impact rules when the repository provides them."""

    resolved_impact_path = _resolve_impact_path(workspace_root, impact_path=impact_path)
    if not resolved_impact_path.is_file():
        return None
    return load_eval_impact_manifest(workspace_root, impact_path=impact_path)


def _resolve_impact_path(workspace_root: Path, *, impact_path: Path | None) -> Path:
    if impact_path is None:
        return (workspace_root.resolve() / DEFAULT_EVAL_IMPACT_PATH).resolve()
    if impact_path.is_absolute():
        return impact_path.resolve()
    return (workspace_root.resolve() / impact_path).resolve()
